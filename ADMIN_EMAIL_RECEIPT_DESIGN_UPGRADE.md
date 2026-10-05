# CIRCULINK Admin + Email + Receipt Design Upgrade

This package preserves the existing CIRCULINK application and applies a unified visual system to the secondary admin pages while leaving the Command Center dashboard design intact.

## Included
- Unified responsive admin design for users, listings, payments, requests, revenue, payouts, finance, certificates, plans, inbox, notifications, M-Hub, settings and audit pages.
- Redesigned personal transaction/receipt ledger with responsive KPI cards, searchable register and expandable payment details.
- Branded OTP verification emails with CIRCULINK logo, expiry/security messaging and mobile-friendly HTML.
- Branded payment receipt emails with logo, payment summary, PDF attachment and an embedded QR code.
- Receipt PDF retains CIRCULINK branding and QR verification.
- Public receipt verification page styled as a secure verification card.
- Existing payment state and graceful-email behavior remain intact: email delivery does not determine whether payment is successful.

## Email configuration
Configure the existing SMTP variables in `.env`/deployment environment:
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`.

## Important
The QR code verifies against the public CIRCULINK receipt route. Set `PUBLIC_APP_URL` or `FRONTEND_URL` to the production application URL when generating receipts outside an active request.
