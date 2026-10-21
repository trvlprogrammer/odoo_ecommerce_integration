# Multi-Company and Security Audit

## Verified controls

- Read-only eCommerce users denied Store and Magento synchronization actions.
- Wizards require Operator access server-side.
- Store company/backend reassignment blocked after dependent records exist.
- Backend company change blocked while Stores exist.
- Queue jobs created with Store company and allowed-company context.
- Queue metadata includes provider/backend/Store.
- Mapping target company validation passes cross-company rejection test.
- Stock helper filters Stores by the move/quant company.
- Dashboard intersects requested companies with `env.companies`.
- Dashboard queue counts use narrowly scoped `sudo` aggregates with explicit
  company domain; queue drill-down requires queue manager.
- Magento SSRF/private-network checks retained.
- Magento uninstall only deletes Magento-owned job method names.

## Runtime evidence

- Odoo 19 queue job company test passes.
- Odoo 19 cross-company stock Store discovery test passes.
- Odoo 19 uninstall isolation:
  - Magento `_job_preflight` removed.
  - Core `action_view_jobs` job retained.
  - Two unrelated jobs retained.
  - Core module remained installed.

## Remaining risks

- A full company-A-to-company-B real Magento order/inventory execution was not
  run against two live Magento stores.
- Historical queue jobs have no provider metadata and remain unclassified.
- Odoo 18 and 17 uninstall isolation also passed: Magento job removed, core and
  unrelated jobs retained, core module remained installed.
- Actual worker restart was executed during the 10k Odoo 19 run; OCA resumed the
  run to exact completion without duplicate mappings.
