# Real E2E Execution Checkpoint

Date: 2026-10-22

## Scope

This checkpoint records the final real-Magento execution after the release
candidate had already passed the regression suites. A real Magento 2 instance
(`http://127.0.0.1:8083`) was used for every transaction below. No fake
Magento response was used for real-E2E evidence.

## Executed scenarios

| Scenario | Odoo 19 | Odoo 18 | Odoo 17 |
|---|---|---|---|
| Configurable product order | PASS, order 35 / SO48 | PASS, order 39 / SO46 | PASS, order 40 / SO47 |
| Virtual/service product order | PASS, order 36 / SO49, no picking | PASS, order 39 / SO46 | PASS, order 40 / SO47 |
| Phantom-kit order | PASS, order 37 / SO50, A x2 + B x1 per kit | PASS, order 39 / SO46 | PASS, order 40 / SO47 |
| Partial shipment and backorder | PASS, order 38 / SO51, qty 2 + 3 | PASS, order 39 / SO46 | PASS, order 40 / SO47 |
| Variant-level image ownership | PASS, E2E-CONF-RED | PASS unit contract | PASS unit contract |
| Invoice and payment | PASS, orders 35-38 | PASS, order 39 | PASS, order 40 |
| Partial credit memo | PASS, order 38, memo 3 | PASS, order 39, memo 5 | PASS, order 40, memo 6 |
| Late/full credit memo | PASS, order 38, memo 4 | PASS auto-registration | PASS auto-registration |

## Defects found and fixed

1. The shipment coordinator only scanned order mappings above its cursor. A
   backorder created on an already-scanned order was therefore never exported.
   Fixed by adding unmapped completed outgoing pickings to the scan.
2. Auto refund registration reconciled receivable lines twice on modern Odoo
   and used `account.payment.line_ids`, which no longer exists. Fixed by
   reconciling only unreconciled receivable lines and using the payment move.
3. Configurable child media was imported onto the parent template. Child media
   is now written to `image_variant_1920` and variant-owned `product.image`
   records, leaving the parent image untouched.

## Regression status

Fresh test databases were created for this checkpoint:

| Version | Core tests | Magento tests | Result |
|---|---|---|---|
| 19.0 | 20 | 60 | 80/80 PASS |
| 18.0 | 20 | 60 | 80/80 PASS |
| 17.0 | 20 | 60 | 80/80 PASS |

## Remaining contract boundary

Magento RMA is explicitly outside the connector contract. Refunds are
synchronized from Magento credit memos, including shipping and item lines.
Physical return-to-stock workflows are not claimed by this release.
