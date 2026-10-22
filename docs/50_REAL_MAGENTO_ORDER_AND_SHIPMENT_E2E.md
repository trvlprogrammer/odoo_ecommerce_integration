# Real Magento Order and Shipment E2E

## Odoo 19

| Magento order | Odoo sale order | Amount | Product result |
|---|---|---|---|
| 35 | SO48 / 000000034 | 43.00 | Configurable child `E2E-CONF-RED`, qty 2, price 15 |
| 36 | SO49 / 000000035 | 24.20 | Virtual `E2E-VIRTUAL-1`, qty 1, no delivery picking |
| 37 | SO50 / 000000036 | 76.00 | Phantom kit `E2E-KIT-1`, qty 2; moves A x4 and B x2 |
| 38 | SO51 / 000000037 | 85.50 | `SCALE10K-00002`, qty 5 |

All four orders were imported through the real queue and finished with
`financial_check = matched`.

### Partial shipment

Order 38 was delivered in two steps:

| Odoo picking | Delivered | Magento shipment | Magento item | Qty |
|---|---|---|---|---|
| 48 | 2 of 5 | 9 | 43 | 2 |
| 49 (backorder) | 3 of 5 | 10 | 43 | 3 |

The second shipment is the regression case for the shipment-coordinator fix.
The Magento shipment total is 5, equal to the ordered quantity.

The same behavior was proven for order 35 and order 37:

| Magento order | Odoo pickings | Magento shipments | Shipped total |
|---|---|---|---|
| 35 configurables | 46, 52 | 11, 12 | 2 |
| 37 kit | 47, 53 | 13, 14 | 2 |

A repeated shipment scan created no extra mapping or Magento shipment:
6 mappings, 6 remote shipment IDs, and 6 Magento shipment documents.

## Odoo 18 and 17 combined orders

One combined Magento order was executed on each version. Each contained the
configurable child, virtual product, kit, and a simple product.

| Version | Magento order | Odoo sale order | Items shipped | Shipments |
|---|---|---|---|---|
| 18.0 | 39 | SO46 / 000000038 | configurable 2, kit 1, simple 2 | 15, 16 |
| 17.0 | 40 | SO47 / 000000039 | configurable 2, kit 1, simple 2 | 17, 18 |

The virtual line produced no stock move and no Magento shipment line. The kit
was exploded through the Odoo phantom BOM, and the shipment service converted
component quantities back to the single Magento kit order item.

## Assertions

- Magento order item quantities equal the sum of the shipment quantities.
- Odoo picking state is `done`; the remaining demand is on a linked backorder.
- Shipment mappings are `shipped`; repeated scans are idempotent.
- No duplicate Magento shipments were created for an already-mapped picking.
