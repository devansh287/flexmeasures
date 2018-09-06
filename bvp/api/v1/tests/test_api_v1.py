import json
from datetime import timedelta

from flask import url_for
import pytest
from iso8601 import parse_date
from numpy import repeat


from bvp.api.common.responses import (
    invalid_domain,
    invalid_sender,
    invalid_unit,
    request_processed,
    unrecognized_connection_group,
)
from bvp.api.tests.utils import get_auth_token
from bvp.api.common.utils.api_utils import message_replace_name_with_ea
from bvp.api.v1.tests.utils import (
    message_for_get_meter_data,
    message_for_post_meter_data,
)
from bvp.data.auth_setup import UNAUTH_ERROR_STATUS
from bvp.api.v1.tests.utils import count_connections_in_post_message
from bvp.data.models.forecasting.jobs import ForecastingJob
from bvp.data.models.assets import Asset


@pytest.mark.parametrize("query", [{}, {"access": "Prosumer"}])
def test_get_service(client, query):
    get_service_response = client.get(
        url_for("bvp_api_v1.get_service"),
        query_string=query,
        headers={"content-type": "application/json"},
    )
    print("Server responded with:\n%s" % get_service_response.json)
    assert get_service_response.status_code == 200
    assert get_service_response.json["type"] == "GetServiceResponse"
    assert get_service_response.json["status"] == request_processed()[0]["status"]
    if "access" in query:
        for service in get_service_response.json["services"]:
            assert "Prosumer" in service["access"]


def test_unauthorized_request(client):
    get_meter_data_response = client.get(
        url_for("bvp_api_v1.get_meter_data"),
        query_string=message_for_get_meter_data(no_connection=True),
        headers={"content-type": "application/json"},
    )
    print("Server responded with:\n%s" % get_meter_data_response.json)
    assert get_meter_data_response.status_code == 401
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    assert get_meter_data_response.json["status"] == UNAUTH_ERROR_STATUS


def test_no_connection_in_get_request(client):
    get_meter_data_response = client.get(
        url_for("bvp_api_v1.get_meter_data"),
        query_string=message_for_get_meter_data(no_connection=True),
        headers={
            "Authorization": get_auth_token(
                client, "test_prosumer@seita.nl", "testtest"
            )
        },
    )
    print("Server responded with:\n%s" % get_meter_data_response.json)
    assert get_meter_data_response.status_code == 400
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    assert (
        get_meter_data_response.json["status"]
        == unrecognized_connection_group()[0]["status"]
    )


def test_invalid_connection_in_get_request(client):
    get_meter_data_response = client.get(
        url_for("bvp_api_v1.get_meter_data"),
        query_string=message_for_get_meter_data(invalid_connection=True),
        headers={
            "Authorization": get_auth_token(
                client, "test_prosumer@seita.nl", "testtest"
            )
        },
    )
    print("Server responded with:\n%s" % get_meter_data_response.json)
    assert get_meter_data_response.status_code == 400
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    assert get_meter_data_response.json["status"] == invalid_domain()[0]["status"]


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    "message",
    [
        message_for_get_meter_data(no_unit=True),
        message_for_get_meter_data(invalid_unit=True),
    ],
)
def test_invalid_or_no_unit(client, method, message):
    if method == "GET":
        get_meter_data_response = client.get(
            url_for("bvp_api_v1.get_meter_data"),
            query_string=message,
            headers={
                "Authorization": get_auth_token(
                    client, "test_prosumer@seita.nl", "testtest"
                )
            },
        )
    elif method == "POST":
        get_meter_data_response = client.post(
            url_for("bvp_api_v1.get_meter_data"),
            data=json.dumps(message),
            headers={
                "Authorization": get_auth_token(
                    client, "test_prosumer@seita.nl", "testtest"
                )
            },
        )
    else:
        get_meter_data_response = []
    assert get_meter_data_response.status_code == 400
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    assert get_meter_data_response.json["status"] == invalid_unit("MW")[0]["status"]


def test_invalid_sender_and_logout(client):
    """
    Tries to get meter data as a logged-in test user without any USEF role, which should fail.
    Then tries to log out, which should succeed as a url direction.
    """

    # get meter data
    auth_token = get_auth_token(client, "test_user@seita.nl", "testtest")
    get_meter_data_response = client.get(
        url_for("bvp_api_v1.get_meter_data"),
        query_string=message_for_get_meter_data(),
        headers={"Authorization": auth_token},
    )
    print("Server responded with:\n%s" % get_meter_data_response.json)
    assert get_meter_data_response.status_code == 403
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    assert get_meter_data_response.json["status"] == invalid_sender("MDC")[0]["status"]

    # log out
    logout_response = client.get(
        url_for("security.logout"),
        headers={"Authorization ": auth_token, "content-type": "application/json"},
    )
    assert logout_response.status_code == 302


@pytest.mark.parametrize(
    "post_message",
    [
        message_for_post_meter_data(),
        message_for_post_meter_data(single_connection=True),
        message_for_post_meter_data(single_connection_group=True),
    ],
)
@pytest.mark.parametrize(
    "get_message",
    [message_for_get_meter_data(), message_for_get_meter_data(single_connection=False)],
)
def test_post_and_get_meter_data(db, client, post_message, get_message):
    """
    Tries to post meter data as a logged-in test user with the MDC role, which should succeed.
    There should be some ForecastingJobs waiting now.
    Then tries to get meter data, which should succeed, and should return the same meter data as was posted.
    """

    # post meter data
    auth_token = get_auth_token(client, "test_prosumer@seita.nl", "testtest")
    post_meter_data_response = client.post(
        url_for("bvp_api_v1.post_meter_data"),
        data=json.dumps(message_replace_name_with_ea(post_message)),
        headers={"content-type": "application/json", "Authorization": auth_token},
    )
    print("Server responded with:\n%s" % post_meter_data_response.json)
    assert post_meter_data_response.status_code == 200
    assert post_meter_data_response.json["type"] == "PostMeterDataResponse"

    # look for Forecasting jobs
    jobs = ForecastingJob.query.order_by(ForecastingJob.horizon.asc()).all()
    expected_connections = count_connections_in_post_message(post_message)
    assert (
        len(jobs) == 4 * expected_connections
    )  # four horizons times the number of assets
    horizons = repeat(
        [
            timedelta(hours=1),
            timedelta(hours=6),
            timedelta(hours=24),
            timedelta(hours=48),
        ],
        expected_connections,
    )
    for job, horizon in zip(jobs, horizons):
        assert job.horizon == horizon
        assert job.start == parse_date(post_message["start"]) + horizon
    for asset_name in ("CS 1", "CS 2", "CS 3"):
        if asset_name in str(post_message):
            asset = Asset.query.filter_by(name=asset_name).one_or_none()
            assert asset.id in [job.asset_id for job in jobs]

    # get meter data
    get_meter_data_response = client.get(
        url_for("bvp_api_v1.get_meter_data"),
        query_string=message_replace_name_with_ea(get_message),
        headers={"Authorization": auth_token},
    )
    print("Server responded with:\n%s" % get_meter_data_response.json)
    assert get_meter_data_response.status_code == 200
    assert get_meter_data_response.json["type"] == "GetMeterDataResponse"
    if "groups" in post_message:
        values = post_message["groups"][0]["values"]
    else:
        values = post_message["values"]
    if "groups" in get_meter_data_response.json:
        assert get_meter_data_response.json["groups"][0]["values"] == values
    else:
        assert get_meter_data_response.json["values"] == values
