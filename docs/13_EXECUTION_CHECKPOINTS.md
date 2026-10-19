# 13 — Execution Checkpoints

## Current checkpoint

| Field | Value |
| --- | --- |
| Phase | **Documentation phase** |
| Date | 2026-10-19 |
| Status | **Documentation complete; final verification passed** |
| Application code | None written |
| Branch changes | None |
| Commits / pushes | None |
| Protected repos | Verified clean at baseline; final check pending |
| Next gate | Documentation acceptance, then M1 on explicit implementation authorization |

## Baseline evidence

| Item | Value |
| --- | --- |
| Workspace | `/home/ridho/Data/odooapps` |
| Core HEAD | `fc49b66f11a04ff011182bffdd168a86aa884ca7` on `main` |
| Magento connector HEAD | `ecea4746619e2fa37f5492c5b9494ff944b07bc0` on `main` |
| SaaS reference HEAD | `d88326de2431311cc80720b23122111ed4dc5dda` on `main` |
| Odoo 19 commit | `20f5882e87e818e94a79ad07ac00530842d7045b` |
| Odoo 18 commit | `8e50ecb100695e2d4c98bf3bd88463f2cfb53cad` |
| Odoo 17 commit | `02d3a1d847bb4c3f784e3b018b581ee4d8f3fe4e` |
| PostgreSQL | `odoo-dev-postgres` exists, stopped |
| Magento | not installed |
| queue_job | not on active addons path; local stale copy exists outside product repos |

Protected repository baseline:

| Repository | HEAD | Dirty |
| --- | --- | --- |
| `move_line_in_picking_list` | `894691104e74e4ca862bf1502286cf85f602f295` | 0 |
| `odoo_advance_chatter` | `c6da242a2e4208fbd0e0b78a871d1cbf55c2326e` | 0 |
| `odoo_sticky_view` | `111afd8d6ad643616d0bfc355c913a522d9cd814` | 0 |
| `order_line_in_order_list` | `fba4274075ae40b41f3db32d262b9500363c42bc` | 0 |
| `po_line_in_po_list` | `5f10e48128b55e8c2a4eb5e13be388752dbe2ebc` | 0 |

## Documents

| File | Status |
| --- | --- |
| `00_PROJECT_BASELINE.md` | complete |
| `01_ARCHITECTURE.md` | complete |
| `02_REPOSITORY_STRUCTURE.md` | complete |
| `03_FEATURE_PARITY_MATRIX.md` | complete |
| `04_DATA_MODELS.md` | complete |
| `05_OCA_QUEUE_JOB_DESIGN.md` | complete |
| `06_MAGENTO_API_ADAPTER.md` | complete |
| `07_MAGENTO_LOCAL_ENVIRONMENT.md` | complete |
| `08_ODOO_19_IMPLEMENTATION_PLAN.md` | complete |
| `09_ODOO_18_17_PORTING_PLAN.md` | complete |
| `10_TESTING_AND_ACCEPTANCE.md` | complete |
| `11_SECURITY_AND_DISTRIBUTION.md` | complete |
| `12_RISKS_AND_DECISIONS.md` | complete |
| `13_EXECUTION_CHECKPOINTS.md` | this file |
| `14_IMPLEMENTATION_HANDOFF.md` | complete |

## Important decisions recorded

- Core/connector split with Magento-only API code in the connector.
- Backend = installation; store = website + store view.
- Product mapping = template; variant mapping = `product.product`.
- Store-scoped external identity and company record rules.
- OCA queue_job only; no custom queue.
- Adopt-before-retry for financial and shipment writes.
- Magento invoice is evidence; Odoo invoice is primary.
- V1 excludes images, complex product types, multi-source MSI, RMA, post-import
  edits, later tracking updates, and refund payment automation.
- Credentials are masked, not field-encrypted; deployment must protect the DB at
  rest (documented limitation).
- Odoo 19 uses `models.Constraint`; 18/17 use `_sql_constraints`.

## Open blockers

These block **implementation**, not the documentation phase:

1. Magento is not installed; M1 must provision the isolated stack.
2. OCA queue_job is not installed on the active Odoo 19 addons path; M1 must
   install a pinned 19.0 revision and `openupgradelib`.
3. Magento Composer/Adobe credentials are required to provision Magento.
4. Dedicated Odoo 19 test database does not exist yet.
5. Odoo Apps/license review and pricing/support terms are not finalized.
6. Decisions D15 (credential encryption), tax mapping, and Magento support line
   remain open for the commercial release.

## Evidence references

- Workspace: `00_PROJECT_BASELINE.md`
- SaaS parity: `03_FEATURE_PARITY_MATRIX.md`
- Data/security: `04_DATA_MODELS.md`, `11_SECURITY_AND_DISTRIBUTION.md`
- Queue API: `05_OCA_QUEUE_JOB_DESIGN.md`; upstream OCA/queue 19.0
- Magento adapter: `06_MAGENTO_API_ADAPTER.md`
- Environment: `07_MAGENTO_LOCAL_ENVIRONMENT.md`
- Acceptance: `10_TESTING_AND_ACCEPTANCE.md`

## Final verification

- Only `odoo_ecommerce_integration/docs/` is new; the connector repository is
  clean.
- No application code, manifest, view, security rule, or configuration file was
  added.
- All five protected repositories remain at their baseline HEADs with zero
  working-tree changes.
- All 15 required documents exist and their cross-references resolve.
- No real token, password, customer PII, or local secret was found in the docs.
- Documentation acceptance: **PASS**.

## Next safe action

1. Stop. The documentation phase is complete.
2. Do not implement M1 until the operator authorizes the implementation phase.
3. On authorization, start M1 from `08_ODOO_19_IMPLEMENTATION_PLAN.md` and record
   evidence in this file. Do not start M2 in the same step.

## Checkpoint template

Append after every milestone:

```text
### YYYY-MM-DD — <MILESTONE>
- result: COMPLETE | BLOCKED | READY_FOR_REVIEW
- branch / commit / tag:
- Odoo version / commit:
- queue_job branch / commit:
- Magento version / image digest:
- database:
- code changed:
- tests run (command + result):
- live scenarios:
- failures / skips:
- security checks:
- protected repo status:
- docs updated:
- blocker:
- next safe action:
```
