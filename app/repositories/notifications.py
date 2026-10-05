from datetime import datetime
from app.db import get_db
from app.utils.ids import new
def add(uid,title,message,kind="info"): get_db().notifications.insert_one({"_id":new("not_"),"user_id":uid,"title":title,"message":message,"kind":kind,"read":False,"created_at":datetime.utcnow()})
def for_user(uid): return list(get_db().notifications.find({"user_id":uid}).sort("created_at",-1).limit(50))
