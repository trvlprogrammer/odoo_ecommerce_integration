# 05 — OCA queue_job Design

## 1. Verified upstream facts

Inspected upstream OCA/queue on 2026-10-19:

| Branch | `queue_job` manifest | License | Depends | Python deps |
| --- | --- | --- | --- | --- |
| `19.0` | `19.0.2.1.6` | LGPL-3 | `mail`, `base_sparse_field`, `web` | `requests`, `openupgradelib` |
| `18.0` | `18.0.4.1.1` | LGPL-3 | `mail`, `base_sparse_field`, `web` | `requests` |
| `17.0` | `17.0.1.5.4` | LGPL-3 | `mail`, `base_sparse_field`, `web` | `requests` |

Relevant API confirmed from upstream source/README:

- `with_delay()` and `delayable()` enqueue methods; `delay()` persists.
- `priority`, `eta`, `max_retries`, `description`, `channel`, `identity_key`.
- `on_done()`, `chain()`, `group()`, `split()` for dependency graphs.
- `RetryableJobError(msg, seconds=None, ignore_retry=False)`,
  `FailedJobError`, `JobError`.
- `queue.job` states include pending, enqueued, started, done, failed,
  cancelled, wait_dependencies.
- Retry pattern is configured on `queue.job.function`;
  default retry interval is 10 minutes; default `max_retries` is 5.
- Jobs left in `enqueued`/`started` after worker death are automatically
  re-queued.
- `queue_job__no_delay=True` and `trap_jobs()` support tests.

The local checkout at
`/home/ridho/Data/odoo-integrator/odoo-project/custom-odoo-modules/src/queue_job`
is version `19.0.2.0.3`, **not** the current OCA `19.0` branch and not on the
active addons path. Do not use it implicitly. M1 must install a pinned OCA
revision as an independent addon.

## 2. Mandatory installation

1. Clone OCA/queue at a pinned `19.0` commit.
2. Put the repository root on `addons_path`; do not copy `queue_job` into either
   product repository.
3. Install Python dependency `openupgradelib` for Odoo 19.
4. Install `queue_job` in the database before installing the connector.
5. Run Odoo with `server_wide_modules = web,queue_job` and `workers > 1`.
6. Configure channels and verify the jobrunner starts.

Illustrative config:

```ini
[options]
workers = 4
max_cron_threads = 2
server_wide_modules = web,queue_job
addons_path = /opt/odoo/addons,/opt/oca/queue,/opt/custom-addons

[queue_job]
channels = root:4,ecommerce:4
```

Raise `root` above the default `root:1` for a multi-channel deployment. Child
channel capacities are created/configured in Odoo or via the same channel
configuration, depending on the OCA version; verify the exact syntax for the
pinned queue_job branch.

`workers = 0` is not an acceptable production configuration for queue_job.
Threaded development mode can execute jobs, but it is not production evidence.

The free core declares `queue_job` in `depends`. The connector does not copy the
addon. Odoo does not auto-download Git dependencies; customer installation notes
must say this explicitly.

## 3. Coordinator and child jobs

Provider operations use a discovery/coordinator job that creates bounded child
jobs. The core owns run/batch progress and company-aware enqueuing; providers own
API pagination, payloads, and per-batch work. One core cron discovers due Store
operations from provider-neutral schedule hooks.

## 4. Core enqueue helper

`ecommerce.store._ecommerce_enqueue_job(method_name, *args, channel,
identity_key)` is the only generic queue construction helper. It selects the
backend job user, applies `with_delay()`, and returns the delayed record method.
It does not choose channels, batch sizes, retry patterns, or payloads.

Connector stores expose `_ecommerce_enqueue_sync(resource, operation)`, which
maps a supported capability to the connector's existing queued method. The core
Store Sync wizard calls that hook. Connectors keep their own `queue.job.function`
records and cron scheduling because polling semantics are provider-specific.

## 5. Channels

Create child channels from `queue_job.channel_root`:

| Channel | Capacity | Work |
| --- | --- | --- |
| `ecommerce` | 4 | parent grouping; no jobs directly |
| `ecommerce.orders` | 2 | order discovery/import/confirmation |
| `ecommerce.finance` | 1 | invoice/payment/credit memo workflows |
| `ecommerce.inventory` | 1 | quantity calculation/push |
| `ecommerce.shipments` | 1 | shipment creation/adoption |
| `ecommerce.catalog` | 1 | catalog discovery/import/export |
| `ecommerce.customers` | 1 | customer discovery/mapping |
| `ecommerce.maintenance` | 1 | health checks, reconciliation, preflight |

Capacity is a global channel limit, not a per-store limit. Per-store isolation
and duplicate prevention use advisory locks and identity keys.

Do not put every connector job in `root`; a long catalog import must not starve
payments.

## 6. Job catalogue

Model/method names are stable API. Renaming requires a migration and review.

| Model.method | Channel | Priority | Max retries | Identity key |
| --- | --- | --- | --- | --- |
| `ecommerce.backend.action_test_connection` | maintenance | 50 | 3 | `ecom:health:<backend>` |
| `ecommerce.store.action_preflight` | maintenance | 40 | 3 | `ecom:preflight:<store>` |
| `ecommerce.store.action_discover_orders` | orders | 10 | 5 | `ecom:orders:scan:<store>` |
| `ecommerce.order.mapping.action_import` | orders | 10 | 10 | `ecom:order:import:<store>:<entity>` |
| `ecommerce.order.mapping.action_confirm` | orders | 15 | 3 | `ecom:order:confirm:<store>:<entity>` |
| `ecommerce.store.action_discover_customers` | customers | 40 | 5 | `ecom:customers:scan:<store>` |
| `ecommerce.store.action_sync_catalog` | catalog | 40 | 5 | `ecom:catalog:scan:<store>` |
| `ecommerce.store.action_push_inventory` | inventory | 30 | 5 | `ecom:inventory:push:<store>` |
| `ecommerce.store.action_scan_shipments` | shipments | 20 | 5 | `ecom:shipments:scan:<store>` |
| `ecommerce.shipment.mapping.action_push` | shipments | 20 | 10 | `ecom:shipment:push:<store>:<picking>` |
| `ecommerce.store.action_scan_credit_memos` | finance | 10 | 5 | `ecom:creditmemos:scan:<store>` |
| `ecommerce.refund.mapping.action_import` | finance | 10 | 5 | `ecom:refund:import:<store>:<memo>` |
| `ecommerce.order.mapping.action_sync_finance` | finance | 5 | 5 | `ecom:finance:<store>:<entity>` |

Priority is lower-is-faster. Manual urgent jobs may use priority `0`.

Job methods must be small dispatchers or one bounded unit of work. A discovery
job should read one page or one bounded window, enqueue per-entity jobs, then
return. It must not import an unbounded store in one transaction.

Suggested graph for an imported order:

```
discover_orders (bounded)
  -> import_order (one per entity)
       -> confirm_order (only if auto-confirm and total acceptable)
       -> sync_finance (when paid evidence exists)
```

Do not make finance a dependency of an unconfirmed order. Finance re-checks the
order state and refuses with a business error if prerequisites are absent.

## 7. Retry policy

### 5.1 Exception classes

| Condition | Raise | Retry? |
| --- | --- | --- |
| Connection timeout, DNS failure, 5xx, 429 | `RetryableJobError` | yes |
| 429 with `Retry-After` | `RetryableJobError(seconds=<header>)` | yes |
| Auth expired/rejected | `RetryableJobError` once after revalidation | limited |
| Missing product/customer/source mapping | `FailedJobError` | no |
| Financial total mismatch | `FailedJobError` | no |
| Ambiguous remote write outcome | `FailedJobError` and issue | no; manual review |
| Invalid/unsupported product type | `FailedJobError` | no |
| Local configuration incomplete | `FailedJobError` | no |
| Unknown programming error | let it fail normally; capture issue | no automatic blind retry |

Use `FailedJobError` (or a connector subclass) for permanent business failures.
Do not use a generic `except Exception` that converts everything into a retry.

### 5.2 Retry patterns

Configured on `queue.job.function` records:

| Class | Pattern | Notes |
| --- | --- | --- |
| Network/read | `{1: 60, 3: 300, 6: 1800}` | max 10; respect 429 |
| Remote write | `{1: 120, 3: 900}` | max 5; adopt-before-retry mandatory |
| Auth/health | `{1: 60, 3: 600}` | max 3; then issue |
| Finance | `{1: 300, 3: 1800}` | max 5; no retry on ambiguous writes |
| Business failure | no pattern | permanent; issue |

`max_retries` is set at enqueue time. Remember that OCA `max_retries = 0` means
infinite; never use `0` for business jobs.

### 5.3 Job function records

Create `queue.job.function` records for every model/method above. Set
`channel_id`, `retry_pattern`, `on_fail_method` (e.g. `_on_job_failed`), and a
related action where useful. The `on_fail_method` records a sanitized issue and
does not perform remote writes.

Example shape (not final XML):

```xml
<record id="job_function_order_import" model="queue.job.function">
  <field name="model_id" ref="model_ecommerce_order_mapping"/>
  <field name="method">action_import</field>
  <field name="channel_id" ref="channel_ecommerce_orders"/>
  <field name="retry_pattern">{1: 60, 3: 300, 6: 1800}</field>
  <field name="on_fail_method">_on_job_failed</field>
</record>
```

## 8. Identity and deduplication

Use `identity_key` to prevent duplicate **active** jobs. Example:

```
ecom:order:import:<store_id>:<magento_entity_id>
```

OCA creates the new job only if no pending/enqueued/waiting job has the same key.
Once the job is done, a later job with the same key is allowed. Therefore:

- identity_key prevents duplicate concurrent work;
- database mapping constraints prevent duplicate economic documents;
- state checks make a deliberate re-run safe.

Do not use identity_key as a substitute for a mapping unique constraint.

## 9. Concurrency control

1. Channel capacity limits total parallel work.
2. A per-store/resource PostgreSQL advisory lock protects stateful workflows:
   catalog scan, inventory push, order discovery, shipment scan.
3. Use `pg_try_advisory_xact_lock` (non-blocking). If unavailable, raise
   `RetryableJobError(seconds=...)`; do not block a worker indefinitely.
4. Compute the lock key from a stable hash of `(store_id, resource)`.
5. Per-order jobs may run in parallel across orders; a per-order lock prevents
   two finance jobs for the same order.
6. The lock is released on transaction end, including failure.

Do not rely on an in-process Python lock; Odoo workers are separate processes.

## 10. Transaction boundaries and recovery

- One job attempt = one Odoo transaction.
- Remote reads may be repeated safely.
- For a remote create (shipment, future writes), persist a local intent /
  attempted marker and a content fingerprint before the call.
- On retry, list remote records and adopt an exact fingerprint match. More than
  one match or a partial match is an issue, not a create.
- Do not commit midway through a financial chain unless the state model requires
  it. If a commit is unavoidable, the next step must re-read and validate state.
- Do not enable OCA `allow_commit` unless a documented, tested recovery design
  requires it.
- A killed worker may leave a job `started`; OCA re-queues it. The job must
  re-read all local state and never assume the previous attempt completed.

## 11. Scheduled dispatch

Thin cron methods:

```text
ecommerce.store._cron_discover_orders()
  for each active ready store:
      store.with_delay(identity_key=...).action_discover_orders()
```

Cron methods must not perform API calls. They must not loop over all stores in a
single job. Per-store failure must not prevent other stores from being queued.
Use `job_user_id` for scheduled jobs; do not run as superuser.

## 12. Monitoring and support

- Standard OCA `queue.job` views are the low-level job monitor.
- Core `ecommerce.sync.event` records operational facts.
- Core `ecommerce.sync.issue` records actionable problems.
- A permanent job failure opens one issue per deterministic fingerprint.
- A retryable failure does not open an issue on every attempt; `on_fail_method`
  opens it when OCA gives up.
- Manual “Retry” on an issue enqueues a new job after state validation.
- Do not expose a generic “retry any job” button to end users.

## 13. Testing contract

For every queued method, test both halves:

1. **Enqueue test:** use `trap_jobs()`; assert model/method, args, identity key,
   channel, priority, and dependency shape. Do not execute network code.
2. **Execution test:** call the method synchronously with mocked adapter/client;
   assert database state, adoption behavior, and issue creation.

Set `queue_job__no_delay=True` only where synchronous execution is intended.
Never let the default test suite depend on a live jobrunner.

Integration test with a real worker at least once per milestone, using an
isolated database and fake HTTP server. Verify requeue after process kill.

## 14. Version portability

| Version | queue_job branch | Notes |
| --- | --- | --- |
| Odoo 19 | `19.0` | requires `openupgradelib`; current API verified |
| Odoo 18 | `18.0` | verify job function XML/API before porting |
| Odoo 17 | `17.0` | verify job function XML/API before porting |

Do not share a single `queue_job` checkout across Odoo major versions. Pin each
branch. Port job function records and tests, not just Python methods.

## 15. Acceptance criteria

- `queue_job` is independently installed and visible in Odoo.
- The jobrunner starts with workers > 1.
- All API-bound operations are queued; no web request performs a paginated sync.
- Every job has a documented channel, priority, retry policy, and identity key.
- Duplicate active order/shipment/finance jobs are rejected by identity key.
- Per-store locks prevent duplicate concurrent scans.
- A 429/timeout retries with backoff; a missing mapping fails permanently.
- A killed worker's job is re-queued and the retry adopts or safely stops.
- No secret or PII appears in `queue.job` arguments, descriptions, or errors.
- Job function records exist for every model/method in the catalogue.
