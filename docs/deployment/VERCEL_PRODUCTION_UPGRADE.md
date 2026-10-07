# CIRCULINK Vercel production upgrade

This build preserves the existing Flask/Python application and its MongoDB + Daraja architecture.

## Required Vercel environment variables
- `SECRET_KEY`: long random secret; never commit it.
- `MONGODB_URI`: MongoDB Atlas connection string.
- `MONGODB_DB`: production database name.
- `PUBLIC_APP_URL`: exact public HTTPS domain.
- `MPESA_ENV=production` only after Safaricom production approval.
- `DARAJA_BASE_URL=https://api.safaricom.co.ke`
- `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_BUSINESS_SHORT_CODE`, `MPESA_VENDOR_TILL`, `MPESA_PASSKEY`
- `MPESA_CALLBACK_URL=https://YOUR-DOMAIN/api/mpesa/callback`
- SMTP/provider variables for OTP, receipts and notifications.
- `CRON_SECRET`: separate random secret used by the media retention cron.

## Inventory protection
Checkout no longer trusts browser prices or quantities. The server reads the current listing price and atomically decrements stock inside a MongoDB transaction. When quantity reaches zero, the listing becomes `sold_out`.

## Media retention
The hourly Vercel cron calls `/api/cron/media-cleanup`. Unreferenced media older than 12 hours is deleted from MongoDB; active listing images are retained.

## Important
MongoDB Atlas must support transactions (replica set / appropriate cluster). Safaricom production approval, registered PayBill/Till, callback registration and any required payment/escrow legal arrangement must be completed before live-money launch.

## OTP hardening
OTP codes are now stored only as hashes, expire after the configured period, stop after five attempts, and include per-IP resend throttling. Do not log OTP values.
