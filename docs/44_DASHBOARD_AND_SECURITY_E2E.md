# Dashboard and Security E2E

## Odoo 19

- Populated Dashboard with 10k mappings.
- Company B switch through native company switcher.
- Provider/backend/Store/date/Reset filters and mapped-product drill-down.
- Company A vs B counts isolated.
- No JS/page errors.

## Odoo 18/17

- Populated Company A + B fixtures.
- Company B browser results: 2 products, 1 mapped, 1 unmapped, 1 order, 1 invoice,
  1 issue.
- Provider/backend/Store/date/Reset/mapped drill-down passed.
- Screenshots: `docs/screenshots/dashboard18_company_b.png`,
  `docs/screenshots/dashboard17_company_b.png`.

## Security

ACL/operator/read-only tests pass. Dashboard server methods intersect requested
companies with `env.companies`. Queue aggregates use narrow sudo with company
scope. Unauthorized-user browser matrix was not created.
