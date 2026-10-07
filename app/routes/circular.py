from flask import Blueprint, render_template, request, redirect, flash, send_file
from io import BytesIO
from app.utils.auth import required, user
from app.db import get_db
from app.services.circular import create_request, create_fulfillment, confirm_fulfillment, redeem_points, point_balance, finance_settings
from app.services.compliance import contributor_level, pdf_bytes

circular_bp = Blueprint("circular", __name__, url_prefix="/circular")

def _current(): return user()

@circular_bp.route("/requests", methods=["GET", "POST"])
@required
def requests_page():
    db = get_db(); u = _current()
    if request.method == "POST":
        if u.get("account_type") != "company":
            flash("Only company accounts can create material demand requests.", "error")
        else:
            try:
                create_request(u, request.form); flash("Material request published for matching.", "success")
            except Exception as exc: flash(str(exc), "error")
        return redirect("/circular/requests")
    mine = list(db.material_requests.find({"company_id": u["_id"]}).sort("created_at", -1)) if db is not None else []
    open_requests = list(db.material_requests.find({"status": "OPEN"}).sort("created_at", -1).limit(50)) if db is not None and u.get("account_type") != "company" else []
    return render_template("circular/requests.html", user=u, mine=mine, open_requests=open_requests)

@circular_bp.route("/request/<request_id>", methods=["GET", "POST"])
@required
def request_detail(request_id):
    db = get_db(); u = _current(); req = db.material_requests.find_one({"_id": request_id}) if db is not None else None
    if not req: return render_template("error.html", code=404, title="Request not found", message="The material request could not be found."), 404
    if request.method == "POST":
        if u.get("account_type") != "individual":
            flash("Only individual accounts can submit a collection-to-source fulfillment.", "error")
        else:
            try:
                source = db.users.find_one({"_id": request.form.get("source_id"), "account_type":"source"})
                if not source: raise ValueError("Select a registered source/collector location.")
                create_fulfillment(request_id, source, u, request.form); flash("Fulfillment submitted and awaiting source verification.", "success")
            except Exception as exc: flash(str(exc), "error")
        return redirect(f"/circular/request/{request_id}")
    fulfillments = list(db.fulfillments.find({"request_id": request_id}).sort("created_at", -1))
    sources = list(db.users.find({"account_type":"source", "verified":True}, {"password_hash":0}).sort("name",1)) if db is not None else []
    return render_template("circular/request_detail.html", request=req, fulfillments=fulfillments, user=u, finance=finance_settings(), sources=sources)

@circular_bp.post("/fulfillment/<fulfillment_id>/confirm")
@required
def confirm(fulfillment_id):
    try:
        confirm_fulfillment(fulfillment_id, _current()["_id"])
        flash("Delivery verified. Payouts and points have been created.", "success")
    except Exception as exc: flash(str(exc), "error")
    return redirect(request.referrer or "/dashboard/")

@circular_bp.route("/wallet", methods=["GET", "POST"])
@required
def wallet():
    db = get_db(); u = _current()
    if request.method == "POST":
        try: redeem_points(u["_id"], request.form.get("points", 0), request.form.get("payout_method", "M-Pesa")); flash("Redemption request submitted for review.", "success")
        except Exception as exc: flash(str(exc), "error")
        return redirect("/circular/wallet")
    ledger = list(db.point_ledger.find({"user_id":u["_id"]}).sort("created_at",-1).limit(50)) if db is not None else []
    redemptions = list(db.point_redemptions.find({"user_id":u["_id"]}).sort("created_at",-1)) if db is not None else []
    return render_template("circular/wallet.html", user=u, balance=point_balance(u["_id"]), ledger=ledger, redemptions=redemptions, finance=finance_settings())

@circular_bp.get("/certificates/<certificate_id>/pdf")
@required
def certificate_pdf(certificate_id):
    db = get_db(); c = db.certificates.find_one({"_id": certificate_id}) if db is not None else None
    if not c: return "Certificate not found", 404
    u = _current()
    if u.get("role") != "ADMIN" and c.get("owner_id") != u.get("_id"): return "Forbidden", 403
    return send_file(BytesIO(pdf_bytes(c)), mimetype="application/pdf", as_attachment=True, download_name=f"{c['certificate_no']}.pdf")
