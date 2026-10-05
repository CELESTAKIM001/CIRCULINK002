import secrets
from datetime import datetime,timedelta
from flask import current_app
from app.db import get_db
from app.services.email import send_otp
def issue(email,purpose="verify_email"):
    db=get_db(); now=datetime.utcnow(); prev=db.otps.find_one({"email":email.lower(),"purpose":purpose},sort=[("created_at",-1)])
    if prev and (now-prev["created_at"]).total_seconds()<current_app.config["OTP_RESEND_COOLDOWN_SECONDS"]: raise ValueError("Please wait before requesting another code.")
    code=f"{secrets.randbelow(1000000):06d}";db.otps.update_many({"email":email.lower(),"purpose":purpose,"used":False},{"$set":{"used":True}})
    db.otps.insert_one({"_id":secrets.token_hex(12),"email":email.lower(),"purpose":purpose,"code":code,"attempts":0,"used":False,"created_at":now,"expires_at":now+timedelta(minutes=current_app.config["OTP_EXPIRY_MINUTES"])})
    return bool(send_otp(email,code))
def verify(email,code,purpose="verify_email"):
    db=get_db(); x=db.otps.find_one({"email":email.lower(),"purpose":purpose,"used":False},sort=[("created_at",-1)])
    if not x or datetime.utcnow()>x["expires_at"] or x["attempts"]>=current_app.config["OTP_MAX_ATTEMPTS"]: return False
    if x["code"]!=code: db.otps.update_one({"_id":x["_id"]},{"$inc":{"attempts":1}}); return False
    db.otps.update_one({"_id":x["_id"]},{"$set":{"used":True}}); return True
