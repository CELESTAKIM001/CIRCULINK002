# CIRCULINK — TUNA TAKA TAKA

CIRCULINK is a Flask + MongoDB circular-material marketplace designed for Vercel. It connects material sources and collectors with people and companies looking for reusable, repairable or recoverable inputs.

## Vercel deployment

1. Import the project into Vercel.
2. Keep the Python entrypoint at `api/index.py` and `vercel.json` unchanged.
3. Add the variables in `.env.example` as Vercel Environment Variables.
4. Put the real MongoDB, Daraja and Gmail credentials only in Vercel. Do not commit them.
5. Set `FRONTEND_URL` and `PUBLIC_APP_URL` to the deployed CIRCULINK origin.
6. `MPESA_CALLBACK_URL` is retained for environment compatibility, but the STK implementation dynamically builds the callback as `<request-origin>/api/mpesa/callback`.

## Payment configuration

- Daraja environment: production
- Business Short Code: configured by `MPESA_BUSINESS_SHORT_CODE`
- Receiving Till: configured separately by `MPESA_VENDOR_TILL`
- Transaction type: `CustomerBuyGoodsOnline`
- Callback endpoint: `/api/mpesa/callback`
- STK initiation is stored as `initiated` or `failed`.
- The transaction is only marked `paid` after the Daraja callback reports success.
- Provider error text is retained in the transaction record for Admin → Payments.
- A successful transaction generates a branded PDF receipt with a validation QR code and sends it through SMTP.

## Important 500-error fix

PyMongo `Database` objects must not be used in boolean expressions. The previous build contained expressions such as:

```python
if db:
```

and:

```python
... if db else ...
```

Those caused:

`NotImplementedError: Database objects do not implement truth value testing or bool(). Please compare with None instead.`

The rebuilt project uses explicit `db is not None` checks and adds guarded database-unavailable states.

## UI rebuild

The responsive UI was rebuilt around a Microsoft Fluent-inspired system:

- Segoe UI / Segoe UI Variable typography
- Fluent-style spacing, borders, surfaces and controls
- Fluent SVG interface icons
- Responsive navigation with mobile menu
- Responsive marketplace cards
- Responsive admin command center
- Mobile-friendly forms
- Horizontally scrollable data tables where tables require more width
- Responsive cart drawer
- Responsive Leaflet maps
- Accessible focus states and reduced-motion support
- No emojis and no generic AI/chat visual language

The CIRCULINK logo is used from `static/img/logo.png` and the landing page displays it in a two-second startup screen.
## CIRCULINK visual refresh

The current build uses the supplied CIRCULINK circular-recovery logo as a transparent PNG across the startup screen, header, hero and footer. The startup screen is shown for about 2 seconds and respects reduced-motion preferences.

The responsive UI is designed for desktop, tablet and mobile widths, with navigation, marketplace, pickup, dashboard, authentication and contact links preserved. Vercel is configured with a filesystem-first route so `/static/*` assets are served before the Flask catch-all.

## Production media, receipts and finance upgrade

CIRCULINK listings now require at least one genuine photo. Uploads accept JPG/JPEG/PNG/WEBP, are validated and converted to optimized WebP in memory, then uploaded to Cloudinary. MongoDB stores the resulting media URL and metadata; Vercel's local filesystem is not used as permanent media storage.

Required Vercel variables:

- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

The receipt QR code resolves to the public verification route `/verify/receipt/<receipt>`. When a receipt is generated during an HTTP request, the deployed request origin is used rather than a hard-coded development host; `PUBLIC_APP_URL` remains the fallback for non-request contexts.

Administrators can control transaction tax, service-fee percentage and pickup/delivery charges at `/admin/settings`. Each order stores the rates and amounts used at the time of checkout so historical receipts remain stable.

The listing form includes Leaflet/OpenStreetMap location selection. Listing coordinates are stored with the listing and exposed through `/api/map/locations` and `/api/map/nearby` for map display and distance-based discovery.

## Circular Operations Architecture (Mega Upgrade)

CIRCULINK now supports a managed demand-to-recovery workflow:

**Company demand → Individual collection → Source confirmation → Verified settlement → Source/individual payout queue → Individual points → Point redemption → Company/contributor certification.**

Admin controls include:
- System commission percentage
- Source and individual share percentages
- Source and individual service fees
- Points awarded per kilogram
- Point-to-KES conversion value
- Minimum point redemption
- Contributor level thresholds
- Individual/source/company subscription plans
- Platform revenue monitoring
- Material request and fulfillment monitoring
- Payout and redemption queue management
- Compliance certificate issuance
- Platform contact inbox

Financial calculations are retained as a per-fulfillment `rules_snapshot`. This prevents later admin changes from rewriting historical transaction economics.

Actual external payout execution is intentionally separated from the settlement calculation. A production Safaricom payout/B2C integration should be connected before automatically disbursing funds.
