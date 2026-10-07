from app.db import get_db


def stats():
    db = get_db()
    if db is None:
        return {k: 0 for k in ["users", "listings", "orders", "transactions"]}
    return {k: db[k].count_documents({}) for k in ["users", "listings", "orders", "transactions"]}
