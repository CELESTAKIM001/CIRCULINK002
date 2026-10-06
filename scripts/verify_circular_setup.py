"""Check that the circular-operations database indexes/settings can be initialized."""
from app import create_app
from app.db import get_db

app = create_app()
with app.app_context():
    db = get_db()
    if db is None:
        raise SystemExit("MONGODB_URI is not configured or MongoDB is unavailable.")
    print("CIRCULINK database connected")
    print("Circular collections are created lazily by MongoDB on first write.")
    print("Finance defaults are available through app.services.circular.finance_settings().")
