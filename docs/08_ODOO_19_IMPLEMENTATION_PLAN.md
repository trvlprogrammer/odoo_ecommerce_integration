# 08 — Odoo 19 Implementation Plan

## 1. Rules

- Implement milestones in order. Do not start M10 before M9 passes.
- Each milestone is a separate branch/PR against `19.0`.
- Documentation is updated in the same PR when behavior or decisions change.
- No milestone is “done” without executed evidence, not just code.
- Financial and shipment milestones require adopt-before-retry tests.
- Never test against a production Odoo or Magento database.

## 2. Milestone map

| ID | Milestone | Gate |
| --- | --- | --- |
| M1 | Environment readiness | Odoo 19 + queue_job + Magento + empty modules install |
| M2 | Shared core | Core models, security, state/events/issues, tests |
| M3 | Magento authentication | Backend/store scope + connection test |
| M4 | Catalog and customers | Simple/configurable import/export; customer mapping |
| M5 | Order synchronization | Order import/confirm/idempotency |
| M6 | Financial workflows | Invoice/payment/credit memo |
| M7 | Inventory and shipments | SourceItem push + shipment create/adopt |
| M8 | Queue resilience and recovery | Retry/requeue/ambiguity/locks |
| M9 | Odoo 19 acceptance | Full gate + release tag |
| M10 | Odoo 18 port | Separate acceptance |
| M11 | Odoo 17 port | Separate acceptance |

---

## M1 — Environment readiness

### Scope

- Create `19.0` branches from `main`.
- Add repository scaffolding (manifest, package, license, README) with no
  business logic beyond installability.
- Install pinned OCA `queue_job` for 19.0; verify jobrunner.
- Provision isolated Magento `2.4.7-p3` stack.
- Create a dedicated Odoo 19 test database and test company.
- Wire addons paths and document launch commands.
- Confirm protected repositories untouched.

### Files / modules

- `odoo_ecommerce_integration/__manifest__.py`, `__init__.py`, `LICENSE`,
  `README.md`
- `odoo_ecommerce_magento/__manifest__.py`, `__init__.py`, `LICENSE`,
  `README.md`
- `odoo_ecommerce_magento/tools/magento-compose/*`
- Environment notes under connector README or docs

### Dependencies

- Odoo 19 source/venv
- PostgreSQL 16 container
- Docker/Compose
- Adobe Composer credentials (operator-supplied, not committed)
- OCA queue 19.0 pinned commit

### Tests

- `odoo-bin -d <test_db> -i queue_job,odoo_ecommerce_integration,odoo_ecommerce_magento --stop-after-init`
- Start Odoo with `workers > 1`, `server_wide_modules=web,queue_job`; verify
  jobrunner log lines.
- Magento health check.
- Mint a token; call `/V1/store/storeViews` and `/V1/inventory/sources`.
- Confirm no secrets in `git status`, logs, or docs.

### Success criteria

- Both modules install and uninstall cleanly.
- `queue_job` is installed as an external addon; no copies in product repos.
- Odoo 19 test DB and Magento are reachable.
- A trivial queue job executes through the real jobrunner.
- Baseline SHAs and environment are recorded in
  `13_EXECUTION_CHECKPOINTS.md`.

### Failure conditions

- Magento cannot be provisioned due to missing legitimate credentials.
- Odoo module install fails due to a real dependency conflict.
- queue_job cannot run with a jobrunner.
- Any protected repo changes.

### Evidence

- Commands and outputs (redacted), module install log summary, queue runner log
  lines, Magento version/health output, Git status of protected repos.

### Safe resume point

If blocked, leave no partial database mutation. Document the exact failing step
and resume at that step; do not delete shared Odoo/PostgreSQL volumes.

---

## M2 — Shared core implementation

### Scope

- Backend/store models.
- Mapping mixin and mapping models.
- Sync state, event, issue models.
- Security groups, ACLs, record rules.
- Base views/menus and smart buttons.
- Queue helper/dispatch conventions (no Magento jobs yet).
- Module upgrade skeleton.

### Files / modules

Core only: `models/*`, `services/mapping_service.py`,
`services/event_service.py`, `services/issue_service.py`, `security/*`,
`views/*`, `tests/test_backend.py`, `test_store_scope.py`,
`test_mapping_constraints.py`, `test_sync_state.py`, `test_security.py`.

### Dependencies

M1.

### Tests

- Install/upgrade on empty and existing test DB.
- Company isolation for backend/store/mappings.
- Unique constraints under concurrent inserts (PostgreSQL).
- Archive/reactivate behavior.
- Event vs issue separation; issue fingerprint deduplication.
- Credential field not visible to non-manager group.
- A dummy queue job using the core channel convention.

### Success criteria

- Core installs without Magento.
- All mapping tables have store/backend/company scope and unique constraints.
- Company record rules pass positive and negative tests.
- No cross-company read/write through ORM.
- Views usable for backend/store/mapping/log browsing.
- No Magento import in core.

### Failure conditions

- Core cannot install without the connector.
- A mapping allows duplicate active identity or cross-company access.
- Credentials leak through a view, log, or generic search.
- Odoo 19 constraint syntax is used incorrectly.

### Evidence

- Test output, schema constraints, security test matrix, upgrade log.

### Safe resume point

After core install and security tests pass. Do not begin Magento models while
core security is failing.

---

## M3 — Magento authentication and scope

### Scope

- Magento backend inheritance fields (token, edition/version/capabilities).
- HTTP client with URL normalization, TLS, timeouts, error taxonomy, redaction.
- Website/store-view discovery and binding.
- Connection test, preflight, capability flags.
- Backend/store Magento views and buttons.
- Queue health/preflight jobs.

### Files / modules

Connector: `services/magento_client.py`, `magento_adapter.py`,
`magento_errors.py`, `magento_connection.py`, backend/store inherited models,
views, `tests/test_client.py`, `test_auth.py`, `test_scope.py`.

### Dependencies

M1, M2.

### Tests

- Unit: URL normalization, loopback rules, redirects, timeout, 401/403/404/429/5xx,
  invalid JSON, token redaction, response-size cap.
- Live: store views, websites, sources, capability flags against isolated Magento.
- Scope: store view belongs to website; duplicate binding rejected; inactive
  store cannot sync.
- Multi-company: backend from company A cannot bind store in company B.
- Queue: health/preflight jobs execute with retries and issue on permanent fail.

### Success criteria

- Valid token connection is ready; invalid token fails safely.
- Two store views bind to two stores without collision.
- Preflight reports missing MSI/scope blockers precisely.
- No token in logs, queue args, events, or exception text.
- No commerce write during connection tests.

### Failure conditions

- SSRF/redirect guard bypass.
- Credentials exposed.
- Cross-company binding allowed.
- Connection test writes commerce data.

### Evidence

- Live capability output (redacted), test matrix, event/issue records.

### Safe resume point

After scope binding and connection tests pass against the isolated Magento.

---

## M4 — Catalog and customer synchronization

### Scope

- Product/variant/attribute/value mappings.
- Catalog discovery/import for simple/configurable products.
- Catalog export for simple/configurable products (explicit only).
- SKU auto-match with ambiguity handling.
- Customer discovery/mapping and optional create-in-Odoo.
- Guest identity helpers (used by M5).
- Catalog/customer jobs, state, events, issues.

### Files / modules

Connector: `magento_catalog.py`, `magento_customers.py`, mapping helpers,
jobs, views, tests `test_catalog.py`, `test_customers.py`,
`test_product_mapping.py`.

### Dependencies

M3.

### Tests

- Simple product import and round trip.
- Configurable parent/child import/export; attribute/value mapping.
- Unsupported types rejected.
- Duplicate SKU ambiguity → issue, no arbitrary mapping.
- Repeat import/export idempotent.
- Customer website isolation.
- Duplicate customer email does not auto-merge.
- Guest order identity deterministic (unit-level; full flow in M5).
- Multi-company product/partner lookup rejection.

### Success criteria

- Configurable T-Shirt S/M/L round trip passes twice.
- Product/variant mappings unique per store and active.
- Unsupported products create issues and do not partially corrupt data.
- Customer mapping is website-scoped.
- All operations are queued and use bounded pages.

### Failure conditions

- SKU match silently overwrites a mapping.
- Configurable structure is rebuilt destructively.
- Cross-website customer leak.
- Unbounded catalog sync in a web request.

### Evidence

- Before/after Magento and Odoo fixture snapshots, repeated-run evidence,
  test output.

### Safe resume point

After catalog round trip and customer isolation pass. Order work may begin only
when variant/order line mapping is stable.

---

## M5 — Order synchronization

### Scope

- Order discovery with `entity_id` cursor.
- Order import, line mapping, addresses, guest/customer contacts.
- Discounts, shipping, currency, total verification.
- Optional confirmation.
- Order identity/adoption, increment-ID naming, collision handling.
- Order jobs/state/events/issues.

### Files / modules

Connector: `magento_orders.py`, order job methods, order views, tests
`test_orders.py`, `test_order_fidelity.py`.

### Dependencies

M4.

### Tests

- Guest order creates sale.order; repeated import does not duplicate.
- Registered customer mapping used; guest repeat reuses commercial partner.
- Addresses (billing/shipping), discount, shipping, tax, currency totals.
- Missing product mapping fails safely with issue.
- Configurable order line uses child mapping; child item ID persisted.
- Increment ID collision with an unrelated Odoo order fails, no merge.
- Canceled/unimportable state skipped with event.
- Cursor advances only after success; retry after failure does not skip.
- Auto-confirm only when totals match/tolerance; mismatch blocks.
- Multi-company: order cannot use another company's warehouse/currency.

### Success criteria

- Eight M5 scenarios pass on isolated Magento + Odoo 19:
  guest, registered, configurable, discount, shipping, tax, currency, duplicate.
- Sale order name uses Magento increment ID for new imports.
- No duplicate sale orders under repeated/concurrent jobs.
- Financial mismatch creates issue and never auto-confirms.

### Failure conditions

- Duplicate sale order or line.
- Wrong customer/address merge.
- Cursor advances past a failed order.
- Cross-company order import.

### Evidence

- Order payload fixtures (redacted), Odoo sale order snapshots, cursor state,
  repeat-run test output.

### Safe resume point

After order import and idempotency pass. Do not start financial posting until
order totals are trustworthy.

---

## M6 — Financial workflows

### Scope

- Invoice create/post from sale.order.
- Payment evidence, method → journal mapping.
- Payment adoption/registration with residual/currency checks.
- Credit memo → credit note.
- Financial mappings, state, events, issues.
- No refund payment automation in V1.

### Files / modules

Connector: `magento_finance.py`, financial jobs, payment/carrier mapping views,
tests `test_finance.py`, `test_payments.py`, `test_refunds.py`.

### Dependencies

M5.

### Tests

- Invoice created/posted once; retry detects existing.
- Unmapped payment method blocks with issue.
- Payment adoption by deterministic memo; >1 match → manual review.
- Amount/currency/residual guards.
- Partial payment/overpayment → manual review, no invented payment.
- Credit memo requires existing invoice; creates/posts one credit note.
- Duplicate credit memo retry is idempotent.
- RMA is unsupported and clearly reported.
- Posted documents cannot be silently altered by retry.

### Success criteria

- One invoice, one payment per evidence key, one credit note per memo.
- No duplicate economic documents after crash/retry.
- Every ambiguity produces an issue with a deterministic fingerprint.
- Financial tests pass under PostgreSQL concurrency.

### Failure conditions

- Double payment/invoice/credit note.
- Posting before totals/currency verified.
- Retry overwrites posted accounting data.

### Evidence

- Journal entries, payment residuals, mapping states, concurrency test output.

### Safe resume point

After financial idempotency and manual-review paths pass.

---

## M7 — Inventory and shipment workflows

### Scope

- Source mapping (one active per store).
- Odoo quantity calculation (on-hand/reserved/safety/kits).
- SourceItem absolute push and last-pushed idempotency.
- Completed delivery discovery.
- Magento shipment create, partial quantities, tracking, exact adoption.
- Inventory/shipment jobs, events, issues.

### Files / modules

Connector: `magento_inventory.py`, `magento_shipments.py`,
`services/kits.py` if shared, jobs, views, tests `test_inventory.py`,
`test_shipments.py`.

### Dependencies

M5 (order line mapping), M3 (source discovery).

### Tests

- Quantity formula: on-hand, reserved, safety, floor/clamp.
- Kit availability with one phantom BOM; ambiguous BOM → manual review.
- Unchanged target performs no write.
- SourceItem 429/5xx retry does not duplicate effect (absolute).
- One source per store enforced.
- Partial delivery creates correct Magento shipment.
- Multiple deliveries/backorders produce multiple mappings.
- Kit shipment quantity to parent item.
- Exact adoption after simulated ACK loss; ambiguous adoption → issue.
- Tracking at creation; later tracking change not synced (accepted limitation).
- Never ship more than ordered.

### Success criteria

- Inventory fixture `A=10, B=21, KIT=A+3B` produces expected complete kits.
- Partial/configurable/kit shipments pass.
- No duplicate shipment after uncertain create.
- Unsupported/ambiguous cases do not write.

### Failure conditions

- Negative/over-shipped quantities.
- Duplicate shipment.
- Multi-source write.
- Inventory job writes catalog/orders.

### Evidence

- Quantity calculations, SourceItem responses, shipment item signatures,
  adoption tests.

### Safe resume point

After inventory and shipment idempotency pass.

---

## M8 — Queue resilience and recovery

### Scope

- Finalize channels, job functions, retry patterns, priorities, identity keys.
- Add per-store advisory locks.
- Add `on_fail_method` issue creation and safe retry actions.
- Add stale/running recovery behavior.
- Add queue monitoring views/links.
- Load/concurrency tests.

### Files / modules

Core queue services and connector job data; tests
`test_queue_resilience.py`, `test_concurrency.py`.

### Dependencies

M3–M7.

### Tests

- Duplicate identity key does not create a second active job.
- 429/timeout retries; 4xx permanent; max retries then issue.
- Worker killed mid-job; requeue; no duplicate financial/shipment document.
- Two concurrent scans for one store: one defers.
- Two stores scan concurrently without blocking each other.
- Manual retry after resolved issue is safe.
- Queue arguments contain no secrets/PII.
- Job description/result bounded.

### Success criteria

- Measured behavior matches the documented retry matrix.
- No duplicate economic documents under forced concurrency/crash.
- Issues deduplicate and resolve.
- Jobrunner and channels survive restart.

### Failure conditions

- Infinite retry loop.
- Queue job stores customer payload/token.
- Cross-store lock contention.
- Manual retry bypasses state checks.

### Evidence

- Job state transitions, retry counts, lock test output, crash/restart log.

### Safe resume point

After crash/concurrency tests pass. Only then run M9 acceptance.

---

## M9 — Odoo 19 acceptance

### Scope

- Full regression on a clean database and isolated Magento.
- Security, multi-company, upgrade, performance, and documentation review.
- Release tag for Odoo 19.
- No new features during acceptance.

### Tests

- Full module test suite on Odoo 19.
- Live acceptance scenarios (at minimum):
  1. connection + scopes
  2. simple product round trip
  3. configurable product round trip
  4. customer mapping + guest repeat orders
  5. order economics (discount/shipping/tax/currency)
  6. invoice + payment + duplicate retry
  7. credit memo
  8. partial shipment + tracking
  9. kit shipment
  10. inventory/kit SourceItem
  11. multi-store isolation
  12. multi-company isolation
  13. queue crash/requeue
- Upgrade from previous 19.0 tag on a DB copy.
- Uninstall/reinstall behavior; data cleanup expectations.
- Access rights: user/operator/manager, manager credential access only.
- No secrets in logs/repo; `git diff --check`.

### Success criteria

- All tests pass; live scenarios pass; no critical/high security findings.
- Documentation matches implemented behavior.
- Tag `19.0.1.0.0` (or the actual release) created after approval.
- `13_EXECUTION_CHECKPOINTS.md` records evidence.

### Failure conditions

- Any duplicate financial document or shipment.
- Cross-company data leak.
- Unresolved critical issue.
- Claim of a feature not covered by tests.
- Protected repo changes.

### Evidence

- Test logs, live scenario report, tag/SHA, security checklist, known-limitations
  list, upgrade log.

### Safe resume point

If acceptance fails, fix on a new commit and rerun the affected scenario; do not
move to M10. Do not rewrite already-published tags.

## 3. Cross-milestone definition of done

- Code merged to `19.0`.
- Unit + ORM + queue tests added and passing.
- Live test evidence for the milestone (if it touches Magento).
- Security/multi-company tests unaffected.
- Docs updated (`03`, `04`, `05`, `06`, `10`, `13`).
- No protected repository changes.
- No secrets/PII in diff or logs.
- Failure modes produce issues, not silent skips.
