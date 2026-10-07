import os
import bcrypt
from datetime import datetime
from app.db import get_db
from app.utils.ids import new


def create(d):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    email = d["email"].lower().strip()
    u = {
        "_id": new("usr_"),
        "name": d["name"].strip(),
        "email": email,
        "phone": d.get("phone", ""),
        "password_hash": bcrypt.hashpw(d["password"].encode(), bcrypt.gensalt()).decode(),
        "role": "ADMIN" if email == os.getenv("ADMIN_EMAIL", "circulink1@gmail.com").lower() else "USER",
        "account_type": d.get("account_type", "individual"),
        "verified": False,
        "created_at": datetime.utcnow(),
    }
    db.users.insert_one(u)
    return u


def by_email(e):
    db = get_db()
    return db.users.find_one({"email": e.lower().strip()}) if db is not None else None


def check(u, p):
    return bool(u and bcrypt.checkpw(p.encode(), u["password_hash"].encode()))
