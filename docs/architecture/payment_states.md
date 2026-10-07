# Payment States

CIRCULINK treats a confirmed Safaricom provider result as authoritative for the
payment state.

## State flow

`awaiting_callback` → `processing` → `paid`

A transaction can also move from any non-paid state to `failed` when Safaricom
returns a terminal failure result.

## Confirmation paths

1. **Daraja callback** at `/api/mpesa/callback`.
2. **STK Query fallback** from the customer checkout status endpoint.
3. **Administrator reconciliation** from `/admin/payments`.

All three paths use the same idempotent payment finalization logic.

## Important receipt behavior

STK Query can confirm `ResultCode=0` without returning the final
`MpesaReceiptNumber`. CIRCULINK therefore records the transaction and order as
`paid` immediately when the provider result is conclusive. The M-Pesa receipt
number is attached later when Safaricom supplies it through the callback or a
provider response.

A payment must never remain `awaiting_callback` solely because the receipt
number was absent from an otherwise successful provider result.

## Terminal and non-terminal query results

- `0`: successful; finalize as `paid`.
- `1037`: provider timeout/pending; retain the pending state.
- `4999`: provider request still unresolved; retain the pending state.
- Other result codes, including user cancellation or insufficient funds, are
treated as terminal failures.

## Idempotency

A late or duplicate callback cannot downgrade an already `paid` transaction.
If a paid transaction has no receipt and a later successful callback includes
one, the receipt is attached and receipt delivery is attempted.

## Admin reconciliation

Administrators can reconcile one pending transaction or all pending
transactions from the payment monitor. Provider query data and reconciliation
timestamps are stored on the transaction for auditability.
