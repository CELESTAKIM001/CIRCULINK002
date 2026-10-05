from flask import Flask
from dotenv import load_dotenv
from .config import Config
from .db import init_db
from .routes.public import public_bp
from .routes.auth import auth_bp
from .routes.marketplace import marketplace_bp
from .routes.pickups import pickups_bp
from .routes.payments import payments_bp
from .routes.dashboard import dashboard_bp
from .routes.admin import admin_bp
from .routes.api import api_bp
from .routes.receipt import receipt_bp
from .routes.circular import circular_bp

def create_app():
    import uuid
    from flask import request, jsonify, render_template
    from werkzeug.exceptions import HTTPException

    load_dotenv()
    app=Flask(__name__,template_folder="../templates",static_folder="../static",static_url_path="/static")
    app.config.from_object(Config); init_db(app)

    @app.before_request
    def attach_request_id():
        request.circulink_request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]

    @app.after_request
    def attach_response_headers(response):
        response.headers["X-Request-ID"] = getattr(request, "circulink_request_id", "")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.context_processor
    def global_context():
        from app.db import get_db
        default_ad = {"enabled": True, "kicker": "M-HUB 2026 · NYERI", "title": "Built during the M-Hub 2026 innovation season", "text": "CIRCULINK was developed by GEOPRAM TECHNOLOGIES and friends at Nyeri, connecting circular materials, people and businesses.", "link_url": "/about", "link_label": "About the build"}
        db = get_db()
        if db is not None:
            try:
                doc = db.settings.find_one({"key":"mhub_ad"}) or {}
                default_ad.update(doc.get("value", {}))
            except Exception:
                app.logger.exception("Unable to load M-Hub feature banner settings")
        return {"mhub_ad": default_ad, "request_id": getattr(request, "circulink_request_id", "")}

    for bp in [public_bp, auth_bp, marketplace_bp, pickups_bp, payments_bp, dashboard_bp, admin_bp, api_bp, receipt_bp, circular_bp]:
        app.register_blueprint(bp)

    def _is_json_request():
        return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"

    def _error_response(code, title, message, retryable=False, description=None):
        rid = getattr(request, "circulink_request_id", "")
        if _is_json_request():
            return jsonify(ok=False, code=code, title=title, error=message, retryable=retryable, request_id=rid), code
        return render_template("error.html", code=code, title=title, message=message, description=description, retryable=retryable, request_id=rid), code

    @app.errorhandler(400)
    def bad_request(error):
        return _error_response(400, "Request could not be understood", "The information sent to CIRCULINK was incomplete or invalid. Please review it and try again.")

    @app.errorhandler(401)
    def unauthorized(error):
        return _error_response(401, "Sign-in required", "Please sign in before continuing.", retryable=False)

    @app.errorhandler(403)
    def forbidden(error):
        return _error_response(403, "Access not permitted", "You do not have permission to access this resource.")

    @app.errorhandler(404)
    def not_found(error):
        return _error_response(404, "Page not found", "The page or record you requested does not exist, may have moved, or may no longer be available.")

    @app.errorhandler(405)
    def method_not_allowed(error):
        return _error_response(405, "Action not supported", "That action is not available for this page. Return to the page and use the available controls.")

    @app.errorhandler(409)
    def conflict(error):
        return _error_response(409, "Action needs attention", "The requested change conflicts with the current record state. Refresh the page and try again.")

    @app.errorhandler(422)
    def unprocessable(error):
        return _error_response(422, "Information needs correction", "CIRCULINK could not process the submitted information. Check the highlighted fields and try again.")

    @app.errorhandler(429)
    def rate_limited(error):
        return _error_response(429, "Please wait a moment", "Too many requests were received. Wait briefly and try again.", retryable=True)

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled CIRCULINK application error; request_id=%s", getattr(request, "circulink_request_id", ""))
        return _error_response(500, "Something went wrong", "CIRCULINK could not complete that request. Your data was not intentionally marked successful. Please retry or contact support.", retryable=True)

    @app.errorhandler(502)
    def bad_gateway(error):
        return _error_response(502, "External service unavailable", "A connected service did not complete the request. Your CIRCULINK record remains unchanged unless a success message was shown.", retryable=True)

    @app.errorhandler(503)
    def unavailable(error):
        return _error_response(503, "Service temporarily unavailable", "CIRCULINK is temporarily unable to complete this operation. Please wait and try again.", retryable=True)

    @app.errorhandler(Exception)
    def unhandled(error):
        if isinstance(error, HTTPException):
            return _error_response(error.code or 500, error.name, error.description or "The request could not be completed.", retryable=(error.code or 500) >= 500)
        app.logger.exception("Unhandled non-HTTP CIRCULINK error; request_id=%s", getattr(request, "circulink_request_id", ""))
        return _error_response(500, "Something went wrong", "CIRCULINK could not complete that request. Please retry or contact support.", retryable=True)

    return app
