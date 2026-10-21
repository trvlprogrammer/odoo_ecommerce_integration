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

## Limits

- 18/17 now additionally verify provider/backend/Store filters, date change,
  Reset, and mapped-product drill-down with zero console errors. Odoo 19 also
  covers company switching and the 10k mapping drill-down.
