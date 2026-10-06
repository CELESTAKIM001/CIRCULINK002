import jwt
from datetime import datetime,timedelta,timezone
from flask import current_app
def issue(user_id): return jwt.encode({"sub":user_id,"exp":datetime.now(timezone.utc)+timedelta(days=current_app.config["JWT_EXPIRES_DAYS"])},current_app.config["SECRET_KEY"],algorithm="HS256")
def decode(token): return jwt.decode(token,current_app.config["SECRET_KEY"],algorithms=["HS256"])
