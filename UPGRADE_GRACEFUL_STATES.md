# CIRCULINK graceful progress, success and failure upgrade

This production upgrade keeps the original CIRCULINK application and assets, then adds:

- Full Flask HTTP handling for 400, 401, 403, 404, 405, 409, 422, 429, 500, 502 and 503. API requests receive structured JSON errors with request IDs; normal pages receive a branded recovery page.
- `X-Request-ID` on responses so support can trace a failure in logs.
- Global form progress feedback without changing server-side success/error flash messages.
- M-Pesa STK state handling for request sent, provider confirmation, payment success, failure, timeout and reconciliation. A provider-query failure is never silently converted into a payment failure.
- Duplicate active STK prevention when a user double-clicks or refreshes.
- Callback acknowledgement that stays safe for Safaricom even when MongoDB is temporarily unavailable; the payment status endpoint can reconcile an active transaction through STK Query.
- Receipt delivery after either the Daraja callback **or** STK Query confirms payment. This fixes the case where the callback is delayed but payment is actually successful.
- Receipt email delivery is recorded as `sent`, `failed` or `unavailable`; SMTP failure never changes a confirmed payment back to failed.
- Retry receipt-email endpoint for confirmed payments, plus a direct PDF receipt download.
- QR-backed public receipt verification and a graceful 404 when a receipt does not exist.
- Health endpoint reports `ready` only when MongoDB can answer a ping.

## Production email

Set `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_HOST`, `SMTP_PORT` and `SMTP_USE_TLS`. A confirmed M-Pesa payment remains valid even when SMTP is down. The customer is told that the receipt can be downloaded instead.

## Production M-Pesa callback

Set `MPESA_CALLBACK_URL` to the exact deployed public URL ending in `/api/mpesa/callback`. The callback route is intentionally unauthenticated because Safaricom must reach it. The customer-facing payment status endpoint provides a reconciliation fallback through Daraja STK Query.
