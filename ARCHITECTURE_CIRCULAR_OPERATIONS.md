# CIRCULINK Circular Operations Architecture

## Core business flow

1. A verified **Company** creates a material demand request.
2. The request can include an optional suggested amount. The amount is not mandatory at request creation.
3. A verified **Individual** selects an open request, chooses a registered **Source / Collector**, records quantity delivered and the transaction amount, and submits a fulfillment record.
4. The Source confirms receipt. An administrator can also verify a fulfillment when an operational exception requires an override.
5. Verification creates a settlement snapshot. The snapshot records the system commission, source share, individual share, source service fee, individual service fee and points calculation that were active at that moment.
6. Source and individual payout records enter a payout queue. The current project records the payable amounts; actual provider disbursement should be connected to an appropriate Safaricom payout/B2C service before production payout execution.
7. Verified individual participation creates points in an immutable point ledger. The user's balance is updated only after verification.
8. Individuals can request redemption once the configured minimum is reached. Redemptions are separated from the points ledger and remain auditable.
9. Administrators control commission, shares, service fees, points-per-kg, point value and minimum redemption from the admin interface.
10. Historical fulfillments retain a `rules_snapshot`, so later pricing changes do not rewrite previous calculations.
11. CIRCULINK certificates can be issued to companies or contributors. Certificates have a unique number, status and PDF representation and can be publicly checked at `/verify/certificate/<certificate_no>`.

## Collections

- `material_requests`: company demand and lifecycle.
- `fulfillments`: collection/delivery evidence and verification state.
- `payouts`: source and individual settlement queue.
- `point_ledger`: earned and redeemed point events.
- `point_redemptions`: conversion requests.
- `certificates`: contributor and company compliance records.
- `contact_messages`: platform inbox and email-delivery state.
- `settings`: configurable finance and contributor rules.

## Money model

For a gross transaction, the configured system commission is removed first. The remaining distributable amount is split using the configured source and individual shares. Service fees are then calculated independently for each beneficiary. Every calculation is stored in the fulfillment's settlement snapshot.

The application deliberately separates **calculation** from **payment execution**. A production payout provider must be connected before automatically sending money to external wallets/accounts.

## Contributor levels

Default thresholds are:

- Beginner: below 1,500 points
- Intermediate: 1,500+ points
- Super: 5,000+ points

Administrators can change the thresholds. Certificate colors follow the requested visual hierarchy: yellow, pale yellow and green.

## Reliability controls

- Verified accounts participate in operational flows.
- Source confirmation is required before points and payout records are created.
- Admin verification is available as an operational override.
- Financial rules are snapshotted per transaction.
- Database indexes support request, fulfillment, payout, points, certificates and inbox queries.
- Certificate numbers are unique.
- Contact messages are persisted even when SMTP delivery is unavailable.
