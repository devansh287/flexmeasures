from marshmallow import Schema, fields, validate

from flexmeasures.data.schemas.sensors import QuantityOrSensor, SensorIdField


class FlexContextSchema(Schema):
    """
    This schema lists fields that can be used to describe sensors in the optimised portfolio
    """

    ems_power_capacity_in_mw = QuantityOrSensor(
        "MW",
        required=False,
        data_key="site-power-capacity",
        validate=validate.Range(min=0),
    )
    ems_production_capacity_in_mw = QuantityOrSensor(
        "MW",
        required=False,
        data_key="site-production-capacity",
        validate=validate.Range(min=0),
    )
    ems_consumption_capacity_in_mw = QuantityOrSensor(
        "MW",
        required=False,
        data_key="site-consumption-capacity",
        validate=validate.Range(min=0),
    )

    ems_soft_production_capacity_in_mw = QuantityOrSensor(
        "MW",
        required=False,
        data_key="site-soft-production-capacity",
        validate=validate.Range(min=0),
    )
    ems_soft_consumption_capacity_in_mw = QuantityOrSensor(
        "MW",
        required=False,
        data_key="site-soft-consumption-capacity",
        validate=validate.Range(min=0),
    )

    ems_power_limit_relaxation_cost = fields.Float(
        data_key="power-limit-deviation-cost", required=False, default=None
    )
    ems_soft_power_limit_relaxation_cost = fields.Float(
        data_key="soft-power-limit-deviation-cost", required=False, default=None
    )

    consumption_price_sensor = SensorIdField(data_key="consumption-price-sensor")
    production_price_sensor = SensorIdField(data_key="production-price-sensor")
    curtailable_device_sensors = fields.List(
        SensorIdField(), data_key="curtailable-device-sensors"
    )
    inflexible_device_sensors = fields.List(
        SensorIdField(), data_key="inflexible-device-sensors"
    )
