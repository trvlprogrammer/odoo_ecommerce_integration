# Dashboard Accuracy Verification

## KPI partition rules

- Eligible products/variants: active saleable records with an internal reference,
  shared (`company_id = False`) or in selected Store companies.
- Mapped products/variants: distinct eligible targets with an active mapping in
  selected Stores.
- Unmapped = max(total - mapped, 0).
- Categories: all `product.public.category` records vs distinct active mapping
  targets.
- Customers: `customer_rank > 0` partners vs distinct active mapping targets.
- Orders: order mappings imported inside the selected date range.
- Revenue: sum of mapped sale-order totals in the date range.
- Queue counts: company + channel `ecommerce%` + integration metadata
  (`ecommerce_provider`, `ecommerce_backend_id`, `ecommerce_store_id`).

## Runtime comparisons

Odoo 19 (`e2e_accept_19`): dashboard matched independent ORM results:
products 14, mapped 13, unmapped 1, orders 7, open issues 0.

Odoo 18 (`hard_upgrade18`): products 9, mapped 8, unmapped 1, orders 5,
open issues 0 — exact match.

Odoo 17 (`hard_upgrade17`): products 9, mapped 8, unmapped 1, orders 5,
open issues 0 — exact match.

## Browser verification

- Odoo 19 populated dashboard: zero page errors; Mapped Products drill-down
  opened Product Mappings with Store scope.
- Odoo 18 populated dashboard: zero page errors; real KPI values rendered.
- Odoo 17 populated dashboard: zero page errors; real KPI values rendered.
- Screenshots:
  - `/tmp/listing-final/screens/dashboard.png`
  - `/tmp/listing-final/screens/dashboard18.png`
  - `/tmp/listing-final/screens/dashboard17.png`

## Queue classification

New jobs are classified by integration-owned metadata. Historical jobs without
metadata remain unclassified and are excluded from filtered provider/backend/
Store queue counts rather than guessed.
