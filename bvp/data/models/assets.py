from typing import Dict, List, Tuple, Union
from datetime import timedelta

import isodate
import inflection
from inflection import humanize, pluralize, titleize
from sqlalchemy.orm import Query
from sqlalchemy.ext.hybrid import hybrid_property

from bvp.data.config import db
from bvp.data.models.time_series import TimedValue
from bvp.data.queries.utils import assign_source_ids
from bvp.utils.config_utils import get_naming_authority, get_addressing_scheme


# Give the inflection module some help for our domain
inflection.UNCOUNTABLES.add("solar")
inflection.UNCOUNTABLES.add("wind")


class AssetType(db.Model):
    """Describing asset types for our purposes"""

    name = db.Column(db.String(80), primary_key=True)
    display_name = db.Column(db.String(80), default="", unique=True)
    is_consumer = db.Column(db.Boolean(), nullable=False, default=False)
    is_producer = db.Column(db.Boolean(), nullable=False, default=False)
    can_curtail = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    can_shift = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    daily_seasonality = db.Column(db.Boolean(), nullable=False, default=False)
    weekly_seasonality = db.Column(db.Boolean(), nullable=False, default=False)
    yearly_seasonality = db.Column(db.Boolean(), nullable=False, default=False)

    def __init__(self, **kwargs):
        super(AssetType, self).__init__(**kwargs)
        self.name = self.name.replace(" ", "_").lower()
        if "display_name" not in kwargs:
            self.display_name = humanize(self.name)

    @property
    def icon_name(self) -> str:
        """Icon name for this asset type, which can be used for UI html templates made with Jinja. For example:
            <i class={{ asset_type.icon_name }}></i>
        becomes (for a charging station):
            <i class="icon-charging_station"></i>
        """
        if self.name == "solar":
            return "icon-solar"
        elif self.name == "wind":
            return "icon-wind"
        elif self.name in ("charging_station", "bidirectional_charging_station"):
            return "icon-charging_station"
        elif self.name == "battery":
            return "icon-battery"
        elif self.name == "building":
            return "icon-building"

    @property
    def preconditions(self) -> Dict[str, bool]:
        """Assumptions about the time series data set, such as normality and stationarity
        For now, this is usable input for Prophet (see init), but it might evolve or go away."""
        return dict(
            daily_seasonality=self.daily_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            yearly_seasonality=self.yearly_seasonality,
        )

    @property
    def weather_correlations(self) -> List[str]:
        """Known correlations of weather sensor type and asset type."""
        correlations = []
        if self.name == "solar":
            correlations.append("radiation")
        if self.name == "wind":
            correlations.append("wind_speed")
        if self.name in (
            "charging_station",
            "bidirectional_charging_station",
            "battery",
            "building",
        ):
            correlations.append("temperature")
        return correlations

    @property
    def pluralized_name(self):
        return pluralize(self.name)

    def __repr__(self):
        return "<AssetType %r>" % self.name


class Asset(db.Model):
    """Each asset is an energy- consuming or producing hardware. """

    id = db.Column(db.Integer, primary_key=True)
    # The name
    name = db.Column(db.String(80), default="", unique=True)
    # The name we want to see
    display_name = db.Column(db.String(80), default="", unique=True)
    # The name of the assorted AssetType
    asset_type_name = db.Column(
        db.String(80), db.ForeignKey("asset_type.name"), nullable=False
    )
    unit = db.Column(db.String(80), default="", nullable=False)
    # How many MW at peak usage
    capacity_in_mw = db.Column(db.Float, nullable=False)
    # State of charge in MWh and its datetime and udi event
    min_soc_in_mwh = db.Column(db.Float, nullable=True)
    max_soc_in_mwh = db.Column(db.Float, nullable=True)
    soc_in_mwh = db.Column(db.Float, nullable=True)
    soc_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    soc_udi_event_id = db.Column(db.Integer, nullable=True)
    # latitude is the North/South coordinate
    latitude = db.Column(db.Float, nullable=False)
    # longitude is the East/West coordinate
    longitude = db.Column(db.Float, nullable=False)
    # owner
    owner_id = db.Column(db.Integer, db.ForeignKey("bvp_users.id", ondelete="CASCADE"))
    # market
    market_id = db.Column(db.Integer, db.ForeignKey("market.id"), nullable=True)

    def __init__(self, **kwargs):
        super(Asset, self).__init__(**kwargs)
        self.name = self.name.replace(" (MW)", "")
        if self.display_name == "" or self.display_name is None:
            self.display_name = titleize(self.name)

    asset_type = db.relationship("AssetType", backref=db.backref("assets", lazy=True))
    owner = db.relationship(
        "User",
        backref=db.backref(
            "assets", lazy=True, cascade="all, delete-orphan", passive_deletes=True
        ),
    )
    market = db.relationship("Market", backref=db.backref("assets", lazy=True))

    @hybrid_property
    def resolution(self) -> timedelta:
        return timedelta(minutes=15)

    @property
    def power_unit(self) -> float:
        """Return the 'unit' property of the generic asset, just with a more insightful name."""
        return self.unit

    @property
    def asset_type_display_name(self) -> str:
        return titleize(self.asset_type_name)

    @property
    def entity_address(self) -> str:
        return "%s.%s:%s:%s" % (
            get_addressing_scheme(),
            get_naming_authority(),
            self.owner_id,
            self.id,
        )

    @property
    def location(self) -> Tuple[float, float]:
        return self.latitude, self.longitude

    def capacity_factor_in_percent_for(self, load_in_mw) -> int:
        if self.capacity_in_mw == 0:
            return 0
        return min(round((load_in_mw / self.capacity_in_mw) * 100, 2), 100)

    @property
    def is_pure_consumer(self) -> bool:
        """Return True if this asset is consuming but not producing."""
        return self.asset_type.is_consumer and not self.asset_type.is_producer

    @property
    def is_pure_producer(self) -> bool:
        """Return True if this asset is producing but not consuming."""
        return self.asset_type.is_producer and not self.asset_type.is_consumer

    def to_dict(self) -> Dict[str, Union[str, float]]:
        return dict(
            name=self.name,
            display_name=self.display_name,
            asset_type_name=self.asset_type_name,
            latitude=self.latitude,
            longitude=self.longitude,
            capacity_in_mw=self.capacity_in_mw,
        )

    def __repr__(self):
        return "<Asset %s:%r (%s) on market %s>" % (
            self.id,
            self.name,
            self.asset_type_name,
            self.market,
        )


class Power(TimedValue, db.Model):
    """
    All measurements of power data are stored in one slim table.
    Negative values indicate consumption.
    TODO: datetime objects take up most of the space (12 bytes each)). One way out is to normalise them out to a table.
    TODO: If there are more than one measurement per asset per time step possible, we can expand rather easily.
    """

    asset_id = db.Column(
        db.Integer(), db.ForeignKey("asset.id", ondelete="CASCADE"), primary_key=True
    )
    asset = db.relationship(
        "Asset",
        backref=db.backref(
            "measurements",
            lazy="joined",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

    @classmethod
    def make_query(cls, source_ids: Union[int, List[int]] = None, **kwargs) -> Query:
        query = super().make_query(asset_class=Asset, **kwargs)
        query = assign_source_ids(cls, query, source_ids)
        return query

    def to_dict(self):
        return {
            "datetime": isodate.datetime_isoformat(self.datetime),
            "asset_id": self.asset_id,
            "value": self.value,
            "horizon": self.horizon,
        }

    def __init__(self, **kwargs):
        super(Power, self).__init__(**kwargs)

    def __repr__(self):
        return "<Power %.2f on Asset %s at %s by DataSource %s, horizon %s>" % (
            self.value,
            self.asset_id,
            self.datetime,
            self.data_source_id,
            self.horizon,
        )
