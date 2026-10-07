from datetime import datetime
from app.db import get_db
from app.utils.ids import new
def create(d,uid):
    x={"_id":new("pup_"),"requester_id":uid,"listing_id":d.get("listing_id"),"location":{"name":d["location_name"],"lat":float(d["lat"]),"lng":float(d["lng"])},"scheduled_for":d["scheduled_for"],"notes":d.get("notes",""),"status":"requested","created_at":datetime.utcnow()}
    get_db().pickups.insert_one(x);return x
