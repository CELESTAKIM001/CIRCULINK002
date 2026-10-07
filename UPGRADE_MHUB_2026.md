# CIRCULINK M-Hub 2026 Production Upgrade

This build updates the production CIRCULINK application for the M-Hub 2026 / Nyeri innovation build by GEOPRAM TECHNOLOGIES and friends.

## Major changes

- Atlas-style admin Command Center based on the supplied dashboard design.
- Material Flow Map showing company demand, CIRCULINK coordination, individual delivery and collector/source verification.
- Admin-controlled M-Hub 2026 feature banner.
- Administrative CRUD/action controls for activation, verification, approval, rejection, deletion, payout state, certificates, notifications and messages.
- Contributor/admin recognition badges.
- Landscape certificates with CIRCULINK logo watermark and QR verification.
- Public certificate verification route.
- M-Pesa STK callback reconciliation improved with stored CheckoutRequestID and STK status-query fallback.
- Production Daraja endpoint remains `https://api.safaricom.co.ke`.
- Uploaded images are compressed to WebP and stored in MongoDB as compact base64 media records; no Cloudinary image API is required.
- SDG page uses locally bundled visual tiles; no external SDG image URL is embedded.
- Browser copy/right-click deterrence is included for presentation/content protection. This is not a substitute for server-side authorization or DRM.
- Contact messages remain visible to administrators and can be replied to from the admin inbox.
- ROI records continue to separate platform commission/service-fee revenue from beneficiary payouts.

## Important production environment variables

Keep the existing production values in Vercel. Do not commit secrets.

- `MONGODB_URI`
- `MONGODB_DB`
- `SECRET_KEY`
- `MPESA_ENV=production`
- `DARAJA_BASE_URL=https://api.safaricom.co.ke`
- `MPESA_CONSUMER_KEY`
- `MPESA_CONSUMER_SECRET`
- `MPESA_BUSINESS_SHORT_CODE`
- `MPESA_PASSKEY`
- `MPESA_VENDOR_TILL`
- `MPESA_CALLBACK_URL=https://circulink002.vercel.app/api/mpesa/callback`
- SMTP variables for receipts and contact responses

The callback route is public by design because Safaricom must be able to call it. Payment confirmation is based on the provider callback or the STK query reconciliation, never merely on successful STK initiation.
