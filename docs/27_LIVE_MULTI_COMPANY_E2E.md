# Live Multi-Company Magento E2E

Status: **PARTIAL** — business-record company isolation passed; a separate live
Magento store-view order could not be created through the available REST flow.

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
- Therefore the live order/finance/inventory isolation was executed against the
  same Magento store view but two independent Odoo companies/backends/stores.

## Actual records

- Magento order 9 (`000000009`) was imported into Company B:
  - order mapping 31, company 5, Store 7
  - Sale Order 21, company 5, warehouse 7, state `sale`, total 42.95
- Finance:
  - Invoice mapping 14, company 5
  - Posted invoice company 5, total 42.95
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

Odoo company isolation for real order, invoice, inventory, queue metadata, and
Dashboard is demonstrated. Full separate Magento store-view order isolation is
**BLOCKED by the local Magento cart/order REST behavior**, not by the Odoo
connector. This is a release limitation, not a claimed PASS for two independent
Magento store views.
