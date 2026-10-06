from flask import Blueprint, current_app, flash, redirect, render_template, request
from app.db import get_db
from app.services.email import send

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def home():
    return render_template("landing.html")


@public_bp.get("/about")
def about():
    return render_template("about.html")


@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please complete your name, email and message.", "error")
            return render_template("contact.html"), 400
        db = get_db()
        delivery = False
        if db is not None:
            from datetime import datetime, timezone
            from app.utils.ids import new
            db.contact_messages.insert_one({"_id":new("msg_"),"name":name,"email":email,"message":message,"status":"NEW","created_at":datetime.now(timezone.utc)})
        subject = f"CIRCULINK contact from {name}"
        html = f"<h2>CIRCULINK contact enquiry</h2><p><b>From:</b> {email}</p><p><b>Name:</b> {name}</p><p>{message}</p>"
        delivery = send(current_app.config["ADMIN_EMAIL"], subject, html)
        if db is not None:
            db.contact_messages.update_one({"email":email,"message":message,"status":"NEW"},{"$set":{"email_delivered":bool(delivery)}})
        if delivery:
            flash("Your message has been received and forwarded to the CIRCULINK team.", "success")
        else:
            flash("Your message has been saved. Email forwarding is temporarily unavailable, but your enquiry is recorded for review.", "warning")
        return redirect("/contact")
    return render_template("contact.html")


@public_bp.get("/sdgs")
def sdgs():
    return render_template("sdgs.html")


@public_bp.get("/verify/certificate/<certificate_no>")
def verify_certificate(certificate_no):
    db=get_db(); cert=db.certificates.find_one({"certificate_no":certificate_no}) if db is not None else None
    return render_template("certificate_verify.html", certificate=cert, certificate_no=certificate_no)
