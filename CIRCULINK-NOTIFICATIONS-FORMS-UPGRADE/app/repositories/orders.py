from datetime import datetime
from app.db import get_db
from app.utils.ids import new
from app.services.pricing import calculate

def create(buyer, items, subtotal, pickup_fee=None):
    pricing = calculate(subtotal, pickup_fee)
    x = {"_id": new("ord_"), "buyer_id": buyer, "items": items, **pricing,
         "total": pricing["total"], "status": "pending_payment", "payment_status": "pending",
         "created_at": datetime.utcnow()}
    get_db().orders.insert_one(x)
    return x
