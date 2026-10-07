from datetime import datetime
from app.db import get_db

DEFAULTS = {"tax_enabled": True, "tax_percent": 0.0, "service_fee_percent": 0.0, "pickup_fee": 0.0, "currency": "KES"}


def settings():
    db = get_db()
    if db is None:
        return DEFAULTS.copy()
    doc = db.settings.find_one({"key": "pricing"}) or {}
    value = {**DEFAULTS, **(doc.get("value") or {})}
    return value


def calculate(subtotal, pickup_fee=None):
    cfg = settings()
    subtotal = round(float(subtotal), 2)
    service_fee = round(subtotal * float(cfg.get("service_fee_percent", 0)) / 100, 2)
    pickup = round(float(cfg.get("pickup_fee", 0) if pickup_fee is None else pickup_fee), 2)
    taxable = subtotal + service_fee + pickup
    tax = round(taxable * float(cfg.get("tax_percent", 0)) / 100, 2) if cfg.get("tax_enabled") else 0.0
    total = round(taxable + tax, 2)
    return {"subtotal": subtotal, "service_fee": service_fee, "pickup_fee": pickup, "tax": tax,
            "tax_percent": float(cfg.get("tax_percent", 0)), "service_fee_percent": float(cfg.get("service_fee_percent", 0)), "total": total}
