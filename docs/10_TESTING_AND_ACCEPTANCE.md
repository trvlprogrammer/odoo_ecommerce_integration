# 10 — Testing and Acceptance

## 1. Principles

- Test business behavior, not implementation trivia.
- Test the failure paths that can create money or stock: duplicates, ambiguity,
  retry, cross-company access.
- Use deterministic fixtures and fake HTTP for unit/ORM tests.
- Use the isolated Magento stack only for live contract/acceptance tests.
- Never use production data, production credentials, or a shared development
  database as a test target.
- A skipped test is not a pass. Record every skip with a reason and an owner.

## 2. Test layers

| Layer | Purpose | Runs where |
| --- | --- | --- |
| Unit | DTO mapping, URL/error/redaction, money/qty calculations | Odoo test runner, no network |
| ORM | Models, constraints, record rules, state transitions | PostgreSQL test DB |
| Queue | Enqueue shape, retry, identity, dependency, crash/requeue | Odoo + queue_job runner |
| Adapter contract | HTTP status/JSON/pagination/redirect/timeout | Mock HTTP server |
| Live Magento | Real REST payloads and capability behavior | Isolated `2.4.7-p3` |
| End-to-end | Magento fixture → Odoo documents → reverse write | Isolated stack |
| Security | ACL, record rules, SSRF, secret/PII redaction | Odoo test DB |
| Upgrade | Previous tag → current tag on a DB copy | Dedicated DB |
| UI smoke | Menus/views/buttons render; no per-row API calls | Browser/manual or tour |

## 3. Test data

Use a dedicated test company, warehouse, chart of accounts, and store. Prefix
fixtures with `E2E-`/`TEST-`.

Required fixtures:

- simple product, configurable product with 3 variants, and phantom kit
- registered customer + guest email used twice
- orders with discount, shipping, tax, and non-default currency only if a
  supported currency/rate exists
- paid invoice, unmapped payment method, partial/full credit memo
- partial/full shipments with/without tracking
- two store views on one website; a second company/store for isolation
- unsupported product type for failure-path tests

No real customer data. No real payment credentials. Scrub any captured payload.

## 4. Commands

Illustrative Odoo test commands (adjust DB name and addons path):

```bash
/home/ridho/Data/odoo-dev/19/venv/bin/python \
  /home/ridho/Data/odoo-dev/19/odoo-src/odoo-bin \
  -d ecommerce_magento_test_19 \
  --addons-path=/home/ridho/Data/odoo-dev/19/odoo-src/addons,\
/home/ridho/Data/odoo-dev/19/odoo-src/odoo/addons,\
/home/ridho/Data/odoo-dev/19/addons,\
/home/ridho/Data/odoo-dev/oca/queue \
  -i odoo_ecommerce_integration,odoo_ecommerce_magento \
  --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init
```

The exact queue_job path and test tags are finalized in M1. Live tests must be
marked/separated from the default suite (environment variable or test tag) so CI
does not require Magento.

## 5. Mandatory Odoo 19 acceptance matrix

| ID | Scenario | Must prove |
| --- | --- | --- |
| A1 | Connection/auth | Valid token ready; invalid token fails closed; no secret leak |
| A2 | Store scopes | Website + two store views bind; duplicate binding rejected |
| A3 | Simple product round trip | Create/update/import/export idempotent; mapping stable |
| A4 | Configurable product | Parent/child/attributes/values; repeated round trip |
| A5 | Customer | Website-scoped mapping; duplicate email not silently merged |
| A6 | Guest repeat orders | One commercial partner per email/store; addresses correct |
| A7 | Order economics | Discount/shipping/tax/currency totals preserved/verified |
| A8 | Order idempotency | Re-import/concurrent import creates one sale order |
| A9 | Confirmation | Auto-confirm only on acceptable total; mismatch issue |
| A10 | Invoice/payment | One invoice, one payment; unmapped method blocks |
| A11 | Payment adoption | Simulated uncertain outcome adopts; >1 match manual |
| A12 | Credit memo | One credit note; missing invoice manual; no RMA |
| A13 | Inventory | Formula + kit + unchanged skip + absolute SourceItem |
| A14 | Shipment | Partial/full/kit; exact adoption; no duplicate |
| A15 | Tracking | At-creation tracks copied; later change not synced (documented) |
| A16 | Multi-store | Orders/customers/inventory isolated by store view |
| A17 | Multi-company | Cross-company read/write/enqueue denied |
| A18 | Queue crash | Kill worker; requeue; no duplicate economic document |
| A19 | Concurrency | Same store scan serialized; different stores not blocked |
| A20 | Upgrade | Previous tag upgrades on a DB copy; no data loss/duplicate |
| A21 | Uninstall | Module uninstall leaves no orphan queue jobs/security errors |
| A22 | UI | Menus/views/buttons work; no API call per list row |

No M9 acceptance claim without A1–A22 evidence.

## 6. Financial acceptance specifics

A financial test passes only if all are true:

1. The invoice is created from the correct sale order and company.
2. The invoice is posted exactly once.
3. The payment journal matches the Magento method mapping.
4. The payment amount does not exceed the invoice residual.
5. The currency matches.
6. The deterministic memo/adoption query prevents a second payment.
7. A retry after a forced exception does not create a second payment.
8. Posted documents are not mutated by a retry.
9. Ambiguity opens a manual-review issue and does not register a payment.
10. Credit note is linked to the correct invoice and is posted once.

## 7. Shipment/inventory acceptance specifics

- Delivered quantities come from done moves, not ordered quantities.
- UoM conversion is explicit; no silent float truncation.
- Kit quantities use complete kits and the Magento parent order item.
- Cumulative shipments never exceed ordered quantity.
- SourceItem writes are absolute and skip unchanged targets.
- A retry after a lost response adopts an exact signature; ambiguous adoption
  creates an issue and performs no write.
- Negative targets are clamped to zero; no negative remote quantity.
- One active source per store is enforced.

## 8. Security tests

- Non-manager cannot read/write backend token.
- Non-manager cannot configure backend/store.
- Company A user cannot read/enqueue/retry company B records.
- Job user cannot act outside its allowed companies.
- URL parser rejects credentials, query/fragment, non-HTTP schemes, metadata
  endpoints, and unsafe redirects.
- HTTP is rejected unless loopback development is explicitly allowed.
- Tokens/cookies/authorization headers never appear in event/issue/job fields.
- Customer PII in errors is sanitized; no raw payload in issue summaries.
- SQL injection is not possible through external IDs (ORM parameters only).
- XML/data files contain no real secrets.

## 9. Queue tests

Use OCA `trap_jobs()` for enqueue shape, and direct synchronous method calls for
business behavior.

Required assertions:

- model/method, recordset, arguments
- channel, priority, max_retries
- identity_key and duplicate active job behavior
- `on_done`/chain/group relationships
- retry after `RetryableJobError`; no retry after `FailedJobError`
- `on_fail_method` creates one issue
- killed worker requeues and state guards prevent duplicate documents
- advisory lock contention defers, not blocks forever
- job args/description contain no secret/PII

Live jobrunner test is mandatory at M8/M9. Do not simulate the worker only.

## 10. Performance and capacity

Non-functional acceptance:

- Catalog page size bounded; a 10k-product fixture does not exhaust memory.
- Order discovery uses a bounded page/window and queues per-order jobs.
- A single store scan never blocks other stores.
- 100 queued order jobs drain without database connection exhaustion.
- Financial/shipment jobs do not hold locks during long HTTP waits where
  avoidable; timeouts are bounded.
- No N+1 ORM reads per order line beyond documented lookups.
- Logs and queue result fields are bounded.

Record measured values; do not claim performance from intuition.

## 11. Upgrade tests

- Install previous tag, create representative mappings/state, upgrade to current
  tag on a database copy.
- Verify constraints/indexes, data preservation, mapping uniqueness, queue job
  function records, views, and security.
- Verify no automatic remote writes occur during upgrade.
- Test uninstall/reinstall on a disposable DB; queue jobs referencing uninstalled
  models must be handled as documented.

## 12. Evidence format

Every milestone record includes:

```text
Milestone:
Commit/tag:
Odoo version / commit:
queue_job branch / commit:
Magento version / image digest:
Database:
Tests run (command + count):
Live scenarios:
Failures/skips:
Security checks:
Protected repo status:
Docs updated:
Next safe action:
```

Store evidence in `13_EXECUTION_CHECKPOINTS.md` or a linked test log that does
not contain secrets/PII.

## 13. Acceptance authority

A milestone is accepted only by a human maintainer after reviewing evidence. An
agent may prepare evidence and mark a checkpoint `READY_FOR_REVIEW`, but must not
declare production acceptance or a commercial release unilaterally.
