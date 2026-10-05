from datetime import datetime
from app.db import get_db
from app.utils.ids import new
def log(actor,action,entity="",meta=None,ip=""):
    get_db().audit_logs.insert_one({"_id":new("aud_"),"actor_id":actor,"action":action,"entity":entity,"metadata":meta or {},"ip":ip,"created_at":datetime.utcnow()})
