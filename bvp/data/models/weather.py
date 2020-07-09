from typing import Dict, List, Optional, Tuple, Union
from datetime import timedelta
import math

from sqlalchemy.orm import Query
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.sql.expression import func
from sqlalchemy.schema import UniqueConstraint

from bvp.data.config import db
from bvp.data.models.time_series import TimedValue
from bvp.data.queries.utils import add_user_source_filter, add_source_type_filter
from bvp.utils.geo_utils import parse_lat_lng
from bvp.utils.bvp_inflection import humanize


class WeatherSensorType(db.Model):
    """"
    TODO: Add useful attributes like ...?
    """

    name = db.Column(db.String(80), primary_key=True)
    display_name = db.Column(db.String(80), default="", unique=True)

    daily_seasonality = True
    weekly_seasonality = False
    yearly_seasonality = True

    def __init__(self, **kwargs):
        super(WeatherSensorType, self).__init__(**kwargs)
        self.name = self.name.replace(" ", "_").lower()
        if "display_name" not in kwargs:
            self.display_name = humanize(self.name)

    @property
    def icon_name(self) -> str:
        """Icon name for this weather sensor type, which can be used for UI html templates made with Jinja. For example:
            <i class={{ sensor_type.icon_name }}></i>
        becomes (for a wind speed sensor):
            <i class="wi wi-strong-wind"></i>
        """
        if self.name == "radiation":
            return "wi wi-horizon-alt"
        elif self.name == "temperature":
            return "wi wi-thermometer"
        elif self.name == "wind_direction":
            return "wi wi-wind-direction"
        elif self.name == "wind_speed":
            return "wi wi-strong-wind"
        return ""

    def __repr__(self):
        return "<WeatherSensorType %r>" % self.name


class WeatherSensor(db.Model):
    """A weather sensor has a location on Earth and measures weather values of a certain weather sensor type, such as
    temperature, wind speed and radiation."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    display_name = db.Column(db.String(80), default="", unique=False)
    weather_sensor_type_name = db.Column(
        db.String(80), db.ForeignKey("weather_sensor_type.name"), nullable=False
    )
    unit = db.Column(db.String(80), default="", nullable=False)
    # latitude is the North/South coordinate
    latitude = db.Column(db.Float, nullable=False)
    # longitude is the East/West coordinate
    longitude = db.Column(db.Float, nullable=False)

    # only one sensor of any type is needed at one location
    __table_args__ = (
        UniqueConstraint(
            "weather_sensor_type_name",
            "latitude",
            "longitude",
            name="_type_name_location_unique",
        ),
    )

    def __init__(self, **kwargs):
        super(WeatherSensor, self).__init__(**kwargs)
        self.name = self.name.replace(" ", "_").lower()

    @hybrid_property
    def resolution(self) -> timedelta:
        return timedelta(minutes=15)

    @property
    def weather_unit(self) -> float:
        """Return the 'unit' property of the generic asset, just with a more insightful name."""
        return self.unit

    @property
    def location(self) -> Tuple[float, float]:
        return self.latitude, self.longitude

    @hybrid_property
    def cos_rad_lat(self):
        return math.cos(math.radians(self.latitude))

    @hybrid_property
    def sin_rad_lat(self):
        return math.sin(math.radians(self.latitude))

    @hybrid_property
    def rad_lng(self):
        return math.radians(self.longitude)

    @hybrid_method
    def great_circle_distance(self, **kwargs):
        """Query great circle distance (in km).

        Can be called with an object that has latitude and longitude properties, for example:

            great_circle_distance(object=asset)

        Can also be called with latitude and longitude parameters, for example:

            great_circle_distance(latitude=32, longitude=54)
            great_circle_distance(lat=32, lng=54)

        """
        r = 6371  # Radius of Earth in kilometers
        other_latitude, other_longitude = parse_lat_lng(kwargs)
        if other_latitude is None or other_longitude is None:
            return None
        other_cos_rad_lat = math.cos(math.radians(other_latitude))
        other_sin_rad_lat = math.sin(math.radians(other_latitude))
        other_rad_lng = math.radians(other_longitude)
        return (
            math.acos(
                self.cos_rad_lat
                * other_cos_rad_lat
                * math.cos(self.rad_lng - other_rad_lng)
                + self.sin_rad_lat * other_sin_rad_lat
            )
            * r
        )

    @great_circle_distance.expression
    def great_circle_distance(self, **kwargs):
        """Query great circle distance (unclear if in km or in miles).

        Can be called with an object that has latitude and longitude properties, for example:

            great_circle_distance(object=asset)

        Can also be called with latitude and longitude parameters, for example:

            great_circle_distance(latitude=32, longitude=54)
            great_circle_distance(lat=32, lng=54)

         """
        other_latitude, other_longitude = parse_lat_lng(kwargs)
        if other_latitude is None or other_longitude is None:
            return None
        return func.earth_distance(
            func.ll_to_earth(self.latitude, self.longitude),
            func.ll_to_earth(other_latitude, other_longitude),
        )

    sensor_type = db.relationship(
        "WeatherSensorType", backref=db.backref("sensors", lazy=True)
    )

    def __repr__(self):
        return "<WeatherSensor %s:%r (%r)>" % (
            self.id,
            self.name,
            self.weather_sensor_type_name,
        )

    def to_dict(self) -> Dict[str, str]:
        return dict(name=self.name, sensor_type=self.weather_sensor_type_name)


class Weather(TimedValue, db.Model):
    """
    All weather measurements are stored in one slim table.
    TODO: datetime objects take up most of the space (12 bytes each)). One way out is to normalise them out to a table.
    """

    sensor_id = db.Column(
        db.Integer(), db.ForeignKey("weather_sensor.id"), primary_key=True
    )
    sensor = db.relationship("WeatherSensor", backref=db.backref("weather", lazy=True))

    @classmethod
    def make_query(
        cls,
        user_source_ids: Optional[Union[int, List[int]]] = None,
        source_types: Optional[List[str]] = None,
        **kwargs
    ) -> Query:
        query = super().make_query(asset_class=WeatherSensor, **kwargs)
        if user_source_ids:
            query = add_user_source_filter(cls, query, user_source_ids)
        if source_types:
            query = add_source_type_filter(cls, query, source_types)
        return query

    def __init__(self, **kwargs):
        super(Weather, self).__init__(**kwargs)
