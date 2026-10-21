# Dashboard Multi-Company Verification — Odoo 17 and 18

## Odoo 18 fixture

- Company A: id 1; Store 4 (`default`).
- Company B: id 4; Backend 10; Store 5 (`fixture-b`).
- Company A: 7 eCommerce orders, 5 invoices.
- Company B: 1 eCommerce order, 1 invoice, 1 open issue.
- Browser Company B: 2 products, 1 mapped, 1 unmapped, 50% coverage.
- Provider/backend/Store filters, date change, Reset, and mapped-product
  drill-down passed.
- Screenshot: `docs/screenshots/dashboard18_company_b.png`.
- Console: no JS/page errors after website logo/favicon fixture assets.

## Odoo 17 fixture

- Same Company A/B shape on `hard_upgrade17`.
- Company A: 7 orders, 5 invoices.
- Company B: 1 order, 1 invoice, 1 issue.
- Browser Company B: 2 products, 1 mapped, 1 unmapped, 50% coverage.
- Provider/backend/Store filters, date change, Reset, and mapped-product
  drill-down passed via hash route.
- Screenshot: `docs/screenshots/dashboard17_company_b.png`.
- Console: no JS/page errors.

## Limit

The native Odoo company switcher selects one active company at a time; company
A and B Dashboards were exercised separately. The combined allowed-company
selector was not browser-interacted as a simultaneous multi-select.
