# Live Multi-Company Magento E2E

Status: **PASS** — separate Magento store-view order 10 was created and imported.

## Environment

- Odoo 19 `e2e_accept_19`.
- Magento Open Source 2.4.7-p3 local.
- Company A: id 1, Store 4 (`default`).
- Company B: id 5, Backend 14, Store 7 (`magento-b`).
- Company B warehouse 7.
- Magento has store views `default` and `second`; attempts to create an order
  through guest/admin cart APIs with `Store: second` still produced
  `sales_order.store_id=1`. The second view exists but order creation could not
  be isolated to it with the available REST cart flow.
- Magento order 10 was created through `/rest/second/V1/guest-carts` with the
  masked store-2 cart ID. Magento assigned `sales_order.store_id=2`.

## Actual records

- Magento order 10 (`2000000001`, store_id 2) was imported into Company B:
  - order mapping 32, company 5, Store 7
  - Sale Order 22, company 5, warehouse 7, state `sale`, total 42.95
- Magento order 9 (`000000009`) was also isolated in Company B:
  - order mapping 31, company 5, Sale Order 21, total 42.95
- Finance:
  - Invoice mapping 14 for order 9, company 5, posted 42.95
- Invoice mapping 15 for order 10, company 5, posted 42.95
- Inventory:
  - Company B variant mapping for `SCALE10K-09999`
  - Odoo stock 7 pushed to Magento; Magento source item quantity = 7
- Company A stock event:
  - Queue job 218, company 1, Store 4
  - Magento quantity for the B-only SKU remained 7
- Queue metadata:
  - B jobs 211–220 have company 5, Store 7, provider `magento`
  - A stock job 218 has company 1, Store 4
- Dashboard:
  - Company B: 1 mapped product, 1 eCommerce order, 1 invoice
  - Company A: 7 orders
  - Company B Dashboard browser rendered with company B selected, zero errors.

## Conclusion

Odoo company isolation and genuine second Magento store-view order isolation are
demonstrated.
