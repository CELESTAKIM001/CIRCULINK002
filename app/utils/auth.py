from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from app.db import get_db


def user():
    db = get_db()
    uid = session.get("user_id")
    return db.users.find_one({"_id": uid}) if db is not None and uid else None


def login(u):
    session.clear()
    session["user_id"] = u["_id"]
    session.permanent = True


def logout():
    session.clear()


def _is_api():
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not user():
            if _is_api():
                return jsonify(ok=False, code=401, error="Please sign in to continue.", login_url=url_for("auth.login_page")), 401
            flash("Please sign in to continue.", "info")
            return redirect(url_for("auth.login_page"))
        return fn(*a, **k)
    return w


def admin(fn):
    @wraps(fn)
    def w(*a, **k):
        current = user()
        if not current or current.get("role") != "ADMIN":
            if _is_api():
                return jsonify(ok=False, code=403, error="Administrator access is required."), 403
            flash("Administrator access is required.", "error")
            return redirect(url_for("auth.login_page"))
        return fn(*a, **k)
    return w
