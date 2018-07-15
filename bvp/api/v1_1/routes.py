from flask import request

from flask_security import auth_token_required

from bvp.api.v1 import routes
from bvp.api.common.utils.api_utils import check_access, append_doc_of
from bvp.api.common.utils.decorators import as_response_type
from bvp.api.common.utils.validators import usef_roles_accepted
from bvp.api.v1_1 import bvp_api, implementations

# The service listing for this API version (import from previous version or update if needed)
service_listing = {
    "version": "1.1",
    "services": [
        {
            "name": "getMeterData",
            "access": ["Aggregator", "Supplier", "MDC", "DSO", "Prosumer", "ESCo"],
            "description": "Request meter reading",
        },
        {
            "name": "postMeterData",
            "access": ["MDC"],
            "description": "Send meter reading",
        },
        {
            "name": "getPrognosis",
            "access": ["Aggregator", "Supplier", "MDC", "DSO", "Prosumer", "ESCo"],
            "description": "Request load planning",
        },
        {
            "name": "postPrognosis",
            "access": ["Aggregator", "Supplier", "MDC", "DSO", "Prosumer", "ESCo"],
            "description": "Send prediction",
        },
        {
            "name": "postUdiEvent",
            "access": ["Prosumer", "ESCo"],
            "description": "Send a description of some flexible consumption or production process as a USEF Device "
            "Interface (UDI) event, including device capabilities (control constraints)",
        },
        {
            "name": "getDeviceMessage",
            "access": ["Prosumer", "ESCo"],
            "description": "Get an Active Demand & Supply (ADS) request for a certain type of control action, "
            "including control set points",
        },
    ],
}


@bvp_api.route("/getPrognosis", methods=["GET"])
@as_response_type("GetPrognosisResponse")
@auth_token_required
@usef_roles_accepted(*check_access(service_listing, "getPrognosis"))
def get_prognosis():
    """API endpoint to get prognosis.

    .. :quickref: User; Download prognosis from the platform

    **Optional parameters**

    - "resolution" (see :ref:`resolutions`)
    - "horizon" (see :ref:`prognoses`)
    - "source" (see :ref:`sources`)

    **Example request**

    This "GetPrognosisRequest" message requests prognosed consumption between 0.00am and 1.30am for charging station 1,
    with a rolling horizon of 6 hours before the start of each 15 minute time interval.

    .. code-block:: json

        {
            "type": "GetPrognosisRequest",
            "connection": "CS 1",
            "start": "2015-01-01T00:00:00Z",
            "duration": "PT1H30M",
            "horizon": "R/PT6H",
            "resolution": "PT15M",
            "unit": "MW"
        }

    **Example response**

    This "GetPrognosisResponse" message indicates that a prognosis of consumption for charging station 1 was available
    6 hours before the start of each 15 minute time interval.

    .. sourcecode:: json

        {
            "type": "GetPrognosisResponse",
            "connection": "CS 1",
            "values": [
                306.66,
                306.66,
                0,
                0,
                306.66,
                306.66
            ],
            "start": "2015-01-01T00:00:00Z",
            "duration": "PT1H30M",
            "unit": "MW"
        }

    :reqheader Authorization: The authentication token
    :reqheader Content-Type: application/json
    :resheader Content-Type: application/json
    :status 200: PROCESSED
    :status 400: INVALID_MESSAGE_TYPE, INVALID_TIMEZONE, INVALID_UNIT, or UNRECOGNIZED_CONNECTION_GROUP
    :status 401: UNAUTHORIZED
    :status 403: INVALID_SENDER
    :status 405: INVALID_METHOD
    """
    return implementations.get_prognosis_response()


@bvp_api.route("/getMeterData", methods=["GET"])
@as_response_type("GetMeterDataResponse")
@auth_token_required
@usef_roles_accepted(*check_access(service_listing, "getMeterData"))
@append_doc_of(routes.get_meter_data)
def get_meter_data():
    return routes.get_meter_data()


@bvp_api.route("/postMeterData", methods=["POST"])
@as_response_type("PostMeterDataResponse")
@auth_token_required
@usef_roles_accepted(*check_access(service_listing, "postMeterData"))
@append_doc_of(routes.post_meter_data)
def post_meter_data():
    return routes.post_meter_data()


@bvp_api.route("/getService", methods=["GET"])
@as_response_type("GetServiceResponse")
@append_doc_of(routes.get_service)
def get_service():
    return routes.get_service_response(service_listing, request.args.get("access"))
