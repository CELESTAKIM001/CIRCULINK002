"""Small, self-contained image storage for Vercel + MongoDB.
Uploads are normalized to compact WebP and stored in MongoDB as base64 bytes.
No Cloudinary or external image URL is required.
"""
from io import BytesIO
from datetime import datetime, timezone
from base64 import b64encode
from PIL import Image, ImageOps, UnidentifiedImageError
from app.db import get_db
from app.utils.ids import new

ALLOWED={"image/jpeg","image/png","image/webp"}
MAX_BYTES=5*1024*1024
MAX_DIMENSION=1200
QUALITY=68

def upload(file_storage, folder="circulink/media"):
    if not file_storage or not file_storage.filename: raise ValueError("Choose an image to upload.")
    if (file_storage.mimetype or "").lower() not in ALLOWED: raise ValueError("Only JPG, PNG and WEBP images are allowed.")
    raw=file_storage.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError("Images must be 5 MB or smaller before optimization.")
    try:
        im=Image.open(BytesIO(raw)); im.verify(); im=Image.open(BytesIO(raw))
    except (UnidentifiedImageError,OSError) as exc: raise ValueError("The uploaded file is not a valid image.") from exc
    im=ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((MAX_DIMENSION,MAX_DIMENSION),Image.Resampling.LANCZOS)
    out=BytesIO(); im.save(out,format="WEBP",quality=QUALITY,method=6)
    data=out.getvalue()
    if len(data)>700_000:
        out=BytesIO(); im.save(out,format="WEBP",quality=55,method=6); data=out.getvalue()
    db=get_db()
    if db is None: raise RuntimeError("Database is not configured for image storage.")
    media_id=new("med_")
    db.media.insert_one({"_id":media_id,"folder":folder,"content_type":"image/webp","data":b64encode(data).decode("ascii"),"bytes":len(data),"width":im.width,"height":im.height,"created_at":datetime.now(timezone.utc)})
    return {"media_id":media_id,"secure_url":f"/api/media/{media_id}","public_id":media_id,"width":im.width,"height":im.height,"format":"webp","bytes":len(data)}
