from datetime import datetime, timedelta, timezone
from app.db import get_db

def cleanup(hours=12, limit=500):
    db=get_db()
    if db is None: return {"deleted":0,"skipped":0}
    cutoff=datetime.now(timezone.utc)-timedelta(hours=hours)
    deleted=skipped=0
    for media in db.media.find({"created_at":{"$lt":cutoff}},{"_id":1}).limit(limit):
        mid=media["_id"]
        active_ref=db.listings.find_one({"status":"active","images.media_id":mid}) or db.listings.find_one({"status":"active","primary_image":f"/api/media/{mid}"})
        if active_ref:
            skipped+=1; continue
        db.media.delete_one({"_id":mid})
        db.listings.update_many({}, {"$pull":{"images":{"media_id":mid}}})
        db.listings.update_many({"primary_image":f"/api/media/{mid}"},{"$unset":{"primary_image":""}})
        deleted+=1
    return {"deleted":deleted,"skipped":skipped}
