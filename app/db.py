from pymongo import ASCENDING, DESCENDING, MongoClient

_client = None
_db = None


def init_db(app):
    global _client, _db
    uri = (app.config.get("MONGODB_URI") or "").strip()
    if not uri:
        app.logger.warning("MONGODB_URI is not configured; database-backed features are unavailable.")
        return None
    try:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        _db = _client[app.config.get("MONGODB_DB", "circulink")]
        # Creating indexes is safe to repeat and keeps production data consistent.
        _db.users.create_index([("email", ASCENDING)], unique=True)
        _db.otps.create_index([("email", ASCENDING), ("purpose", ASCENDING)])
        _db.listings.create_index([("status", ASCENDING), ("category", ASCENDING)])
        _db.audit_logs.create_index([("created_at", DESCENDING)])
        _db.material_requests.create_index([("company_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)])
        _db.fulfillments.create_index([("request_id", ASCENDING), ("status", ASCENDING)])
        _db.payouts.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
        _db.point_ledger.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.point_redemptions.create_index([("user_id", ASCENDING), ("status", ASCENDING)])
        _db.certificates.create_index([("certificate_no", ASCENDING)], unique=True)
        _db.contact_messages.create_index([("created_at", DESCENDING)])
        _db.media.create_index([("created_at", DESCENDING)])
        _db.badges.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.mhub_events.create_index([("created_at", DESCENDING)])
        _db.platform_revenue.create_index([("created_at", DESCENDING)])
        _db.transactions.create_index([("order_id", ASCENDING), ("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.transactions.create_index([("checkout_request_id", ASCENDING)], sparse=True)
        _db.transactions.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
        _db.mpesa_callbacks.create_index([("checkout_request_id", ASCENDING), ("created_at", DESCENDING)])
        return _db
    except Exception:
        app.logger.exception("Unable to initialise MongoDB.")
        _db = None
        return None


def get_db():
    """Return the configured Mongo database or None.

    Never use a PyMongo Database object as a boolean. PyMongo deliberately raises
    NotImplementedError for ``if database`` checks.
    """
    return _db


def db_configured():
    return _db is not None
