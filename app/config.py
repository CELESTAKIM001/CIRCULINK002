import os
class Config:
    SECRET_KEY=os.getenv("SECRET_KEY","")
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE","true").lower()=="true"
    SESSION_COOKIE_HTTPONLY=True
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_COOKIE_SAMESITE","Lax")
    CRON_SECRET=os.getenv("CRON_SECRET","")
    JWT_EXPIRES_DAYS=int(os.getenv("JWT_EXPIRES_DAYS","30"))
    MONGODB_URI=os.getenv("MONGODB_URI",""); MONGODB_DB=os.getenv("MONGODB_DB","circulink")
    FRONTEND_URL=os.getenv("FRONTEND_URL","http://localhost:5000"); PUBLIC_APP_URL=os.getenv("PUBLIC_APP_URL",FRONTEND_URL)
    OTP_EXPIRY_MINUTES=int(os.getenv("OTP_EXPIRY_MINUTES","10")); OTP_RESEND_COOLDOWN_SECONDS=int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS","60")); OTP_MAX_ATTEMPTS=int(os.getenv("OTP_MAX_ATTEMPTS","5"))
    ADMIN_EMAIL=os.getenv("ADMIN_EMAIL","circulink1@gmail.com").lower()
    DARAJA_BASE_URL=os.getenv("DARAJA_BASE_URL","https://api.safaricom.co.ke"); MPESA_ENV=os.getenv("MPESA_ENV","production")
    MPESA_CONSUMER_KEY=os.getenv("MPESA_CONSUMER_KEY",""); MPESA_CONSUMER_SECRET=os.getenv("MPESA_CONSUMER_SECRET","")
    MPESA_TRANSACTION_TYPE=os.getenv("MPESA_TRANSACTION_TYPE","CustomerBuyGoodsOnline"); MPESA_BUSINESS_SHORT_CODE=os.getenv("MPESA_BUSINESS_SHORT_CODE","")
    MPESA_VENDOR_TILL=os.getenv("MPESA_VENDOR_TILL",""); MPESA_PASSKEY=os.getenv("MPESA_PASSKEY",""); MPESA_CALLBACK_URL=os.getenv("MPESA_CALLBACK_URL","")
    SMTP_HOST=os.getenv("SMTP_HOST","smtp.gmail.com"); SMTP_PORT=int(os.getenv("SMTP_PORT","587")); SMTP_USERNAME=os.getenv("SMTP_USERNAME",""); SMTP_PASSWORD=os.getenv("SMTP_PASSWORD","")
    SMTP_FROM=os.getenv("SMTP_FROM","CIRCULINK <circulink1@gmail.com>"); SMTP_USE_TLS=os.getenv("SMTP_USE_TLS","true").lower()=="true"
    CLOUDINARY_CLOUD_NAME=os.getenv("CLOUDINARY_CLOUD_NAME",""); CLOUDINARY_API_KEY=os.getenv("CLOUDINARY_API_KEY",""); CLOUDINARY_API_SECRET=os.getenv("CLOUDINARY_API_SECRET","")
