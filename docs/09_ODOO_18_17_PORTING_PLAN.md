# 09 — Odoo 18 / 17 Porting Plan

## 1. Gates

Odoo 18 work starts only after the Odoo 19 M9 gate passes and is recorded.

Odoo 17 work starts only after the Odoo 18 M10 gate passes and is recorded.

No branch may claim compatibility based on “the code looks portable.” Each
version is installed, migrated, and accepted independently against its own Odoo
source, database, queue_job branch, and tests.

## 2. Branch model

| Branch | Purpose | Created |
| --- | --- | --- |
| `main` | documentation/integration history | exists |
| `19.0` | Odoo 19 implementation | M1 |
| `18.0` | Odoo 18 port | after M9 |
| `17.0` | Odoo 17 port | after M10 |

Rules:

- Branch from the previous verified branch, not from `main` feature work.
- Keep the same module technical names.
- Change the manifest major and dependency versions, not the product identity.
- Tag each accepted release independently (`19.0.x.y.z`, `18.0.x.y.z`,
  `17.0.x.y.z`).
- Do not merge an unverified 18.0/17.0 change into 19.0. Bug fixes follow the
  OCA forward-port policy: fix the oldest affected branch, then port forward
  with tests.

## 3. Verified version differences

Inspected local Odoo sources on 2026-10-19:

| Area | Odoo 19 | Odoo 18 | Odoo 17 | Porting action |
| --- | --- | --- | --- | --- |
| ORM SQL constraints | `models.Constraint` (preferred; `_sql_constraints` warned unsupported) | `_sql_constraints` | `_sql_constraints` | Provide version-specific constraint declarations |
| `stock.move.quantity` | present | present | present | No rename found in the inspected sources; still test picking logic |
| `stock.move.picked` | present | present | present | Same concept; verify write helpers |
| `sale.order.state` / `invoice_status` | present | present | present | Verify transitions/fields on each version |
| `account.move` posting | `action_post` | `action_post` | `action_post` | Verify payment/invoice test fixtures |
| OCA queue_job | `19.0.2.1.6` at audit | `18.0.4.1.1` | `17.0.1.5.4` | Separate pinned checkout/branch per version |
| queue_job Python deps | `requests`, `openupgradelib` | `requests` | `requests` | Install version-specific deps |
| Python | 3.12 in local venv | 3.12 | 3.12 | Keep compatible syntax; do not assume deployment Python |
| Views/assets | Odoo 19 conventions | 18 conventions | 17 conventions | Validate all XML/JS assets per version |

The table is a starting point, not a substitute for a full API audit. At each
port milestone, inspect the actual target source for every method/field the
connector touches.

## 4. Known high-risk surfaces

1. **Constraint syntax:** Odoo 19 model classes must not use the old pattern.
   Odoo 17/18 must not use `models.Constraint`.
2. **Stock quantities:** order/shipment quantity logic must use delivered move
   quantities and UoM conversion, not order-line quantities. Validate against the
   target version's stock API.
3. **Account payment/invoice APIs:** payment registration and invoice creation
   differ across versions and localizations. Use ORM methods, not raw SQL, and
   test on a chart of accounts.
4. **Sale order invoicing:** `_create_invoices` / posting behavior and taxes can
   change. Financial acceptance tests must be rerun, not just unit tests.
5. **Queue job records:** XML model references, channel names, retry patterns,
   and API may change. Re-import the version's job function data.
6. **View syntax:** list/form/search/button modifiers and JS assets may need
   version-specific files or conditional assets.
7. **Security groups:** XML IDs for sale/stock/account groups can differ. Resolve
   against the target version; never assume 19.0 group XML IDs.
8. **Odoo 17 Python/dependency baseline:** verify supported Python and
   `cryptography`/requests versions before using any optional helper.

## 5. M10 — Odoo 18 port

### Scope

- Create `18.0` from the accepted `19.0` code.
- Install OCA queue_job `18.0` (pinned commit).
- Replace Odoo 19-only ORM/view constructs.
- Adapt any sale/stock/account method signatures found during audit.
- Port all tests and fixtures.
- Run the full Magento V1 acceptance suite on Odoo 18.
- Update docs/manifest version.

### Files / modules

Both repositories; primarily `models/*`, `security/*`, `views/*`, `data/*`,
`tests/*`, `__manifest__.py`. A small compatibility helper module is acceptable
only if it avoids repeated conditionals and is tested; do not fork entire files
without evidence.

### Dependencies

M9 accepted; Odoo 18 source; OCA queue 18.0; same isolated Magento 2.4.7-p3.

### Tests

- Install/upgrade/uninstall on a dedicated Odoo 18 database.
- All Odoo 19 acceptance scenarios, adapted and executed on 18.
- Constraint tests on PostgreSQL.
- Queue jobrunner test and crash/requeue.
- Multi-company/security.
- Upgrade from the initial 18.0 tag if one exists (otherwise migration N/A).
- No regression in the Odoo 19 branch (code review/diff check).

### Success criteria

- Odoo 18 tag created only after all scenarios pass.
- No `models.Constraint` on 18; no old constraint style on 19.
- queue_job 18.0 independently installed.
- Documented limitations unchanged or explicitly amended.
- Odoo 18 docs state only verified versions.

### Failure conditions

- Untested API change.
- Financial/shipment duplicate.
- Cross-company leak.
- A test is skipped because “18 behaves differently” without a documented,
  accepted limitation.

### Evidence

- Test logs, live scenario report, manifest version, tag/SHA, diff summary from
  19.0.

### Safe resume point

After install + core + queue tests. Do not proceed to financial acceptance until
order/stock semantics are verified on 18.

## 6. M11 — Odoo 17 port

### Scope

- Create `17.0` from the accepted `18.0` code.
- Install OCA queue_job `17.0` (pinned commit).
- Apply 17-specific ORM/view/account/stock adaptations.
- Port tests and fixtures.
- Run full acceptance on Odoo 17.
- Update docs/manifest version.

### Dependencies

M10 accepted; Odoo 17 source; OCA queue 17.0; isolated Magento.

### Tests

Same mandatory matrix as M10, executed on Odoo 17. Pay special attention to:

- older sale/account APIs and payment registration
- stock move/UoM/picking behavior
- view/JS asset compatibility
- queue_job 17.0 API and job function records
- Python version supported by the deployment

### Success criteria

- Odoo 17 tag created only after full acceptance.
- All documented limitations apply to 17 as well.
- No claim of 17 support in the 19.0/18.0 README.

### Failure conditions

- Reusing 18.0 binaries/addons with 17.
- Skipping a Magento scenario.
- Assuming a method exists because it exists on 19.

### Evidence

- Test/live logs, tag/SHA, support-matrix update.

## 7. Forward-port policy

- **Bug fix:** apply on the oldest affected supported branch, add a regression
  test, then forward-port to newer branches with tests.
- **New feature:** implement on 19.0 first, then backport only after the 19.0
  gate; this project is 19-first by directive.
- **Security fix:** fix all supported branches, but do not publish a compatibility
  claim for an unverified branch.
- Never cherry-pick a commit without running the target branch's tests.

## 8. Version support matrix (to be filled only with evidence)

| Capability | 19.0 | 18.0 | 17.0 |
| --- | --- | --- | --- |
| Install | pending | not started | not started |
| Connection/scope | pending | not started | not started |
| Catalog | pending | not started | not started |
| Customers | pending | not started | not started |
| Orders | pending | not started | not started |
| Finance | pending | not started | not started |
| Inventory | pending | not started | not started |
| Shipments | pending | not started | not started |
| Queue resilience | pending | not started | not started |
| Acceptance | pending | not started | not started |

Update this table only from `13_EXECUTION_CHECKPOINTS.md` evidence.

## 9. Packaging per version

- Manifest version major matches the branch.
- `depends` uses modules available on that Odoo version.
- Queue job function XML references models that exist on that version.
- README installation section names the correct queue_job branch.
- Odoo Apps listing must clearly separate versions; do not upload a 19.0 package
  to an 18.0 listing.

## 10. Exit criteria for the porting phase

- Odoo 19, 18, and 17 each have an independent tag and evidence record.
- No version claims support for a module/feature it was not tested against.
- Protected repositories remain untouched.
- The implementation handoff lists the exact supported versions and limitations.
