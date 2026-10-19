# 13 — Execution Checkpoints

## Current checkpoint

| Field | Value |
| --- | --- |
| Phase | **Autonomous implementation — Odoo 19/18/17 code paths** |
| Date | 2026-10-19 |
| Status | Code installed and tests pass on all three Odoo versions; **live Magento acceptance blocked** |
| Current branch | `19.0` (documentation worktree) |
| Application code | Implemented in both allowed repositories |
| Commits | Local only; no push, tag, release, or deployment |
| Protected repos | Clean; verified after implementation |
| Next gate | Live Magento `2.4.7-p3` provisioning and acceptance |

## Implementation baseline

| Item | Value |
| --- | --- |
| Odoo 19 | `20f5882e87e818e94a79ad07ac00530842d7045b`, Python 3.12.15 |
| Odoo 18 | `8e50ecb100695e2d4c98bf3bd88463f2cfb53cad` |
| Odoo 17 | `02d3a1d847bb4c3f784e3b018b581ee4d8f3fe4e` |
| OCA queue 19.0 | `da2664795eb525698f93dfdd63f6ba5c4c9fccba` (`queue_job 19.0.2.1.6`) |
| OCA queue 18.0 | `8ece5e3b4af13479e22a8cb282c255aeaed7c626` |
| OCA queue 17.0 | `983b6adc1aa780c3d69247cd2d5cadc91bcffe82` |
| PostgreSQL | local `postgres:16` container, loopback |
| Magento | **not installed**; no Adobe Composer credentials |
| Test DB 19 | `ecommerce_magento_accept_19` |
| Test DB 18 | `ecommerce_magento_test_18` |
| Test DB 17 | `ecommerce_magento_test_17` |

Protected repository baseline remains unchanged:

| Repository | HEAD | Dirty |
| --- | --- | --- |
| `move_line_in_picking_list` | `894691104e74e4ca862bf1502286cf85f602f295` | 0 |
| `odoo_advance_chatter` | `c6da242a2e4208fbd0e0b78a871d1cbf55c2326e` | 0 |
| `odoo_sticky_view` | `111afd8d6ad643616d0bfc355c913a522d9cd814` | 0 |
| `order_line_in_order_list` | `fba4274075ae40b41f3db32d262b9500363c42bc` | 0 |
| `po_line_in_po_list` | `5f10e48128b55e8c2a4eb5e13be388752dbe2ebc` | 0 |

## Branch / commit evidence

| Branch | Core implementation commit | Connector implementation commit |
| --- | --- | --- |
| `19.0` | `0001d76` | `16f14a3` (plus later `359f8a9` retry fix) |
| `18.0` | `37e3455` | `6cb9d00` (plus later `77f5183` retry fix) |
| `17.0` | `e32647d` | `b533513` (plus later `1112cd2` retry fix) |

All commits are local. Nothing was pushed. Documentation-only commits after these
implementation commits are not listed individually.

## Milestone results

### M1 — Environment readiness: PARTIAL

Completed:

- Odoo 19/18/17 environments located and verified.
- PostgreSQL started; dedicated test databases created.
- OCA `queue_job` installed from pinned 19.0/18.0/17.0 branches in isolated
  addons directories.
- `openupgradelib 3.13.7` installed in the Odoo 19 venv.
- Real OCA jobrunner started with workers > 1 and executed a job successfully:
  job `650e601f-b62b-4665-8172-b43e5647b8fe` reached state `done` on
  `ecommerce_magento_test_19`.
- Isolated addons paths were used for 18/17 so protected repository modules were
  not loaded or modified.

Blocked:

- No real Magento Open Source `2.4.7-p3` stack exists.
- `~/.composer/auth.json` is absent, so Adobe's Composer repository cannot be
  used to install Magento.
- No live Magento API endpoint, token, or fixture data exists.

### M2 — Shared core: COMPLETE (tests)

Implemented:

- `ecommerce.backend`, `ecommerce.store`
- product, variant, attribute, attribute-value, customer, order, order-line,
  invoice, payment, shipment, refund, inventory-source, carrier, and
  payment-method mappings
- sync state, event, and issue models
- company rules, groups, ACLs, views, menus
- OCA queue dependency and shared event/issue services

Evidence:

- Odoo 19 clean install: 0 failed, 0 errors; combined 20 tests.
- Odoo 18: 0 failed, 0 errors; combined 19 tests.
- Odoo 17: 0 failed, 0 errors; combined 19 tests.

### M3 — Magento authentication/scope: PARTIAL

Implemented:

- Bearer integration-token client
- URL/TLS/loopback validation
- store-view discovery, MSI source probe, capability flags
- preflight and connection test
- queue jobs and channels

Evidence:

- Deterministic fake Magento HTTP server tests for successful auth, bad URL,
  429, timeout, store scope, MSI probe.
- **No real Magento authentication test.**

### M4 — Catalog and customers: PARTIAL

Implemented and tested:

- simple product import and replay
- simple product export
- configurable parent discovery plus child product import
- SKU matching/ambiguity failure
- website-scoped customer import and replay
- mapping persistence

Limitations:

- Configurable attributes are discovered as child products but full Odoo
  attribute-line/variant reconstruction and attribute/value mapping records are
  not completed.
- No product image, bundle/grouped/virtual/downloadable support.
- No live Magento payload verification.

### M5 — Orders: PARTIAL

Implemented and tested:

- incremental order discovery by `entity_id`
- guest/customer partner resolution
- billing/shipping address partners
- product line resolution
- Magento increment ID as Odoo sale-order name
- total verification and optional confirmation
- replay idempotency

Evidence:

- Odoo 19/18/17 unit/ORM tests pass for order import and replay.
- No live Magento order verification.

### M6 — Financial workflows: PARTIAL

Implemented and tested:

- invoice creation/posting
- payment-method-to-journal mapping
- payment registration from paid-invoice evidence
- deterministic payment evidence key and replay prevention
- credit memo to Odoo credit note
- duplicate prevention

Evidence:

- Odoo 19/18/17 tests pass for invoice, payment, and credit note replay.
- No live Magento invoice/payment/credit memo verification.
- Refund payment automation remains out of V1.

### M7 — Inventory and shipments: PARTIAL

Implemented and tested:

- one active source mapping
- Odoo stock quant calculation
- absolute SourceItem push and unchanged-target skip
- completed outgoing picking shipment creation
- partial/ordered quantity handling using done move quantities
- exact shipment adoption and replay prevention

Evidence:

- Odoo 19/18/17 tests pass for inventory and shipment create/replay.
- No live Magento shipment/SourceItem verification.
- Post-create tracking update remains unsupported.
- Multi-source MSI remains out of V1.

### M8 — Queue resilience: PARTIAL/VERIFIED-CORE

Implemented:

- OCA channels and job functions
- identity keys for duplicate active scans
- retry patterns
- transactional advisory lock when running under a real `job_uuid`
- sanitized issue creation on permanent failures
- real jobrunner execution test

Evidence:

- Real OCA jobrunner executed a queued job to `done`.
- Duplicate active catalog job was rejected by identity key.
- 429/timeout mapping and URL safety tests pass.
- Full automated crash/requeue and multi-worker concurrency acceptance remains
  to be run.

### M9 — Odoo 19 acceptance: PARTIAL

Passed:

- clean database install of `queue_job`, core, and connector
- combined 20 module tests: 0 failed, 0 errors
- real jobrunner test
- security/company tests
- secret scan of source tree
- protected repositories unchanged

Not passed:

- live Magento connection/API acceptance
- live catalog/customer/order/finance/inventory/shipment scenarios
- end-to-end financial and shipment evidence against real Magento

**Odoo 19 is not claimed as commercially accepted.**

### M10 — Odoo 18 port: PARTIAL

Passed:

- `18.0` branch created
- `_sql_constraints` port, removal of Odoo 19-only `models.Index`,
  `models.UniqueIndex`, and `models.Constraint`
- OCA queue 18.0 installed in isolated addons path
- install and combined 19 tests pass: 0 failed, 0 errors
- connector functional tests pass, including order/finance/inventory/shipment

Known 18-specific difference:

- Partial unique indexes became full unique constraints; archiving and
  re-creating the same external mapping is not supported on 18.0.
- Live Magento acceptance not executed.

### M11 — Odoo 17 port: PARTIAL

Passed:

- `17.0` branch created
- Odoo 17 `<tree>` view port
- Odoo 17 storable product type (`product`) adaptation
- OCA queue 17.0 installed in isolated addons path
- install and combined 19 tests pass: 0 failed, 0 errors
- connector functional tests pass

Known 17-specific difference:

- Same full-unique/archive limitation as 18.0.
- Live Magento acceptance not executed.

## Verified commands and evidence

Odoo 19 clean acceptance install:

```bash
odoo-bin -c /home/ridho/Data/odoo-dev/19/config/odoo.conf \
  -d ecommerce_magento_accept_19 \
  -i queue_job,odoo_ecommerce_integration,odoo_ecommerce_magento \
  --without-demo \
  --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init
```

Result: `0 failed, 0 error(s) of 20 tests`.

Odoo 18:

```bash
odoo-bin -c /home/ridho/Data/odoo-dev/18/config/odoo.conf \
  --addons-path=<odoo18-core>,<odoo18-addons>,/home/ridho/Data/odoo-dev/18/ecommerce-addons \
  -d ecommerce_magento_test_18 -u odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-enable --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init
```

Result: `0 failed, 0 error(s) of 19 tests`.

Odoo 17:

```bash
odoo-bin -c /home/ridho/Data/odoo-dev/17/config/odoo.conf \
  --addons-path=<odoo17-core>,<odoo17-addons>,/home/ridho/Data/odoo-dev/17/ecommerce-addons \
  -d ecommerce_magento_test_17 -u odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-enable --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init
```

Result: `0 failed, 0 error(s) of 19 tests`.

## Known limitations

- No live Magento environment or API evidence.
- Configurable product attributes are not fully reconstructed into Odoo
  attribute lines/variants.
- Simple product export only; no configurable export.
- No product images or complex Magento product types.
- No tax-rate mapping; product taxes are cleared on imported products and total
  mismatches block auto-confirm.
- No post-import order edits/cancellations.
- No refund payment automation.
- No RMA.
- No multi-source MSI.
- No post-create tracking updates.
- Odoo 18/17 do not support archive/recreate of the same external mapping.
- Full crash/requeue multi-worker acceptance remains open.

## Next safe action

1. Obtain Adobe Composer credentials and provision the isolated Magento
   `2.4.7-p3` stack from `odoo_ecommerce_magento/tools/magento-compose/`.
2. Mint a least-privilege Integration token.
3. Run live connection, catalog, customer, order, finance, inventory, and
   shipment scenarios.
4. Fix any contract mismatches and rerun all three version suites.
5. Only then record M9/M10/M11 as complete and create release tags.
