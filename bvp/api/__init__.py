from flask import Flask, Blueprint, request
from flask_marshmallow import Marshmallow
from flask_security.utils import verify_password
from flask_json import as_json
from flask_login import current_user

from bvp.data.models.user import User

# The api blueprint. It is registered with the Flask app (see app.py)
bvp_api = Blueprint("bvp_api", __name__)

ma: Marshmallow = Marshmallow()


@bvp_api.route("/requestAuthToken", methods=["POST"])
@as_json
def request_auth_token():
    """API endpoint to get a fresh authentication access token. Be aware that this fresh token has a limited lifetime
    (which depends on the current system setting SECURITY_TOKEN_MAX_AGE).

    Pass the `email` parameter to identify the user.
    Pass the `password` parameter to authenticate the user (if not already authenticated in current session)

    .. :quickref: Public; Obtain an authentication token
    """

    """
    The login of flask security returns the auth token, as well, but we'd like to
     * skip authentication if the user is authenticated already
     * be exempt from csrf protection (this is a JSON-only endpoint)
     * use a more fitting name inside the api namespace
     * return the information in a nicer structure
    """
    try:
        if not request.is_json:
            return {"errors": ["Content-type of request must be application/json"]}, 400
        if "email" not in request.json:
            return {"errors": ["Please provide the 'email' parameter."]}, 400

        email = request.json["email"]
        if current_user.is_authenticated and current_user.email == email:
            user = current_user
        else:
            user = User.query.filter_by(email=email).one_or_none()
            if not user:
                return (
                    {"errors": ["User with email '%s' does not exist" % email]},
                    404,
                )

            if "password" not in request.json:
                return {"errors": ["Please provide the 'password' parameter."]}
            if not verify_password(request.json["password"], user.password):
                return {"errors": ["User password does not match."]}, 401
        token = user.get_auth_token()
        return {"auth_token": token, "user_id": user.id}
    except Exception as e:
        return {"errors": [str(e)]}, 500


@bvp_api.route("/", methods=["GET"])
@as_json
def get_versions() -> dict:
    """Public endpoint to list API versions.

    .. :quickref: Public; List available API versions

    """
    response = {
        "message": "For these API versions a public endpoint is available, listing its service. For example: "
        "/api/v1/getService and /api/v1_1/getService. An authentication token can be requested at: "
        "/api/requestAuthToken",
        "versions": ["v1", "v1_1", "v1_2", "v1_3"],
    }
    return response


def register_at(app: Flask):
    """This can be used to register this blueprint together with other api-related things"""
    global ma
    ma.init_app(app)

    app.register_blueprint(
        bvp_api, url_prefix="/api"
    )  # now registering the blueprint will affect all endpoints

    # Load API endpoints for internal operations
    from bvp.api.common import register_at as ops_register_at

    ops_register_at(app)

    # Load API endpoints for play mode
    if app.config.get("BVP_MODE", "") == "play":
        from bvp.api.play import register_at as play_register_at

        play_register_at(app)

    # Load all versions of the API functionality, unless the config specifies otherwise
    if app.config.get("BVP_API", True) is True:
        from bvp.api.v1 import register_at as v1_register_at
        from bvp.api.v1_1 import register_at as v1_1_register_at
        from bvp.api.v1_2 import register_at as v1_2_register_at
        from bvp.api.v1_3 import register_at as v1_3_register_at

        v1_register_at(app)
        v1_1_register_at(app)
        v1_2_register_at(app)
        v1_3_register_at(app)
