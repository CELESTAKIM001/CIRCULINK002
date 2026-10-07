# Deployment checklist

1. Create the `circulink` MongoDB database.
2. Add the variables from `.env.example` in Vercel.
3. Put real Daraja production credentials into Vercel only.
4. Put a Gmail App Password into `SMTP_PASSWORD`.
5. Deploy with `vercel.json`; Python entrypoint is `api/index.py`.
6. Test `/api/health`.
7. Register the configured admin email and verify its OTP.
8. Test a small Daraja transaction in the intended production environment.
9. Confirm the Daraja callback reaches `/api/mpesa/callback`.
10. Confirm the transaction changes from `initiated` to `paid` only after callback.
11. Confirm receipt email and QR validation.
