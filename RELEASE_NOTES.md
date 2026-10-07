# CIRCULINK — Vercel-ready upgrade release

This release preserves the existing CIRCULINK Flask/Python + MongoDB + Daraja application and applies additive upgrades rather than replacing the working platform.

## Included
- Existing marketplace, dashboards, admin, payments, receipts, certificates, circular operations, pickup and M-Pesa reconciliation modules preserved.
- Sample HTML design retained as `docs/reference/Circulink_Platform.original.html` and used as the visual reference for the upgrade.
- Server-authoritative checkout: browser-submitted price/total is ignored; current MongoDB listing price and stock are used.
- MongoDB transaction protects stock/order creation; sold-out listings are marked `sold_out`.
- MongoDB 2dsphere index support for listing coordinates.
- OTP hardening: hashed OTP storage, expiry, attempt limit and IP resend throttling.
- Secure session-cookie defaults and additional HTTP security headers.
- Hourly Vercel cron for safe cleanup of unreferenced media older than 12 hours.
- Vercel deployment environment template and production checklist.
- Original source ZIP retained under `archives/` strictly as rollback reference; it is not required by the application.

## Do not upload secrets
The release contains no production `.env` file. Set secrets in Vercel Project Settings > Environment Variables.

## Before live money
Configure MongoDB Atlas, production Daraja credentials, registered HTTPS callback URLs, Safaricom approval, transactional email, domain DNS/authentication, CRON_SECRET, and any required legal/payment-service arrangements.
