from app.db import get_db
def recent(limit=100):
    db=get_db()
    collection=db.matches if db is not None else None
    return list(collection.find().sort('created_at',-1).limit(limit)) if collection is not None else []
