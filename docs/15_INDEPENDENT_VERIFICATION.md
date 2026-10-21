# 15 — Independent Verification

**Audit date:** 2026-10-19

**Auditor role:** Independent Senior Odoo QA / Magento Integration / OCA queue_job auditor

**Scope:** `odoo_ecommerce_integration`, `odoo_ecommerce_magento`, local Odoo 19/18/17,
local PostgreSQL, OCA `queue_job`, and the documented local Magento environment.

**Verification mode:** Read-only source audit, isolated clean installs, disposable
databases, synthetic fixtures, fake Magento HTTP contract tests, and a real OCA
jobrunner. No application code was changed. No commit, push, deployment, or
production write was performed.

## 1. Executive summary

The implementation installs cleanly and its existing automated tests pass on
Odoo 19, 18, and 17. A real OCA `queue_job` runner executed queued jobs, including
a retryable failure and a permanent failure.

The connector is **not release-ready**. Mandatory acceptance gates are not met:

- No live Magento Open Source instance exists. No Magento API, catalog, order,
  payment, inventory, or shipment scenario was executed against real Magento.
- Several high-severity code defects are present, including cross-store order
  discovery, payment overpayment without a residual check, ignored
  `auto_register_payment`, missing payment adoption, unrestricted HTTPS/SSRF
  targets, and jobs that ignore `job_user_id` and run as the caller/root.
- Configurable products, attributes, tracking, and kit inventory/shipment are
  not implemented to the documented V1 acceptance level.
- Module uninstall leaves orphan queue jobs.

The previous handoff correctly admits that live Magento is blocked, but the
statements that the connector is "complete" and that the documented parity
matrix is satisfied are **not supported** by this audit.

**Release decision: NOT READY** (see §16).

## 2. Repository baseline

Verified at audit start and end. No tracked changes were present before this
report.

| Repository | Branch | HEAD | Dirty | Authority |
| --- | --- | --- | --- | --- |
| `odoo_ecommerce_integration` | `18.0` | `ef245aa5731d6fdba49914077a0cad7a81e64699` | clean | In scope |
| `odoo_ecommerce_magento` | `18.0` | `77f51830369d9a87a7883b6cc8c78c76a7f3bdc0` | clean | In scope |
| `odoo_ecommerce_shopify` | `main` | `6515fbe9db2676fc785f8703e27d9b8d6fb2271e` | clean | Read-only |
| `move_line_in_picking_list` | `19.0` | `894691104e74e4ca862bf1502286cf85f602f295` | clean | Protected |
| `odoo_advance_chatter` | `main` | `c6da242a2e4208fbd0e0b78a871d1cbf55c2326e` | clean | Protected |
| `odoo_sticky_view` | `19.0` | `111afd8d6ad643616d0bfc355c913a522d9cd814` | clean | Protected |
| `order_line_in_order_list` | `19.0` | `fba4274075ae40b41f3db32d262b9500363c42bc` | clean | Protected |
| `po_line_in_po_list` | `19.0` | `5f10e48128b55e8c2a4eb5e13be388752dbe2ebc` | clean | Protected |

Additional in-scope branch tips:

| Repository | `19.0` | `17.0` | `main` |
| --- | --- | --- | --- |
| `odoo_ecommerce_integration` | `aaa68d4f252e270ee9646896541970feafc226e4` | `190071d53523b528d96a120fca02db4fdfc5e8ef` | `fc49b66f11a04ff011182bffdd168a86aa884ca7` |
| `odoo_ecommerce_magento` | `359f8a90aaf696ed8400c4756d4136ead2281c49` | `1112cd2f3e48904d9a64236f6e0a643380005df3` | `ecea4746619e2fa37f5492c5b9494ff944b07bc0` |

Documentation inconsistency (P3): `13_EXECUTION_CHECKPOINTS.md` says the current
branch is `19.0`, but both working trees are on `18.0`. The baseline document
also records the older empty-scaffold SHAs. These are documentation drift, not
code defects.

Historical claims in `00_PROJECT_BASELINE.md`, `13_EXECUTION_CHECKPOINTS.md`, and
`14_IMPLEMENTATION_HANDOFF.md` were treated as claims, not evidence. Every result
below was produced in this audit.

## 3. Environment evidence

| Item | Verified value |
| --- | --- |
| OS / kernel | CachyOS Linux, `7.2.11-1-cachyos`, x86_64 |
| CPU / RAM | 12 CPUs, 31 GiB RAM |
| Odoo 19 | `20f5882e87e818e94a79ad07ac00530842d7045b`, reports `Odoo Server 19.0` |
| Odoo 18 | `8e50ecb100695e2d4c98bf3bd88463f2cfb53cad`, reports `Odoo Server 18.0` |
| Odoo 17 | `02d3a1d847bb4c3f784e3b018b581ee4d8f3fe4e`, reports `Odoo Server 17.0` |
| PostgreSQL | `postgres:16`, loopback `127.0.0.1:5432`, running |
| OCA queue 19.0 | `da2664795eb525698f93dfdd63f6ba5c4c9fccba`, `19.0.2.1.6` |
| OCA queue 18.0 | `8ece5e3b4af13479e22a8cb282c255aeaed7c626`, `18.0.4.1.1` |
| OCA queue 17.0 | `983b6adc1aa780c3d69247cd2d5cadc91bcffe82`, `17.0.1.5.4` |
| Magento stack | **Not installed / not running** |
| Magento health endpoint | `127.0.0.1:8083` connection refused |
| Adobe Composer auth | `~/.composer/auth.json` absent |
| Magento images | none locally; Compose cannot start without local secrets |

The databases used for this audit were newly created and disposable:
`audit_magento_19`, `audit_magento_18`, `audit_magento_17`, and
`audit_uninstall_19_v1`. Existing user databases (`odoo19_dev`, `odoo18_dev`,
`odoo17_dev`) were not modified. Database credential values were read from the
local configuration but are intentionally not reproduced in this report.

No `QUEUE_JOB__NO_DELAY` or equivalent synchronous bypass was used for any queue
execution result below.

## 4. Installation results

For each version, the exact branch was exported with `git archive` to an isolated
addons directory. This avoided installing the `18.0` working tree into Odoo 19 or
17 by accident. The only addons paths used were the matching Odoo core, the
matching OCA `queue_job` checkout, and the isolated branch archive.

Commands (configuration paths abbreviated; no secrets reproduced):

```bash
# Odoo 19
odoo-bin -c <odoo19.conf> -d audit_magento_19 \
  --addons-path=<odoo19-core>,<odoo19-addons>,/home/ridho/Data/odoo-dev/oca/queue,/tmp/audit-modules/19 \
  -i queue_job,odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init --without-demo

# Odoo 18
odoo-bin -c <odoo18.conf> -d audit_magento_18 \
  --addons-path=<odoo18-core>,<odoo18-addons>,/home/ridho/Data/odoo-dev/oca/queue-18,/tmp/audit-modules/18 \
  -i queue_job,odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init --without-demo

# Odoo 17
odoo-bin -c <odoo17.conf> -d audit_magento_17 \
  --addons-path=<odoo17-core>,<odoo17-addons>,/home/ridho/Data/odoo-dev/oca/queue-17,/tmp/audit-modules/17 \
  -i queue_job,odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init --without-demo=all
```

| Version | Install | Tests | Result |
| --- | --- | --- | --- |
| Odoo 19 | PASS | 20 | `0 failed, 0 error(s) of 20 tests` |
| Odoo 18 | PASS | 19 | `0 failed, 0 error(s) of 19 tests` |
| Odoo 17 | PASS | 19 | `0 failed, 0 error(s) of 19 tests` |

Registry, views, security, and menus loaded for every version:

| Artifact | 19 | 18 | 17 |
| --- | --- | --- | --- |
| `ecommerce.%` models registered | 20 | 20 | 20 |
| Integration views | 16 | 16 | 16 |
| Connector views | 2 | 2 | 2 |
| Integration menus | 13 | 13 | 13 |
| ACL records | 55 | 55 | 55 |
| Record rules | 19 | 19 | 19 |
| Queue channels | 9 | 9 | 9 |
| Queue job functions | 9 | 9 | 9 |

Odoo 19 uses `models.UniqueIndex` / `models.Constraint`; 18 and 17 use
`_sql_constraints`. Both forms loaded successfully. Odoo 17 uses `<tree>` views;
they loaded successfully.

External Python dependency `requests` was importable in all three virtual
environments. No missing dependency was observed.

## 5. Magento API results

**Status: BLOCKED.**

No Magento Open Source stack is installed, no local Magento images are present,
no Compose project is running, no health endpoint is reachable, and no Adobe
Composer credentials exist. The documented Compose stack cannot be started
without local database/admin secrets.

The only Magento-style verification available was the repository's fake HTTP
server. It is useful for contract-shape and ORM tests, but it is **not** live
Magento evidence. No claim of Magento authentication, store scope, API
availability, MSI behavior, or error compatibility is made.

## 6. Catalog and customer results

Evidence layer: fake Magento HTTP server + Odoo ORM; **not live Magento**.

| Scenario | Result | Evidence |
| --- | --- | --- |
| Simple product import | PASS (fake) | Product `E2E-SIMPLE-1`, external ID `101`, one product and one variant mapping |
| Repeat simple import | PASS (fake) | Still one mapping after replay |
| Simple product export | PASS (fake) | External ID `900`, mapping method `export` |
| Customer import | PASS (fake) | External ID `201`, mapped partner email `e2e.customer@example.test` |
| Customer replay | PASS (fake) | Still one mapping after replay |
| Configurable product | **FAIL** | Parent/child import exists only as separate templates; no attribute lines, attribute-value mappings, or Odoo variant reconstruction |
| Product attributes/values | **FAIL** | Mapping models exist, but no connector code creates attribute or attribute-value mappings |
| Guest repeat customer | NOT TESTED | No fixture covers two guest orders on one email |
| Billing/shipping addresses | NOT TESTED (catalog); order path creates children | No live payload verification |

The configurable-product limitation is visible in
`services/magento_sync.py:320-332`: `parent_mapping` is accepted but never used,
and every child is imported through `_import_product`, which creates a template
per child. The handoff/checkpoint documents already acknowledge this gap, but the
parity matrix and acceptance matrix require it as a V1 outcome.

SKU ambiguity is not fail-safe: `_find_product_by_sku` (`magento_sync.py:304-318`)
records an issue and returns an empty recordset, after which `_import_product`
creates a new template rather than stopping. This can create duplicate products.

## 7. Order results

Evidence layer: fake Magento HTTP server + Odoo ORM; **not live Magento**.

| Scenario | Result | Evidence |
| --- | --- | --- |
| Order import | PASS (fake) | External ID `301`, sale order name `100000301`, amount `20.0`, financial check `matched` |
| Correct customer | PASS (fake) | Registered customer mapping resolved |
| Correct product/quantity/price | PASS (fake) | One line, quantity `2.0`, unit price `10.0` |
| Repeat import | PASS (fake) | Same order mapping; no duplicate sale order |
| Discount / shipping / tax / non-default currency | NOT TESTED | Fixtures do not cover these combinations |
| Order status persistence | PASS (fake) | External state/status stored on mapping |
| Incremental discovery | **FAIL** | See cross-store discovery defect below |
| Cross-store isolation | **FAIL** | `store_id` and `entity_id > cursor` are emitted as separate Magento filter groups |

Cross-store defect evidence: `MagentoClient._search` emits one
`searchCriteria[filterGroups][n]` per filter
(`services/magento_client.py:102-113`). A captured `list_orders(store_view_id=1,
entity_id_gt=100)` request contained:

```text
filterGroups[0] store_id eq 1
filterGroups[1] entity_id gt 100
```

Magento combines separate filter groups with **OR**. The store filter therefore
does not constrain the cursor filter. `sync_orders`
(`services/magento_sync.py:492-497`) passes both filters, and `import_order`
(`magento_sync.py:517-582`) does not validate the returned order's `store_id`
against the configured store view. A cross-store order can be imported into the
wrong store.

Currency handling is also unsafe: if the Magento currency code is not found in
Odoo, the code silently falls back to the company currency
(`magento_sync.py:605-615`) instead of failing as documented.

Tax is not mapped; imported products clear taxes (`magento_sync.py:258`), so
taxed Magento orders will normally mismatch and block auto-confirmation. This is
a documented limitation, but it means the financial check is not a tax-fidelity
check.

## 8. Financial results

Evidence layer: fake Magento HTTP server + Odoo ORM; **not live Magento**.

| Scenario | Result | Evidence |
| --- | --- | --- |
| Invoice creation | PASS (fake) | One invoice mapping created |
| Invoice posting | PASS (fake) | Invoice state `posted`, amount `20.0` |
| Payment registration | PASS (fake) | One payment mapping, payment state `paid` |
| Credit note | PASS (fake) | One refund mapping, posted credit note |
| Repeat finance sync | PASS (fake) | Existing invoice/payment/refund mappings reused |
| Payment amount ≤ residual | **FAIL** | Magento paid invoice `25.0` against Odoo invoice `20.0` produced a `25.0` payment, invoice residual `0.0` |
| Payment adoption | **FAIL** | No search of existing `account.payment` by deterministic memo; only the mapping table is checked |
| `auto_register_payment=False` respected | **FAIL** | Payment was registered while the store field remained at its default `False` |
| Credit memo when no paid invoice | **FAIL** | `_sync_order_finance` returns before `_import_credit_memos`; refund mapping count `0` |
| Credit note reconciliation | **FAIL** | Credit note is created/posted but not reconciled to the invoice |
| Refund payment automation | NOT APPLICABLE | Deferred in V1 |

Payment overpayment reproduction:

1. Fake Magento order total: `20.0`.
2. Fake Magento paid invoice total: `25.0`.
3. `sync_finance` created a `20.0` Odoo invoice and a `25.0` payment.
4. Invoice residual became `0.0`; the excess `5.0` was not blocked or sent to
   manual review.

Code path: `services/magento_sync.py:1095-1141` registers the payment using the
Magento invoice grand total without checking the invoice residual, currency, or
an existing adopted payment. `auto_register_payment` is defined in
`models/ecommerce_mapping.py:42` but is never read anywhere in the connector.

The finance sync also confirms draft sale orders regardless of
`auto_confirm_orders` (`magento_sync.py:1015-1030`), so disabling auto-confirm
does not prevent confirmation when finance sync is run.

## 9. Inventory and shipment results

Evidence layer: fake Magento HTTP server + Odoo ORM; **not live Magento**.

| Scenario | Result | Evidence |
| --- | --- | --- |
| Inventory source mapping | PASS (fake) | One active source mapping used |
| Stock quantity calculation | PASS (fake) | On-hand `7` pushed as absolute `7` |
| Unchanged target skip | PASS (fake) | Second push produced no additional SourceItem write |
| Negative clamp | PASS (code) | `max(int(floor(target)), 0)` |
| Kit / phantom BOM | **FAIL** | No `mrp` dependency and no BOM logic |
| Multi-source MSI | NOT APPLICABLE | Deferred |
| Shipment creation | PASS (fake) | One shipment mapping, one remote shipment |
| Shipment replay | PASS (fake) | Second sync produced no duplicate remote shipment |
| Shipment tracking | **FAIL** | `create_shipment` is always called without tracks; tracking fields are never populated |
| Shipment line identity | **FAIL** | Moves are matched to order lines by product only, not by exact order item |
| Safe multiple-picking adoption | **FAIL** | The same remote item/qty signature can be adopted by more than one picking |
| Shipment scan completeness | **FAIL** | Only the 50 most recent imported order mappings are scanned |
| Over-shipment guard | **FAIL** | Delivered move quantities are sent without a cap against ordered/shipped quantity |

Code references: `magento_sync.py:886-895` (inventory), `magento_sync.py:897-991`
(shipments), `magento_sync.py:932-947` (product-only line lookup),
`magento_sync.py:950-966` (signature adoption), `magento_sync.py:900-902`
(50-order limit), `services/magento_client.py:200-217` (no tracks passed).

## 10. OCA queue_job results

**This gate was executed for real on Odoo 19.** Odoo was started with
`--load=web,queue_job --workers=2 --max-cron-threads=0 --http-port=8091`. The OCA
runner was active and logged:

```text
odoo.addons.queue_job.jobrunner.runner: starting
odoo.addons.queue_job.jobrunner.runner: queue job runner ready for db audit_magento_19
odoo.addons.queue_job.jobrunner.runner: asking Odoo to run job <uuid> on db audit_magento_19
GET /queue_job/runjob?job_uuid=<uuid> HTTP/1.1 200
```

| Queue scenario | Result | Evidence |
| --- | --- | --- |
| Enqueue a real integration job | PASS | `ecommerce.backend._job_test_connection` persisted as a `queue.job` |
| Job persisted | PASS | `queue_job` row present before execution |
| Jobrunner picks it up | PASS | Runner log `asking Odoo to run job`; HTTP `/queue_job/runjob` `200` |
| Successful completion | PASS | Job `955690cf-2754-460c-b527-d8628b3f8a9d` reached `done` |
| Database changes | PASS | Backend state became `ready`; `last_test_at` and capabilities persisted |
| Retryable failure | PASS | Unreachable endpoint job `53a18c1e-0154-4315-ba14-933160d02ba2` entered `pending`, `retry=2`, future `eta` |
| Permanent failure | PASS | Invalid URL job `dc713926-0b0b-403e-9166-4bcd8d946838` ended `failed` with `FailedJobError` |
| Dependency ordering | NOT TESTED | No job dependency graph used in the connector |
| Concurrent jobs | NOT TESTED | No multi-job concurrency acceptance run |
| Interrupted job recovery | NOT TESTED | No worker kill/requeue test |
| Job identity/deduplication | PASS (unit/ORM) | Existing test enqueued the same catalog identity twice; one job remained |
| Channels/worker limits | PARTIAL | 9 channels and 9 job functions created; runner configured `root` capacity `1`; no per-channel capacity test |

The runner was **not** bypassed with `QUEUE_JOB__NO_DELAY`; execution went
through the real HTTP job endpoint.

## 11. Idempotency and concurrency results

| Replay operation | Sequential replay | Concurrent replay |
| --- | --- | --- |
| Product import | PASS (fake) | NOT TESTED |
| Customer import | PASS (fake) | NOT TESTED |
| Order import | PASS (fake) | NOT TESTED |
| Invoice creation | PASS (fake) | NOT TESTED |
| Payment registration | PASS (fake, normal path) | NOT TESTED |
| Refund processing | PASS (fake, normal paid path) | NOT TESTED |
| Shipment creation | PASS (fake, single picking) | NOT TESTED |

Database uniqueness constraints exist for mapping identities, and the existing
tests exercise sequential replay. Concurrent replay, forced crash/requeue, and
partial-failure recovery were not executed. The payment path has no adoption
query for an existing `account.payment`, which is a design gap independent of
transactional rollback.

## 12. Security results

Evidence layer: Odoo ORM with users/groups and direct `MagentoClient`
construction.

| Check | Result | Evidence |
| --- | --- | --- |
| Non-manager cannot see another company's backend | PASS | `VISIBLE_B 0` |
| Non-manager cannot read `access_token` | PASS | `TOKEN_READ DENIED` (`AccessError`) |
| Non-manager cannot write backend | PASS | `WRITE_BACKEND DENIED` |
| Company record rules loaded | PASS | 19 `ir.rule` rows; cross-company search test passed |
| Uninstall leaves no orphan queue jobs | **FAIL** | After uninstall, 3 `queue.job` rows still referenced `ecommerce.backend` |
| SSRF / metadata endpoint rejection | **FAIL** | `https://169.254.169.254/latest/meta-data` was accepted |
| Job user enforcement | **FAIL** | Job ran as user `1` while backend `job_user_id` was `7`; `MATCH False` |
| Cron user least privilege | **FAIL** | All connector crons are configured with `base.user_root` (`data/ir_cron.xml`) |
| Secret/PII in logs | PASS (code inspection) | HTTP errors are generic; no token is logged |
| Token at rest | Limitation | Plain `Char` field, manager-only; documented in D15 |

SSRF code: `MagentoClient._validate_base_url`
(`services/magento_client.py:39-49`) rejects credentials, query, fragment, and
non-loopback HTTP, but accepts **any** HTTPS host, including cloud metadata and
private network addresses. The bearer token is then sent to that host.

Job-user code: every action uses `self.with_delay(...)` without `user_id` or the
configured `job_user_id` (`models/ecommerce_store.py:21-75`,
`models/ecommerce_backend.py:24-30`). The job therefore inherits `env.user`.
The cron records use `base.user_root`, so scheduled jobs execute as superuser and
bypass company record rules. This contradicts the documented rule "Do not run
business jobs as superuser."

Uninstall evidence: both modules reached `uninstalled`, `ecommerce.%` models were
removed, but `queue_job` retained three rows:
`done` (id 2), `failed` (id 3), and `pending` (id 4), all targeting
`ecommerce.backend._job_test_connection`.

## 13. Performance results

**Status: NOT TESTED.**

No bounded synthetic dataset was executed at the required scale. The audit
measured only the single-job runner path: the successful test-connection job
completed in under one second (`date_started` to `date_done` approximately
0.03 s; queue `exec_time` recorded `0`). This is not a throughput, memory, or
concurrency benchmark.

The following remain unmeasured:

- catalog import with a 10k-product dataset;
- 100 queued order jobs and connection-pool behavior;
- multi-store worker concurrency and channel capacity;
- UI responsiveness during synchronization;
- retry storm / rate-limit behavior.

No performance number in the implementation handoff was accepted without
measurement.

## 14. Odoo 19/18/17 parity matrix

Statuses are for the **release claim**, not for the existence of a fake test.
`Fake/ORM` means the existing fake HTTP + ORM test passed but is not live Magento
evidence.

| Feature | Odoo 19 | Odoo 18 | Odoo 17 | Evidence layer |
| --- | --- | --- | --- | --- |
| Module install, registry, views, ACL, menus | PASS | PASS | PASS | Real clean install |
| OCA queue dependency, channels, job functions | PASS | PASS | PASS | Real install |
| Real jobrunner execution | PASS | NOT TESTED | NOT TESTED | Odoo 19 real runner |
| Simple product import/replay | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Configurable product / variants / attributes | FAIL | FAIL | FAIL | Code inspection |
| Customer import/replay | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Guest repeat order | NOT TESTED | NOT TESTED | NOT TESTED | No fixture |
| Order import/replay | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Incremental order discovery isolation | FAIL | FAIL | FAIL | Shared client code |
| Order economics (discount/shipping/tax/currency) | NOT TESTED | NOT TESTED | NOT TESTED | No combined fixture |
| Invoice creation/posting | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Payment registration | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Payment residual/adoption controls | FAIL | FAIL | FAIL | Shared code; overpayment reproduced |
| Credit note | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Credit note without paid invoice | FAIL | FAIL | FAIL | Refund path skipped |
| Inventory simple quantity/SourceItem | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Kit inventory | FAIL | FAIL | FAIL | No `mrp`/BOM logic |
| Shipment creation/replay | BLOCKED | BLOCKED | BLOCKED | Fake/ORM passed; live missing |
| Shipment tracking / kit / exact line identity | FAIL | FAIL | FAIL | Code inspection |
| Multi-store isolation | FAIL | FAIL | FAIL | Filter-group defect |
| Multi-company isolation | PASS | PASS | PASS | ORM/security tests |
| SSRF / job-user security | FAIL | FAIL | FAIL | Shared code |
| Uninstall safety | FAIL | NOT TESTED | NOT TESTED | Orphan jobs on 19 |
| Upgrade from previous tag | NOT TESTED | NOT TESTED | NOT TESTED | No upgrade run |
| Live Magento connection/API | BLOCKED | BLOCKED | BLOCKED | No Magento instance |
| Performance / capacity | NOT TESTED | NOT TESTED | NOT TESTED | No benchmark |

## 15. Defect register

### P0 — Critical

No P0 was proven during this audit. The absence of live Magento testing means a
P0 cannot be ruled out, especially in payment, refund, and cross-store paths.

### P1 — High

| ID | Area | Defect | Evidence | Code |
| --- | --- | --- | --- | --- |
| P1-01 | Orders | Store view and `entity_id` cursor are emitted as OR-combined filter groups, allowing cross-store order discovery; imported order store IDs are not revalidated | Captured request params; `sync_orders` behavior | `services/magento_client.py:102-113`; `services/magento_sync.py:492-497`, `517-582` |
| P1-02 | Finance | Payment amount is not capped by invoice residual; `25.0` paid against a `20.0` invoice with no block or manual review | Overpayment probe | `services/magento_sync.py:1095-1141` |
| P1-03 | Finance | No adoption search of existing `account.payment` by deterministic memo; only the mapping table is checked | Code inspection; docs A11 | `services/magento_sync.py:1095-1141` |
| P1-04 | Finance | `auto_register_payment` is defined but never read; payments are registered while the setting is `False` | Overpayment probe used default `False` | `models/ecommerce_mapping.py:42`; `services/magento_sync.py:1095-1141` |
| P1-05 | Security | Any HTTPS host is accepted, including cloud metadata/private targets; bearer token is sent there | SSRF probe accepted `169.254.169.254` | `services/magento_client.py:39-49` |
| P1-06 | Security | `job_user_id` is ignored; jobs inherit `env.user`, and cron jobs run as `base.user_root` (superuser) | Job user probe: job user `1`, configured `7`, match false | `models/ecommerce_store.py:21-75`; `models/ecommerce_backend.py:24-30`; `data/ir_cron.xml` |
| P1-07 | Catalog | Configurable products are not reconstructed: children become separate templates; no attributes, values, or variant links | Code inspection; checkpoint admission | `services/magento_sync.py:320-332`; `205-302` |
| P1-08 | Shipments | Move-to-order-line matching uses product only, so duplicate product lines can ship the wrong Magento item | Code inspection | `services/magento_sync.py:932-947` |
| P1-09 | Shipments | The same remote item/qty signature can be adopted by multiple pickings | Code inspection | `services/magento_sync.py:950-966` |
| P1-10 | Finance | Over-shipment/overpayment guard absent on shipment quantities; no ordered/shipped cap | Code inspection | `services/magento_sync.py:931-970` |

### P2 — Medium

| ID | Area | Defect | Evidence | Code |
| --- | --- | --- | --- | --- |
| P2-01 | Uninstall | Uninstall leaves orphan queue jobs targeting removed ecommerce models | 3 jobs remained after uninstall | queue data in `audit_uninstall_19_v1` |
| P2-02 | Finance | Credit memos are skipped when there is no paid invoice or the payment method is unmapped; credit note is not reconciled to the invoice | Refund count `0` with zero paid invoices | `services/magento_sync.py:1065-1066`, `1142`, `1188-1224` |
| P2-03 | Shipments | Tracking is never copied at shipment creation | `create_shipment` called without `tracks` | `services/magento_client.py:200-217`; `magento_sync.py:968` |
| P2-04 | Inventory | Kit/phantom-BOM quantity and shipment conversion not implemented | No `mrp` dependency or BOM code | Manifest; `magento_sync.py:886-895` |
| P2-05 | Catalog | Duplicate SKU records an issue but still creates a new product | Code inspection | `magento_sync.py:304-318`, `247-265` |
| P2-06 | Orders | Missing currency silently falls back to company currency instead of failing | Code inspection | `magento_sync.py:605-615` |
| P2-07 | Shipments | Only 50 most recent imported orders are scanned per shipment run | Code inspection | `magento_sync.py:900-902` |
| P2-08 | Catalog/Customers | Hard page caps: products 1000, customers 500 per run | Code inspection | `magento_sync.py:182-203`, `405-430` |
| P2-09 | Inventory | Source mapping does not constrain warehouse/location to the store company | Code inspection | `models/ecommerce_mapping.py:238-264` |
| P2-10 | Queue | No `on_fail_method`; permanent job failures do not automatically create a sync issue | Code inspection; failed job had no issue | `data/queue_job_data.xml` |
| P2-11 | Orders | `auto_confirm_orders=False` is overridden by finance sync, which confirms draft orders | Code inspection; finance test confirms default-false store | `magento_sync.py:1015-1030` |

### P3 — Low

| ID | Area | Defect | Evidence |
| --- | --- | --- | --- |
| P3-01 | UI | No menus/actions/views for invoice, payment, shipment, refund, carrier, payment-method, or inventory-source mappings | `menus.xml` / mapping views |
| P3-02 | Docs | Checkpoint says current branch `19.0`; both working trees are on `18.0`; baseline SHAs are stale | Git state |
| P3-03 | Finance | Rounding tolerance hardcoded at `0.01`; no configuration field despite docs saying "configured" | `magento_sync.py:685-691` |
| P3-04 | Tax | No tax-rate mapping; imported products clear taxes, so taxed orders normally mismatch | `magento_sync.py:258`; documented limitation |

## 16. Release recommendation

**NOT READY.**

Reasoning:

1. Mandatory live Magento connection, catalog, customer, order, finance,
   inventory, and shipment acceptance has not been executed. Those gates are
   **BLOCKED**, not passed.
2. Multiple mandatory workflows have unresolved high-severity defects:
   cross-store order discovery, payment residual/adoption, ignored payment
   automation control, SSRF, and superuser job execution.
3. Configurable products, attributes, tracking, and kit inventory/shipment are
   required V1 outcomes and are not implemented.
4. Real queue execution passes, but crash/requeue, dependency, concurrency, and
   performance gates are not executed.
5. Code completion is not release readiness.

`CONDITIONALLY READY` is not appropriate because the unresolved items are
high-severity mandatory workflows, not merely documented non-critical limits.

`INSUFFICIENT EVIDENCE` would describe the live Magento portion, but it would
understate the code-level high defects that already establish a failing result.

## 17. Safe next steps

1. Provision the isolated Magento `2.4.7-p3` stack with valid local credentials
   and a least-privilege integration token. Do not use production Magento.
2. Fix the order discovery query so `store_id` and `entity_id` are filters in the
   same Magento filter group (AND), and reject order payloads whose store view
   does not match the configured store.
3. Add payment validation before registration: currency match, residual check,
   amount cap, and deterministic adoption of an existing `account.payment`.
4. Honor `auto_register_payment`, `auto_confirm_orders`, and `job_user_id`.
   Give cron records a dedicated non-superuser integration user.
5. Restrict Magento base URLs to an explicit allowlist and reject loopback,
   link-local, metadata, and private targets unless explicitly enabled for a
   local test.
6. Complete configurable attributes/variants, tracking-at-creation, kit/BOM
   conversion, exact order-line identity, and safe multi-picking adoption.
7. Add uninstall cleanup for queue jobs, or a documented quarantine procedure.
8. Run the full A1–A22 acceptance matrix on real Magento for Odoo 19, then 18,
   then 17, including real jobrunner crash/requeue, concurrency, uninstall, and
   upgrade tests.
9. Only after those gates pass should a human maintainer consider a release tag.

## 18. Audit statement

No application code, protected repository, database schema, branch, commit, or
external service was modified by this audit. The only repository change is this
verification report. Database credentials and tokens are intentionally not
reproduced.
