# eCommerce Dashboard

## Ownership and navigation

The Dashboard is a core client action available at **eCommerce → Dashboard** and
is the eCommerce root menu action. It works with only the core and `queue_job`.
Provider metrics are derived from generic Backend/Store/mapping records.

## Filters

- Company multi-select limited to `env.companies`.
- Provider from installed registry entries.
- Backend and Store dynamically restricted by selected companies/provider.
- Date range defaults to the last 30 days.

The server intersects requested companies with the user's allowed companies and
never uses unrestricted sudo for dashboard data.

## KPIs

Products, mapped/unmapped products, product coverage %, mapped/unmapped
variants, mapped/unmapped categories, mapped/unmapped customers, eCommerce
orders, order revenue, invoices, payments, credit notes, shipments, pending/
running/failed queue jobs, and open issues.

Coverage denominators:
- eligible products/variants: active, saleable, with an internal reference,
  shared or in the selected Store companies;
- mapped products/variants: distinct eligible targets with active mappings in
  the selected Stores;
- categories: all `product.public.category` records vs distinct active category
  mappings;
- customers: partners with `customer_rank > 0` vs distinct active customer
  mappings.

Aggregated coverage means “mapped to at least one selected Store”. External
discovered-but-unmapped entities are not invented; the dashboard reports Odoo
mapping coverage only.

## Charts and sections

CSS/SVG-native doughnut and bar charts cover product/variant/category/customer
coverage, orders over time, orders by provider, queue states, and synchronization
activity. Operational sections show runs, failed jobs, open issues, and Store
health. Every applicable KPI/donut drills into a filtered native action preserving
company/store scope.

## Performance and safety

Counts use `search_count`, SQL DISTINCT joins, and `read_group`; no full catalog
load. Loading performs no provider API call and creates no queue jobs. There is no
cross-user cache. Empty states cover no company, no Store, and no runs.

## Known limits

Queue jobs have no provider field; queue counts are company/Store scoped with a
Store identity-key heuristic and may include another provider serving the same
Store. Dashboard Store health shows last-test evidence, not live connectivity.
