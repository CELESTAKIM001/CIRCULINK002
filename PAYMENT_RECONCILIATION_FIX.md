# CIRCULINK M-Pesa transaction reconciliation fix

## What was happening

The STK Push endpoint correctly created a transaction with `awaiting_callback` after Safaricom accepted the prompt. The final `paid` state depended on either:

1. Safaricom reaching `/api/mpesa/callback`, or
2. the customer checkout page polling `/api/mpesa/status/<order_id>` and the Daraja STK Query returning a confirmed result.

If the callback was delayed or the customer left the checkout page, the admin monitor could continue showing `awaiting_callback` even when the provider had already processed the payment.

## Changes

- Callback URL normalization now guarantees the `/api/mpesa/callback` path is present.
- `PUBLIC_APP_URL` is used as a production fallback before proxy-derived host values.
- Every successful Daraja STK Query response is persisted as `provider_query` with `last_reconciled_at`.
- Admin payments now has a per-transaction **Reconcile** action.
- Admin payments now has **Reconcile pending payments** for up to 50 pending transactions.
- Successful reconciliation updates both the transaction and order to `paid` and records the M-Pesa receipt.
- Reconciliation is idempotent; an already-paid transaction is not paid twice.

## Required Vercel environment variables

Set these in the Vercel project Production environment:

```text
DARAJA_BASE_URL=https://api.safaricom.co.ke
MPESA_CONSUMER_KEY=...
MPESA_CONSUMER_SECRET=...
MPESA_BUSINESS_SHORT_CODE=...
MPESA_PASSKEY=...
MPESA_TRANSACTION_TYPE=CustomerBuyGoodsOnline
MPESA_VENDOR_TILL=...
MPESA_CALLBACK_URL=https://circulink002.vercel.app/api/mpesa/callback
PUBLIC_APP_URL=https://circulink002.vercel.app
```

After changing environment variables, redeploy the Vercel deployment.

## Important

An STK prompt being delivered does **not** by itself mean money was received. CIRCULINK must only mark a transaction `paid` when the Daraja callback or an authenticated Daraja STK Query returns `ResultCode = 0` and a receipt is available.
