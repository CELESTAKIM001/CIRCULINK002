from datetime import datetime, timezone
from uuid import uuid4
from flask import Blueprint, jsonify, render_template, request, current_app
from app.db import get_db
from app.services.mpesa import parse, stk, query_stk
from app.services.payment_receipts import deliver_once
from app.utils.auth import required, user

payments_bp = Blueprint("payments", __name__)


def _now():
    return datetime.now(timezone.utc)


def _find_order(db, order_id, uid):
    return db.orders.find_one({"_id": order_id, "buyer_id": uid}) if db is not None else None


def _finalize_paid(db, tx, order, receipt=None, provider_data=None):
    """Idempotently finalize a confirmed M-Pesa payment.

    Safaricom STK Query can confirm ResultCode=0 without returning the
    MpesaReceiptNumber. A confirmed provider result must still move the order
    to PAID; the receipt is attached later if the callback supplies it.
    """
    set_fields = {
        "status": "paid",
        "provider_query": provider_data or tx.get("provider_query"),
        "updated_at": _now(),
    }
    if receipt:
        set_fields["mpesa_receipt"] = receipt

    db.transactions.update_one({"_id": tx["_id"]}, {"$set": set_fields})

    order_fields = {
        "status": "paid",
        "payment_status": "paid",
        "updated_at": _now(),
    }
    if receipt:
        order_fields["mpesa_receipt"] = receipt
    db.orders.update_one({"_id": order["_id"]}, {"$set": order_fields})

    tx = db.transactions.find_one({"_id": tx["_id"]}) or tx
    if not receipt:
        return tx, "pending"

    buyer = db.users.find_one({"_id": order.get("buyer_id")})
    email_status = deliver_once(db, tx, order, buyer, receipt)
    return db.transactions.find_one({"_id": tx["_id"]}) or tx, email_status


@payments_bp.get("/pay/<order_id>")
@required
def pay(order_id):
    db = get_db()
    order = _find_order(db, order_id, user()["_id"])
    if not order:
        return render_template(
            "error.html", code=404, title="Order not found",
            message="This checkout could not be found, has expired, or does not belong to this account.",
            retry_url="/marketplace/", retry_label="Return to marketplace"
        ), 404
    return render_template("marketplace/checkout.html", order=order), 200


@payments_bp.get("/api/mpesa/status/<order_id>")
@required
def status(order_id):
    db = get_db()
    if db is None:
        return jsonify(ok=False, error="The payment database is temporarily unavailable. Please retry.", retryable=True), 503

    order = _find_order(db, order_id, user()["_id"])
    if not order:
        return jsonify(ok=False, code=404, error="Order not found."), 404

    tx = db.transactions.find_one({"order_id": order_id, "user_id": user()["_id"]}, sort=[("created_at", -1)])
    email_status = (tx or {}).get("receipt_email_status") or ("sent" if (tx or {}).get("receipt_email_sent") else "pending")
    provider_message = None

    if tx and tx.get("status") in {"awaiting_callback", "processing", "pending"} and tx.get("checkout_request_id"):
        q = query_stk(tx["checkout_request_id"])
        data = q.get("data") or {}
        code = data.get("ResultCode")
        provider_message = data.get("ResultDesc") or q.get("error")
        if q.get("ok"):
            # Persist every provider query so an administrator can see what
            # Safaricom actually returned even when the callback is delayed.
            db.transactions.update_one(
                {"_id": tx["_id"]},
                {"$set": {"provider_query": data, "last_reconciled_at": _now(), "updated_at": _now()}}
            )
        if q.get("ok") and code is not None:
            try:
                code_int = int(code)
            except (TypeError, ValueError):
                code_int = 99
            if code_int == 0:
                # STK Query confirms the payment even when its response does
                # not contain the final M-Pesa receipt number. Do not leave a
                # successful customer payment stuck in awaiting_callback.
                receipt = tx.get("mpesa_receipt") or data.get("MpesaReceiptNumber")
                tx, email_status = _finalize_paid(db, tx, order, receipt, data)
                provider_message = data.get("ResultDesc") or "Safaricom confirmed the payment."
            elif code_int in (1037, 4999):
                # Provider has not reached a conclusive state yet.
                db.transactions.update_one(
                    {"_id": tx["_id"]},
                    {"$set": {"provider_query": data, "last_reconciled_at": _now(), "updated_at": _now()}}
                )
            else:
                # Includes user cancellation (1032), insufficient funds (1)
                # and other terminal provider errors.
                db.transactions.update_one(
                    {"_id": tx["_id"]},
                    {"$set": {
                        "status": "failed",
                        "provider_query": data,
                        "failure_reason": data.get("ResultDesc") or "Safaricom reported a failed STK transaction.",
                        "updated_at": _now(),
                    }}
                )
                tx = db.transactions.find_one({"_id": tx["_id"]}) or tx
        elif not q.get("ok"):
            # A temporary provider-query failure is not a payment failure.
            if tx.get("status") not in {"paid", "failed"}:
                db.transactions.update_one({"_id": tx["_id"]}, {"$set": {"last_query_error": q.get("error"), "updated_at": _now()}})

    # If the callback arrived and payment is already paid, retry a failed receipt email.
    if tx and tx.get("status") == "paid" and tx.get("mpesa_receipt") and not tx.get("receipt_email_sent"):
        buyer = db.users.find_one({"_id": order.get("buyer_id")})
        email_status = deliver_once(db, tx, order, buyer, tx["mpesa_receipt"])
        tx = db.transactions.find_one({"_id": tx["_id"]}) or tx

    return jsonify(
        ok=True,
        status=(tx or {}).get("status", "pending"),
        order_status=order.get("status"),
        payment_status=order.get("payment_status", "pending"),
        receipt=(tx or {}).get("mpesa_receipt"),
        amount=order.get("total"),
        checkout_request_id=(tx or {}).get("checkout_request_id"),
        email_status=email_status,
        provider_message=provider_message,
        retryable=(tx or {}).get("status") in {"awaiting_callback", "processing", "pending"},
    )


@payments_bp.post("/api/mpesa/stkpush")
@required
def start():
    d = request.get_json(silent=True) or {}
    db = get_db()
    if db is None:
        return jsonify(ok=False, error="The payment database is temporarily unavailable. Please try again.", retryable=True), 503

    uid = user()["_id"]
    o = _find_order(db, d.get("order_id"), uid)
    if not o:
        return jsonify(ok=False, code=404, error="Order not found."), 404
    if o.get("payment_status") == "paid" or o.get("status") == "paid":
        return jsonify(ok=False, error="This order is already paid.", status="paid"), 409

    # Do not create multiple active STK requests for the same order when a user double-clicks.
    active = db.transactions.find_one({
        "order_id": o["_id"], "user_id": uid,
        "status": {"$in": ["awaiting_callback", "processing", "pending"]},
    }, sort=[("created_at", -1)])
    if active and active.get("checkout_request_id"):
        return jsonify(
            ok=True, reused=True, status=active.get("status"),
            checkout_request_id=active.get("checkout_request_id"),
            message="A payment request is already waiting for confirmation. Check your phone."
        ), 200

    phone = d.get("phone") or user().get("phone")
    r = stk(request, phone, o["total"], o["_id"], "CIRCULINK material purchase")
    data = r.get("data") or {}
    tx = {
        "_id": uuid4().hex,
        "order_id": o["_id"], "user_id": uid, "amount": o["total"],
        "status": "awaiting_callback" if r.get("ok") else "failed",
        "daraja": r,
        "checkout_request_id": data.get("CheckoutRequestID"),
        "merchant_request_id": data.get("MerchantRequestID"),
        "created_at": _now(), "updated_at": _now(),
    }
    db.transactions.insert_one(tx)
    if r.get("ok"):
        return jsonify({**r, "status": "awaiting_callback", "message": "Payment request sent. Check your phone and enter your M-Pesa PIN."}), 200
    return jsonify({**r, "status": "failed", "retryable": True}), 502


@payments_bp.post("/api/mpesa/receipt/<order_id>/retry-email")
@required
def retry_receipt_email(order_id):
    db = get_db()
    if db is None:
        return jsonify(ok=False, error="The receipt service is temporarily unavailable. Please try again.", retryable=True), 503
    order = _find_order(db, order_id, user()["_id"])
    if not order:
        return jsonify(ok=False, error="Order not found."), 404
    tx = db.transactions.find_one({"order_id": order_id, "user_id": user()["_id"], "status": "paid", "mpesa_receipt": {"$exists": True}}, sort=[("created_at", -1)])
    if not tx:
        return jsonify(ok=False, error="A confirmed receipt is not available yet."), 404
    buyer = db.users.find_one({"_id": order.get("buyer_id")})
    status = deliver_once(db, tx, order, buyer, tx.get("mpesa_receipt"))
    if status in {"sent", "already_sent"}:
        return jsonify(ok=True, email_status=status, message="Receipt email has been sent to your registered email."), 200
    if status == "unavailable":
        return jsonify(ok=False, email_status=status, error="Email delivery is not configured for this account. You can download the receipt PDF instead."), 503
    return jsonify(ok=False, email_status="failed", error="Receipt email could not be delivered yet. The payment remains confirmed; please try again later.", retryable=True), 502


@payments_bp.post("/api/mpesa/callback")
def callback():
    payload = request.get_json(silent=True) or {}
    checkout_hint = payload.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
    current_app.logger.info("Daraja callback received: %s", checkout_hint)
    x = parse(payload)
    db = get_db()

    # Safaricom must receive a 200 acknowledgement even when our DB is temporarily down.
    if db is None:
        current_app.logger.error("Daraja callback received while MongoDB is unavailable; reconciliation required: %s", checkout_hint)
        return jsonify(ResultCode=0, ResultDesc="Accepted for reconciliation"), 200

    checkout_id = x.get("checkout_request_id")
    tx = db.transactions.find_one({"checkout_request_id": checkout_id}) if checkout_id else None
    if not tx and checkout_id:
        tx = db.transactions.find_one({"daraja.data.CheckoutRequestID": checkout_id})
    if not tx:
        db.mpesa_callbacks.insert_one({
            "_id": uuid4().hex, "checkout_request_id": checkout_id,
            "payload": payload, "created_at": _now(),
        })
        return jsonify(ResultCode=0, ResultDesc="Accepted; transaction will be reconciled"), 200

    # Never allow a late/duplicate callback to downgrade an already confirmed
    # transaction.
    if tx.get("status") == "paid":
        if x.get("result_code") == 0 and x.get("receipt") and not tx.get("mpesa_receipt"):
            o = db.orders.find_one({"_id": tx.get("order_id")})
            if o:
                _finalize_paid(db, tx, o, x["receipt"], x)
        return jsonify(ResultCode=0, ResultDesc="Accepted"), 200

    if x.get("result_code") == 0:
        o = db.orders.find_one({"_id": tx.get("order_id")})
        if o:
            # Callback success is authoritative even if receipt metadata is
            # temporarily absent. The receipt can be attached by a later
            # callback/query without reversing the paid state.
            tx, email_status = _finalize_paid(db, tx, o, x.get("receipt"), x)
            current_app.logger.info(
                "Payment confirmed: order=%s receipt=%s email=%s",
                o.get("_id"), x.get("receipt"), email_status
            )
        else:
            db.transactions.update_one(
                {"_id": tx["_id"]},
                {"$set": {"status": "processing", "callback": x, "updated_at": _now()}}
            )
    else:
        db.transactions.update_one(
            {"_id": tx["_id"]},
            {"$set": {
                "status": "failed",
                "callback": x,
                "failure_reason": x.get("result_desc") or "Safaricom reported a failed payment.",
                "updated_at": _now(),
            }}
        )

    return jsonify(ResultCode=0, ResultDesc="Accepted"), 200
