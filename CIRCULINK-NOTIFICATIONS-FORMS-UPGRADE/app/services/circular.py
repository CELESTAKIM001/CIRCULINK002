from datetime import datetime, timezone
from app.db import get_db
from app.utils.ids import new

DEFAULT_FINANCE = {
    "currency": "KES",
    "system_commission_percent": 10.0,
    "source_share_percent": 60.0,
    "individual_share_percent": 40.0,
    "source_service_fee_percent": 3.0,
    "individual_service_fee_percent": 5.0,
    "points_per_kg": 10.0,
    "points_value_per_unit": 0.10,
    "minimum_redemption_points": 1000,
    "company_certificate_minimum_kg": 100,
}


def now():
    return datetime.now(timezone.utc)


def finance_settings():
    db = get_db()
    if db is None:
        return DEFAULT_FINANCE.copy()
    doc = db.settings.find_one({"key": "circular_finance"}) or {}
    return {**DEFAULT_FINANCE, **doc.get("value", {})}


def save_finance(values):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    clean = {**DEFAULT_FINANCE}
    for key in clean:
        if key == "currency":
            clean[key] = "KES"
        elif key in values:
            clean[key] = float(values[key]) if "percent" in key or "points" in key or "kg" in key else int(values[key])
    db.settings.update_one({"key": "circular_finance"}, {"$set": {"value": clean, "updated_at": now()}}, upsert=True)
    return clean


def calculate_settlement(gross_amount, source_amount=None, individual_amount=None, quantity_kg=0):
    f = finance_settings()
    gross = max(0.0, float(gross_amount or 0))
    commission = round(gross * f["system_commission_percent"] / 100, 2)
    distributable = max(0.0, gross - commission)
    share_total = max(0.01, float(f["source_share_percent"]) + float(f["individual_share_percent"]))
    source_base = float(source_amount) if source_amount is not None else round(distributable * float(f["source_share_percent"]) / share_total, 2)
    individual_base = float(individual_amount) if individual_amount is not None else round(distributable - source_base, 2)
    source_fee = round(source_base * f["source_service_fee_percent"] / 100, 2)
    individual_fee = round(individual_base * f["individual_service_fee_percent"] / 100, 2)
    source_net = round(max(0, source_base - source_fee), 2)
    individual_net = round(max(0, individual_base - individual_fee), 2)
    points = int(max(0, float(quantity_kg or 0)) * f["points_per_kg"])
    return {
        "gross_amount": gross,
        "system_commission": commission,
        "source_gross": round(source_base, 2),
        "source_service_fee": source_fee,
        "source_net": source_net,
        "individual_gross": round(individual_base, 2),
        "individual_service_fee": individual_fee,
        "individual_net": individual_net,
        "points_awarded": points,
        "rules_snapshot": f.copy(),
        "calculated_at": now(),
    }


def create_request(company, form):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    quantity = float(form.get("quantity", 0) or 0)
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    doc = {
        "_id": new("req_"),
        "company_id": company["_id"],
        "company_name": company.get("name", ""),
        "material": form.get("material", "").strip(),
        "description": form.get("description", "").strip(),
        "quantity": quantity,
        "suggested_amount": float(form["suggested_amount"]) if form.get("suggested_amount") else None,
        "location": form.get("location", "").strip(),
        "required_date": form.get("required_date", "").strip(),
        "status": "OPEN",
        "created_at": now(),
        "updated_at": now(),
    }
    if not doc["material"]:
        raise ValueError("Material is required.")
    db.material_requests.insert_one(doc)
    return doc


def request_with_matches(request_id):
    db = get_db()
    if db is None:
        return None, []
    req = db.material_requests.find_one({"_id": request_id})
    matches = list(db.fulfillments.find({"request_id": request_id}).sort("created_at", -1))
    return req, matches


def create_fulfillment(request_id, source, individual, form):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    req = db.material_requests.find_one({"_id": request_id})
    if not req:
        raise ValueError("Request not found.")
    quantity = float(form.get("quantity_kg", 0) or 0)
    amount = float(form.get("gross_amount", 0) or 0)
    if quantity <= 0 or amount <= 0:
        raise ValueError("Quantity and transaction amount must be greater than zero.")
    settlement = calculate_settlement(amount, quantity_kg=quantity)
    doc = {
        "_id": new("ful_"), "request_id": request_id,
        "company_id": req["company_id"], "source_id": source["_id"], "source_name": source.get("name", ""),
        "individual_id": individual["_id"], "individual_name": individual.get("name", ""),
        "material": req["material"], "quantity_kg": quantity, "gross_amount": amount,
        "status": "PENDING_SOURCE_CONFIRMATION", "settlement": settlement,
        "created_at": now(), "updated_at": now(),
    }
    db.fulfillments.insert_one(doc)
    return doc


def confirm_fulfillment(fulfillment_id, source_id):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    f = db.fulfillments.find_one({"_id": fulfillment_id, "source_id": source_id})
    if not f:
        raise ValueError("Fulfillment not found or source is not authorised.")
    if f.get("status") != "PENDING_SOURCE_CONFIRMATION":
        return f
    s = f["settlement"]
    db.fulfillments.update_one({"_id": fulfillment_id}, {"$set": {"status": "VERIFIED", "verified_at": now(), "updated_at": now()}})
    db.platform_revenue.insert_one({"_id": new("rev_"), "fulfillment_id": fulfillment_id, "system_commission": s["system_commission"], "source_service_fee": s["source_service_fee"], "individual_service_fee": s["individual_service_fee"], "total_revenue": round(s["system_commission"] + s["source_service_fee"] + s["individual_service_fee"], 2), "currency":"KES", "created_at": now()})
    db.payouts.insert_many([
        {"_id": new("pay_"), "fulfillment_id": fulfillment_id, "beneficiary_id": f["source_id"], "beneficiary_type": "SOURCE", "gross": s["source_gross"], "fee": s["source_service_fee"], "net": s["source_net"], "status": "QUEUED", "created_at": now()},
        {"_id": new("pay_"), "fulfillment_id": fulfillment_id, "beneficiary_id": f["individual_id"], "beneficiary_type": "INDIVIDUAL", "gross": s["individual_gross"], "fee": s["individual_service_fee"], "net": s["individual_net"], "status": "QUEUED", "created_at": now()},
    ])
    if s["points_awarded"]:
        db.point_ledger.insert_one({"_id": new("pt_"), "user_id": f["individual_id"], "fulfillment_id": fulfillment_id, "type": "EARN", "points": s["points_awarded"], "description": f"Verified {f['quantity_kg']} kg of {f['material']}", "created_at": now()})
        db.users.update_one({"_id": f["individual_id"]}, {"$inc": {"points_balance": s["points_awarded"], "lifetime_points": s["points_awarded"]}})
    db.material_requests.update_one({"_id": f["request_id"]}, {"$set": {"status": "FULFILLED", "updated_at": now()}})
    return db.fulfillments.find_one({"_id": fulfillment_id})


def point_balance(user_id):
    db = get_db()
    if db is None:
        return 0
    u = db.users.find_one({"_id": user_id}, {"points_balance": 1}) or {}
    return int(u.get("points_balance", 0))


def redeem_points(user_id, points, payout_method="M-Pesa"):
    db = get_db()
    if db is None:
        raise RuntimeError("Database is not configured.")
    f = finance_settings()
    points = int(points)
    balance = point_balance(user_id)
    if points < int(f["minimum_redemption_points"]):
        raise ValueError(f"Minimum redemption is {int(f['minimum_redemption_points'])} points.")
    if points > balance:
        raise ValueError("Insufficient points balance.")
    value = round(points * float(f["points_value_per_unit"]), 2)
    redemption = {"_id": new("red_"), "user_id": user_id, "points": points, "value": value, "currency": "KES", "payout_method": payout_method, "status": "PENDING_REVIEW", "rules_snapshot": f.copy(), "created_at": now()}
    db.point_redemptions.insert_one(redemption)
    db.point_ledger.insert_one({"_id": new("pt_"), "user_id": user_id, "type": "REDEEM", "points": -points, "description": f"Redemption request {redemption['_id']}", "created_at": now()})
    db.users.update_one({"_id": user_id}, {"$inc": {"points_balance": -points}})
    return redemption
