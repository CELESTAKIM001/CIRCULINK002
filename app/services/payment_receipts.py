"""Idempotent payment receipt delivery helpers."""
from datetime import datetime, timezone
from flask import current_app


def _now():
    return datetime.now(timezone.utc)


def deliver_once(db, transaction, order, buyer, receipt):
    """Try to deliver a receipt email without ever making payment depend on SMTP.

    Returns one of: sent, failed, unavailable, already_sent.
    The payment remains authoritative even if email delivery fails.
    """
    if not receipt or not buyer:
        return "unavailable"
    if transaction.get("receipt_email_sent"):
        return "already_sent"

    email = (buyer.get("email") or "").strip().lower()
    if not email:
        db.transactions.update_one(
            {"_id": transaction["_id"]},
            {"$set": {"receipt_email_status": "unavailable", "receipt_email_updated_at": _now()}}
        )
        return "unavailable"

    # Do not block or fail a payment because SMTP is not configured.
    if not current_app.config.get("SMTP_USERNAME") or not current_app.config.get("SMTP_PASSWORD"):
        db.transactions.update_one(
            {"_id": transaction["_id"]},
            {"$set": {"receipt_email_status": "unavailable", "receipt_email_updated_at": _now()}}
        )
        return "unavailable"

    from app.services.receipt import email as receipt_email
    try:
        sent = bool(receipt_email(email, {**order, "mpesa_receipt": receipt}, receipt))
    except Exception:
        current_app.logger.exception("Receipt email delivery failed for %s", receipt)
        sent = False

    if sent:
        db.transactions.update_one(
            {"_id": transaction["_id"]},
            {"$set": {
                "receipt_email_sent": True,
                "receipt_email_status": "sent",
                "receipt_email_sent_at": _now(),
                "receipt_email_updated_at": _now(),
            }}
        )
        return "sent"

    db.transactions.update_one(
        {"_id": transaction["_id"]},
        {"$set": {"receipt_email_status": "failed", "receipt_email_updated_at": _now()}, "$inc": {"receipt_email_attempts": 1}}
    )
    return "failed"
