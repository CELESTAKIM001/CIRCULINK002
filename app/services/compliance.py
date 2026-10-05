from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import landscape,A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
from app.db import get_db
from app.utils.ids import new

LEVELS={"BEGINNER":{"label":"BEGINNER CONTRIBUTOR","fill":colors.HexColor("#f3df78")},"INTERMEDIATE":{"label":"INTERMEDIATE CONTRIBUTOR","fill":colors.HexColor("#f0e5a6")},"SUPER":{"label":"SUPER CONTRIBUTOR","fill":colors.HexColor("#9bd49b")}}
def now(): return datetime.now(timezone.utc)
def contributor_level(points):
    db=get_db()
    if db is not None:
        r=db.settings.find_one({"key":"contributor_levels"}) or {}; v=r.get("value",{})
        if points>=int(v.get("super",5000)): return "SUPER"
        if points>=int(v.get("intermediate",1500)): return "INTERMEDIATE"
    return "BEGINNER"
def verification_url(cert):
    from flask import current_app,request,has_request_context
    origin=request.url_root.rstrip("/") if has_request_context() else current_app.config.get("PUBLIC_APP_URL","").rstrip("/")
    return f"{origin}/verify/certificate/{cert['certificate_no']}"
def create_certificate(owner,certificate_type="CONTRIBUTOR",level="BEGINNER",period=""):
    db=get_db()
    if db is None: raise RuntimeError("Database is not configured.")
    no="CIRC-"+new("CERT").replace("CERT","").upper()
    doc={"_id":new("cert_"),"certificate_no":no,"owner_id":owner["_id"],"owner_name":owner.get("name","") or owner.get("company_name","") or owner.get("email",""),"account_type":owner.get("account_type","individual"),"certificate_type":certificate_type,"level":level,"period":period,"status":"VALID","issued_at":now(),"verification_version":"2026.10"}
    db.certificates.insert_one(doc); return doc
def pdf_bytes(cert):
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=landscape(A4)); w,h=landscape(A4)
    c.setFillColor(colors.HexColor("#f8fbf8")); c.rect(0,0,w,h,fill=1,stroke=0)
    c.setStrokeColor(colors.HexColor("#168447")); c.setLineWidth(4); c.roundRect(25,25,w-50,h-50,16,fill=0,stroke=1)
    # watermark
    logo=Path(__file__).resolve().parents[2]/"static"/"img"/"circulink-logo-transparent.png"
    if logo.exists():
        c.saveState(); c.translate(w/2,h/2); c.rotate(0); c.setFillAlpha(0.08); c.drawImage(ImageReader(str(logo)),-130,-90,260,180,preserveAspectRatio=True,mask="auto"); c.restoreState()
    if logo.exists(): c.drawImage(ImageReader(str(logo)),45,h-105,75,55,preserveAspectRatio=True,mask="auto")
    c.setFillColor(colors.HexColor("#173c2a")); c.setFont("Helvetica-Bold",28); c.drawCentredString(w/2,h-72,"CIRCULINK")
    c.setFillColor(colors.HexColor("#3379a8")); c.setFont("Helvetica-Bold",10); c.drawCentredString(w/2,h-90,"TUNA TAKA TAKA · VERIFIED CIRCULAR PARTICIPATION")
    lev=LEVELS.get(cert.get("level"),LEVELS["BEGINNER"])
    c.setFillColor(lev["fill"]); c.roundRect(w/2-185,h-170,370,46,12,fill=1,stroke=0)
    c.setFillColor(colors.HexColor("#173126")); c.setFont("Helvetica-Bold",15); c.drawCentredString(w/2,h-154,lev["label"])
    c.setFillColor(colors.HexColor("#4d5f55")); c.setFont("Helvetica",13); c.drawCentredString(w/2,h-205,"This certifies that")
    c.setFillColor(colors.HexColor("#17251b")); c.setFont("Helvetica-Bold",25); c.drawCentredString(w/2,h-238,cert.get("owner_name", ""))
    typ="Company Compliance" if cert.get("certificate_type")=="COMPLIANCE" else "Contributor Recognition"
    c.setFillColor(colors.HexColor("#4d5f55")); c.setFont("Helvetica",12); c.drawCentredString(w/2,h-264,f"has a verified CIRCULINK {typ.lower()} record.")
    c.drawCentredString(w/2,h-283,"The record is verifiable through the public certificate verification service.")
    # QR
    qr=qrcode.make(verification_url(cert)); qrb=BytesIO(); qr.save(qrb,"PNG"); qrb.seek(0)
    c.drawImage(ImageReader(qrb),w-150,50,90,90,mask="auto"); c.setFont("Helvetica-Bold",7); c.setFillColor(colors.HexColor("#173126")); c.drawCentredString(w-105,42,"SCAN TO VERIFY")
    c.setFont("Helvetica-Bold",9); c.drawString(55,74,"CERTIFICATE NO."); c.setFont("Helvetica",9); c.drawString(135,74,cert.get("certificate_no",""))
    c.setFont("Helvetica-Bold",9); c.drawString(55,58,"STATUS"); c.setFont("Helvetica",9); c.drawString(105,58,cert.get("status","VALID"))
    c.setFont("Helvetica-Bold",9); c.drawRightString(w-170,74,"ISSUED"); c.setFont("Helvetica",9); c.drawRightString(w-170,58,str(cert.get("issued_at",now()))[:10])
    c.setFillColor(colors.HexColor("#708078")); c.setFont("Helvetica",7); c.drawString(55,39,"Issued by CIRCULINK · Built by GEOPRAM TECHNOLOGIES and friends during M-Hub 2026, Nyeri")
    c.save(); return buf.getvalue()
