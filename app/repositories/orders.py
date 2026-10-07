from datetime import datetime, timezone
from app.db import get_db
from app.utils.ids import new
from app.services.pricing import calculate

def create(buyer, items, subtotal=None, pickup_fee=None):
    db=get_db()
    if db is None: raise RuntimeError("Database is not configured.")
    if not isinstance(items,list) or not items: raise ValueError("Your cart is empty.")
    now=datetime.now(timezone.utc)
    normalized=[]
    computed_subtotal=0.0
    session=db.client.start_session() if hasattr(db,'client') else None
    try:
        with session.start_transaction():
            for raw in items:
                listing_id=str(raw.get("id") or "")
                qty=float(raw.get("quantity",1))
                if not listing_id or qty<=0: raise ValueError("Each order item must have a valid listing and quantity.")
                listing=db.listings.find_one_and_update(
                    {"_id":listing_id,"status":"active","quantity":{"$gte":qty}},
                    {"$inc":{"quantity":-qty},"$set":{"updated_at":now}},
                    session=session,
                    return_document=__import__('pymongo').ReturnDocument.AFTER
                )
                if not listing: raise ValueError("One or more materials are no longer available in the requested quantity.")
                price=float(listing.get("price",0)); line=round(price*qty,2); computed_subtotal+=line
                normalized.append({"listing_id":listing_id,"title":listing.get("title","Material"),"material":listing.get("material",""),"quantity":qty,"unit":listing.get("unit","unit"),"price":price,"line_total":line,"seller_id":listing.get("owner_id")})
                if listing.get("quantity",0)<=0:
                    db.listings.update_one({"_id":listing_id},{"$set":{"status":"sold_out","sold_out_at":now}},session=session)
            pricing=calculate(computed_subtotal,pickup_fee)
            oid=new("ord_")
            order={"_id":oid,"buyer_id":buyer,"items":normalized,**pricing,"total":pricing["total"],"status":"pending_payment","payment_status":"pending","created_at":now}
            db.orders.insert_one(order,session=session)
            return order
    finally:
        if session: session.end_session()
