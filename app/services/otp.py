import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app, request
from app.db import get_db
from app.services.email import send_otp

def _hash(code):
    return hashlib.sha256((str(code)+current_app.config["SECRET_KEY"]).encode()).hexdigest()

def issue(email,purpose="verify_email"):
    db=get_db(); now=datetime.now(timezone.utc); email=email.lower().strip(); ip=request.headers.get("X-Forwarded-For",request.remote_addr or "")[:64]
    prev=db.otps.find_one({"email":email,"purpose":purpose},sort=[("created_at",-1)])
    if prev and (now-prev["created_at"]).total_seconds()<current_app.config["OTP_RESEND_COOLDOWN_SECONDS"]:
        raise ValueError("Please wait before requesting another code.")
    recent_ip=db.otps.count_documents({"ip":ip,"created_at":{"$gt":now-timedelta(minutes=10)}})
    if recent_ip>=10: raise ValueError("Too many verification requests from this network. Please wait and try again.")
    code=f"{secrets.randbelow(1000000):06d}"
    db.otps.update_many({"email":email,"purpose":purpose,"used":False},{"$set":{"used":True}})
    db.otps.insert_one({"_id":secrets.token_hex(12),"email":email,"purpose":purpose,"code_hash":_hash(code),"attempts":0,"used":False,"ip":ip,"created_at":now,"expires_at":now+timedelta(minutes=current_app.config["OTP_EXPIRY_MINUTES"])})
    return bool(send_otp(email,code))

def verify(email,code,purpose="verify_email"):
    db=get_db(); email=email.lower().strip(); x=db.otps.find_one({"email":email,"purpose":purpose,"used":False},sort=[("created_at",-1)])
    if not x or datetime.now(timezone.utc)>x["expires_at"] or x["attempts"]>=current_app.config["OTP_MAX_ATTEMPTS"]: return False
    if not secrets.compare_digest(x.get("code_hash", ""),_hash(str(code).strip())):
        db.otps.update_one({"_id":x["_id"]},{"$inc":{"attempts":1}}); return False
    db.otps.update_one({"_id":x["_id"]},{"$set":{"used":True,"verified_at":datetime.now(timezone.utc)}}); return True
