# Cross-Version Dashboard Verification

## KPI accuracy

| Version | Database | Products | Mapped | Unmapped | Orders | Issues |
|---|---|---:|---:|---:|---:|---:|
| 19 | e2e_accept_19 | 14 | 13 | 1 | 7 | 0 |
| 18 | hard_upgrade18 | 9 | 8 | 1 | 5 | 0 |
| 17 | hard_upgrade17 | 9 | 8 | 1 | 5 | 0 |

Expected and actual counts matched exactly on all three versions.

## Odoo 19

- Populated Dashboard loaded with real data after the 10k run.
- Product mappings drill-down opened 10,000+ filtered mapping records.
- Company switcher moved the Dashboard to Company B; Company B showed its own
  Backend, Store, mapping, order, and invoice counts with zero JS errors.
- Screenshots: `/tmp/listing-final/screens/dashboard.png`,
  `/tmp/listing-final/screens/dashboard_company_b.png`.

## Odoo 18

- Populated Dashboard loaded from `hard_upgrade18` with real KPI values.
- Provider/backend/Store/filter controls rendered.
- No page errors.
- Screenshot: `/tmp/listing-final/screens/dashboard18.png`.

## Odoo 17

- Populated Dashboard loaded via `/web#action=563` from `hard_upgrade17`.
- Real KPI values rendered.
- No page errors.
- Screenshot: `/tmp/listing-final/screens/dashboard17.png`.

## 18/17 populated Company B

- Company B fixtures were created in `hard_upgrade18` and `hard_upgrade17`.
- Company A: 7 orders, 5 invoices.
- Company B: 1 order, 1 invoice, 1 issue.
- Native company switcher selected B; provider/backend/Store/date/Reset/mapped
  drill-down passed.
- Screenshots: `docs/screenshots/dashboard18_company_b.png`,
  `docs/screenshots/dashboard17_company_b.png`.
- Odoo's native company switcher exposes one active company at a time; combined
  simultaneous browser selection was not exercised.
