from datetime import timedelta, datetime, timezone
import pytest

from marshmallow import ValidationError

from flexmeasures.api.common.schemas.sensor_data import (
    SingleValueField,
    PostSensorDataSchema,
    GetSensorDataSchema,
)
from flexmeasures.data.services.sensors import get_staleness, get_status
from flexmeasures.data.schemas.reporting import StatusSchema


@pytest.mark.parametrize(
    "deserialization_input, exp_deserialization_output",
    [
        (
            "PT1H",
            timedelta(hours=1),
        ),
        (
            "PT15M",
            timedelta(minutes=15),
        ),
    ],
)
def test_resolution_field_deserialization(
    deserialization_input,
    exp_deserialization_output,
):
    """Check parsing the resolution field of the GetSensorDataSchema schema.

    These particular ISO durations are expected to be parsed as python timedeltas.
    """
    # todo: extend test cases with some nominal durations when timely-beliefs supports these
    #       see https://github.com/SeitaBV/timely-beliefs/issues/13
    vf = GetSensorDataSchema._declared_fields["resolution"]
    deser = vf.deserialize(deserialization_input)
    assert deser == exp_deserialization_output


@pytest.mark.parametrize(
    "deserialization_input, exp_deserialization_output",
    [
        (
            1,
            [1],
        ),
        (
            2.7,
            [2.7],
        ),
        (
            [1],
            [1],
        ),
        (
            [2.7],
            [2.7],
        ),
        (
            [1, None, 3],  # sending a None/null value as part of a list is allowed
            [1, None, 3],
        ),
        (
            [None],  # sending a None/null value as part of a list is allowed
            [None],
        ),
    ],
)
def test_value_field_deserialization(
    deserialization_input,
    exp_deserialization_output,
):
    """Testing straightforward cases"""
    vf = PostSensorDataSchema._declared_fields["values"]
    deser = vf.deserialize(deserialization_input)
    assert deser == exp_deserialization_output


@pytest.mark.parametrize(
    "serialization_input, exp_serialization_output",
    [
        (
            1,
            [1],
        ),
        (
            2.7,
            [2.7],
        ),
    ],
)
def test_value_field_serialization(
    serialization_input,
    exp_serialization_output,
):
    """Testing straightforward cases"""
    vf = SingleValueField()
    ser = vf.serialize("values", {"values": serialization_input})
    assert ser == exp_serialization_output


@pytest.mark.parametrize(
    "deserialization_input, error_msg",
    [
        (
            ["three", 4],
            "Not a valid number",
        ),
        (
            "3, 4",
            "Not a valid number",
        ),
        (
            None,
            "may not be null",  # sending a single None/null value is not allowed
        ),
    ],
)
def test_value_field_invalid(deserialization_input, error_msg):
    sf = SingleValueField()
    with pytest.raises(ValidationError) as ve:
        sf.deserialize(deserialization_input)
    assert error_msg in str(ve)


@pytest.mark.parametrize(
    "now, sensor_type, source_name, expected_staleness, expected_status",
    [
        (
            datetime(
                2016,
                1,
                1,
                0,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(hours=-11),
            False,
        ),
        (
            datetime(
                2016,
                1,
                2,
                0,
                18,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(hours=13, minutes=18),
            True,
        ),
        (
            datetime(
                2016,
                1,
                3,
                0,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(days=1, hours=13),
            True,
        ),
        (
            datetime(
                2016,
                1,
                4,
                0,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(days=2, hours=13),
            True,
        ),
        (
            datetime(
                2016,
                1,
                2,
                5,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(hours=18),
            True,
        ),
        (
            datetime(
                2016,
                1,
                2,
                13,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(days=1, hours=2),
            True,
        ),
        (
            datetime(
                2016,
                1,
                2,
                21,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "market",
            None,
            timedelta(days=1, hours=10),
            True,
        ),
        (
            datetime(
                2015,
                1,
                2,
                6,
                20,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "production",
            "Seita",
            timedelta(minutes=-40),
            True,
        ),
        (
            datetime(
                2015,
                1,
                2,
                3,
                18,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "production",
            "Seita",
            timedelta(hours=-3, minutes=-42),
            False,
        ),
        (
            datetime(
                2016,
                1,
                2,
                21,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "production",
            "DummySchedule",
            timedelta(hours=14),
            True,
        ),
        (
            datetime(
                2016,
                1,
                2,
                21,
                0,
                0,
                tzinfo=timezone(offset=timedelta(hours=0), name="Europe/Amsterdam"),
            ),
            "production",
            None,
            timedelta(hours=14),
            True,
        ),
    ],
)
def test_get_status(
    add_market_prices,
    capacity_sensors,
    now,
    sensor_type,
    source_name,
    expected_staleness,
    expected_status,
):
    if sensor_type == "market":
        sensor = add_market_prices["epex_da"]
        staleness_search = {}
    elif sensor_type == "production":
        sensor = capacity_sensors["production"]
        staleness_search = {}
        for source in sensor.data_sources:
            print(source.name)
            if source.name == source_name:
                source_id = source.id
                staleness_search = {"source": source_id}

    print(staleness_search)
    staleness = get_staleness(sensor=sensor, staleness_search=staleness_search, now=now)
    sensor_status = get_status(
        sensor=sensor,
        status_specs={"staleness_search": staleness_search, "max_staleness": "PT1H"},
        now=now,
    )

    status_specs = {"staleness_search": staleness_search, "max_staleness": "PT1H"}
    assert StatusSchema().load(status_specs)
    assert staleness == expected_staleness
    assert sensor_status["staleness"] == expected_staleness
    assert sensor_status["stale"] == expected_status
