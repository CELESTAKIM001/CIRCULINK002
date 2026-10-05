from datetime import datetime
from app.db import get_db
from app.utils.ids import new


def add(d, owner, images):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    if not images:
        raise ValueError("At least one real photo is required before publishing a listing.")
    x = {
        "_id": new("mat_"), "owner_id": owner, "title": d["title"], "category": d["category"],
        "material": d["material"], "quantity": float(d["quantity"]), "unit": d["unit"],
        "price": float(d["price"]), "terms": d.get("terms", ""), "status": "active",
        "images": images, "primary_image": images[0]["secure_url"],
        "location": {"name": d.get("location_name", ""), "lat": float(d["lat"]) if d.get("lat") else None, "lng": float(d["lng"]) if d.get("lng") else None},
        "created_at": datetime.utcnow(),
    }
    db.listings.insert_one(x)
    return x


def find(q="", category=""):
    db = get_db()
    if db is None:
        return []
    f = {"status": "active"}
    if category: f["category"] = category
    if q: f["$or"] = [{"title": {"$regex": q, "$options": "i"}}, {"material": {"$regex": q, "$options": "i"}}]
    return list(db.listings.find(f).sort("created_at", -1).limit(100))


def one(i):
    db = get_db()
    return db.listings.find_one({"_id": i}) if db is not None else None
