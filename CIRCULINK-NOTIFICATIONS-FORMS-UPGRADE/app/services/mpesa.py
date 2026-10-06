import base64
from datetime import datetime

import requests
from requests import RequestException
from flask import current_app


def callback_url(request):
    """Return the configured production callback URL when available.

    Falling back to the forwarded request origin keeps local/dev deployments
    working while avoiding proxy-origin issues on Vercel in production.
    """
    configured = current_app.config.get("MPESA_CALLBACK_URL")
    if configured:
        return configured.rstrip("/")

    forwarded_host = request.headers.get("X-Forwarded-Host") or request.host
    forwarded_proto = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()
    return f"{forwarded_proto}://{forwarded_host}/api/mpesa/callback"


def _daraja_url(path):
    return current_app.config["DARAJA_BASE_URL"].rstrip("/") + path


def token():
    c = current_app.config
    raw = base64.b64encode(
        f"{c['MPESA_CONSUMER_KEY']}:{c['MPESA_CONSUMER_SECRET']}".encode()
    ).decode()

    try:
        response = requests.get(
            _daraja_url("/oauth/v1/generate?grant_type=client_credentials"),
            headers={"Authorization": "Basic " + raw},
            timeout=(10, 30),
        )
    except requests.Timeout as exc:
        current_app.logger.warning("Daraja OAuth request timed out: %s", exc)
        raise RuntimeError(
            "Safaricom M-Pesa service did not respond in time. Please try again."
        ) from exc
    except RequestException as exc:
        current_app.logger.exception("Daraja OAuth connection failed")
        raise RuntimeError("Could not connect to Safaricom M-Pesa services.") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {"errorMessage": response.text[:500]}

    if response.status_code >= 400:
        message = (
            payload.get("errorMessage")
            or payload.get("error_description")
            or payload.get("errorCode")
            or "Daraja authentication failed"
        )
        raise RuntimeError(f"Daraja authentication failed: {message}")

    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Daraja authentication failed: no access token was returned.")
    return access_token


def stk(request, phone, amount, ref, desc):
    c = current_app.config
    required = [
        "MPESA_CONSUMER_KEY",
        "MPESA_CONSUMER_SECRET",
        "MPESA_BUSINESS_SHORT_CODE",
        "MPESA_PASSKEY",
    ]
    if not all(c.get(key) for key in required):
        return {"ok": False, "error": "Daraja credentials are not configured."}

    normalized = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if normalized.startswith("0"):
        normalized = "254" + normalized[1:]
    elif normalized.startswith("7") and len(normalized) == 9:
        normalized = "254" + normalized

    if not (normalized.startswith("2547") and len(normalized) == 12):
        return {
            "ok": False,
            "error": "Enter a valid Kenyan M-Pesa number, for example 2547XXXXXXXX.",
        }

    try:
        amount_int = int(float(amount))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Invalid M-Pesa payment amount."}

    if amount_int <= 0:
        return {"ok": False, "error": "M-Pesa payment amount must be greater than zero."}

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{c['MPESA_BUSINESS_SHORT_CODE']}{c['MPESA_PASSKEY']}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": c["MPESA_BUSINESS_SHORT_CODE"],
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": c["MPESA_TRANSACTION_TYPE"],
        "Amount": amount_int,
        "PartyA": normalized,
        "PartyB": c["MPESA_VENDOR_TILL"] or c["MPESA_BUSINESS_SHORT_CODE"],
        "PhoneNumber": normalized,
        "CallBackURL": callback_url(request),
        "AccountReference": str(ref)[:12],
        "TransactionDesc": str(desc)[:20],
    }

    try:
        access_token = token()
        response = requests.post(
            _daraja_url("/mpesa/stkpush/v1/processrequest"),
            json=payload,
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
            },
            # Separate connect/read timeouts prevent a dead network connection
            # from hanging the Vercel function indefinitely.
            timeout=(10, 60),
        )
    except requests.Timeout as exc:
        current_app.logger.warning("Daraja STK request timed out: %s", exc)
        return {
            "ok": False,
            "error": "Safaricom M-Pesa service did not respond in time. Please try again.",
            "error_code": "DARaja_TIMEOUT",
            "callback_url": payload["CallBackURL"],
        }
    except RequestException as exc:
        current_app.logger.exception("Daraja STK connection failed")
        return {
            "ok": False,
            "error": "Could not connect to Safaricom M-Pesa services. Please try again.",
            "error_code": "DARAJA_CONNECTION_ERROR",
            "callback_url": payload["CallBackURL"],
        }
    except RuntimeError as exc:
        current_app.logger.warning("Daraja authentication failed: %s", exc)
        return {
            "ok": False,
            "error": str(exc),
            "error_code": "DARAJA_AUTH_ERROR",
            "callback_url": payload["CallBackURL"],
        }
    except Exception as exc:
        current_app.logger.exception("Unexpected Daraja STK error")
        return {
            "ok": False,
            "error": "M-Pesa payment could not be started. Please try again.",
            "error_code": "DARAJA_REQUEST_ERROR",
            "callback_url": payload["CallBackURL"],
        }

    try:
        data = response.json()
    except ValueError:
        data = {"errorMessage": response.text[:1000]}

    if response.status_code >= 400:
        error = (
            data.get("errorMessage")
            or data.get("ResultDesc")
            or data.get("errorCode")
            or "Daraja request failed"
        )
        return {
            "ok": False,
            "error": error,
            "raw": data,
            "http_status": response.status_code,
            "callback_url": payload["CallBackURL"],
        }

    return {"ok": True, "data": data, "callback_url": payload["CallBackURL"]}


def parse(payload):
    x = payload.get("Body", {}).get("stkCallback", {})
    meta = {
        i.get("Name"): i.get("Value")
        for i in x.get("CallbackMetadata", {}).get("Item", [])
    }
    return {
        "result_code": x.get("ResultCode"),
        "result_desc": x.get("ResultDesc"),
        "receipt": meta.get("MpesaReceiptNumber"),
        "checkout_request_id": x.get("CheckoutRequestID"),
    }


def query_stk(checkout_request_id):
    c=current_app.config
    if not checkout_request_id: return {"ok":False,"error":"Checkout request ID is missing."}
    timestamp=datetime.now().strftime("%Y%m%d%H%M%S")
    password=base64.b64encode(f"{c['MPESA_BUSINESS_SHORT_CODE']}{c['MPESA_PASSKEY']}{timestamp}".encode()).decode()
    payload={"BusinessShortCode":c["MPESA_BUSINESS_SHORT_CODE"],"Password":password,"Timestamp":timestamp,"CheckoutRequestID":checkout_request_id}
    try:
        access=token()
        r=requests.post(_daraja_url("/mpesa/stkpushquery/v1/query"),json=payload,headers={"Authorization":"Bearer "+access,"Content-Type":"application/json"},timeout=(10,45))
        try: data=r.json()
        except ValueError: data={"errorMessage":r.text[:500]}
        if r.status_code>=400: return {"ok":False,"error":data.get("errorMessage") or data.get("ResultDesc") or "STK query failed","data":data}
        return {"ok":True,"data":data}
    except Exception as exc:
        current_app.logger.warning("STK query failed: %s",exc)
        return {"ok":False,"error":"Safaricom status query could not be completed."}
