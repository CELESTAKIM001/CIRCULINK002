from io import BytesIO
from flask import Blueprint, jsonify, render_template, send_file
from app.db import get_db
from app.services.receipt import pdf as receipt_pdf

receipt_bp = Blueprint("receipt", __name__)


def _record(receipt):
    db = get_db()
    if db is None:
        return None
    return db.transactions.find_one({"mpesa_receipt": receipt})


@receipt_bp.get("/verify/receipt/<receipt>")
def verify(receipt):
    db = get_db()
    if db is None:
        return render_template("receipt/verify.html", valid=False, receipt=receipt, unavailable=True), 503
    x = _record(receipt)
    if not x:
        return render_template("receipt/verify.html", valid=False, receipt=receipt, unavailable=False), 404
    return render_template("receipt/verify.html", valid=x.get("status") == "paid", receipt=receipt, transaction=x, unavailable=False)


@receipt_bp.get("/receipt/<receipt>")
def validate(receipt):
    db = get_db()
    if db is None:
        return jsonify({"service": "CIRCULINK", "receipt": receipt, "valid": False, "error": "Verification service temporarily unavailable", "retryable": True}), 503
    x = _record(receipt)
    if not x:
        return jsonify({"service": "CIRCULINK", "receipt": receipt, "valid": False, "error": "Receipt not found"}), 404
    return jsonify({"service": "CIRCULINK", "receipt": receipt, "valid": x.get("status") == "paid",
                    "record": {"receipt": x.get("mpesa_receipt"), "amount": x.get("amount"), "status": x.get("status"), "created_at": x.get("created_at")}})


@receipt_bp.get("/receipt/<receipt>/pdf")
def download(receipt):
    x = _record(receipt)
    if not x or x.get("status") != "paid":
        return render_template("error.html", code=404, title="Receipt not available", message="The confirmed payment receipt could not be found yet. If payment was just completed, wait a moment and try again.", retry_url=f"/verify/receipt/{receipt}", retry_label="Check receipt"), 404
    db = get_db()
    order = db.orders.find_one({"_id": x.get("order_id")}) if db is not None else None
    if not order:
        return render_template("error.html", code=404, title="Receipt order not found", message="The payment was recorded, but its order details are temporarily unavailable. Please contact support with the receipt reference.", retry_url=f"/verify/receipt/{receipt}", retry_label="View verification"), 404
    return send_file(BytesIO(receipt_pdf(order, receipt)), mimetype="application/pdf", as_attachment=True, download_name=f"CIRCULINK-{receipt}.pdf")
