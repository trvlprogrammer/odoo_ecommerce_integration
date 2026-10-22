# Real Magento Invoice, Payment, and Refund E2E

## Invoices and payments

Magento invoices were created through the REST API with capture enabled. Paid
invoices were then imported by the real finance queue.

### Odoo 19

| Magento order | Magento invoice | Odoo invoice | Total | Residual | Odoo inbound payment |
|---|---|---|---|---|---|
| 35 | 8 | INV/2026/00033 | 43.00 | 0.00 | 43.00 |
| 36 | 7 | INV/2026/00034 | 24.20 | 0.00 | 24.20 |
| 37 | 9 | INV/2026/00035 | 76.00 | 0.00 | 76.00 |
| 38 | 10 | INV/2026/00036 | 85.50 | 0.00 | 85.50 |

### Odoo 18 / 17

| Version | Magento order | Magento invoice | Odoo invoice | Total | Odoo inbound payment |
|---|---|---|---|---|---|
| 18.0 | 39 | 11 | INV/2026/00034 | 139.40 | 139.40 |
| 17.0 | 40 | 12 | INV/2026/00035 | 139.40 | 139.40 |

Every invoice mapping was `posted`, every invoice residual was zero, and every
payment mapping was `registered`.

## Partial and late refunds

Order 38 received two Magento credit memos:

| Magento credit memo | Odoo credit note | Amount | Payment result |
|---|---|---|---|
| 3 | RINV/2026/00003 | 49.20 | Outbound 49.20; residual 0.00 |
| 4 | RINV/2026/00004 | 36.30 | Outbound 36.30; residual 0.00 |

Credit memos 3 and 4 total 85.50, exactly the invoice total. Credit memo 3
was first imported while Auto Register Refund was off, so it correctly
remained open. After enabling Auto Register Refund, the pending refund was
registered and the late credit memo was imported and registered automatically.
The fix that prevents double reconciliation was exercised by credit memo 4.

Cross-version refunds:

| Version | Magento order | Credit memo | Odoo credit note | Amount | Residual |
|---|---|---|---|---|---|
| 18.0 | 39 | 5 | RINV/2026/00002 | 110.80 | 0.00 |
| 17.0 | 40 | 6 | RINV/2026/00003 | 110.80 | 0.00 |

Both cross-version refunds generated an outbound Odoo payment through the
repaired auto-refund path.

## Configuration note

Auto Register Refund remains off by default. When it is off, an imported credit
note is intentionally left open for an accountant to refund. This is documented
behavior, not a failure. Enabling it registers the outbound payment and
reconciles the receivable.
