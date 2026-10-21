# Final Reliability Hardening

## Implemented reliability controls

### Queue classification

`queue.job` is extended by core with `ecommerce_store_id`,
`ecommerce_backend_id`, and `ecommerce_provider`. The values are populated from
integration-owned context at job creation. Dashboard queue filters use these
fields deterministically. Historical jobs created before this metadata remain
unclassified and are excluded when provider/backend/Store filters are applied;
they are never guessed from identity strings.

### Per-record inventory isolation

Magento inventory child batches process each mapping in its own savepoint and
remote write. Validation failures create a record-specific issue and do not stop
independent mappings. Transport/auth/rate-limit errors still bubble for queue
retry. Absolute quantity writes make retries idempotent.

### Category isolation

Each category node uses a savepoint. A missing or failed parent produces a
`category_dependency_failed` issue and prevents orphan import; unrelated
top-level category child jobs continue. The category coordinator records a child
as failed when its root subtree imports nothing.

### Run and batch progress

- `ecommerce.sync.run` tracks totals, processed, succeeded, failed, skipped,
  state, timestamps, cursor, and last error.
- `ecommerce.sync.batch` is unique per `(run_id, key)`, so retried child jobs do
  not double-count.
- Completion is only recorded when processed work reaches the run total.

### Scheduler

The provider-neutral core scheduler now uses capability resource names
(`products`, `categories`, `customers`, `orders`, `shipments`, `finance`,
`inventory`) and maps them to singular synchronization-state resources. This
fixes the earlier scheduler/capability resource mismatch.

## Test evidence

- Inventory invalid-mapping isolation test.
- Category missing-parent dependency test.
- Queue metadata provider/store/backend test.
- Scheduler duplicate-trigger deduplication test.
- Company-scoped stock Store discovery test.
- Full regressions: 19 = 72, 18 = 72, 17 = 72.
- Uninstall isolation on Odoo 19: Magento job removed; core job and unrelated
  jobs retained; core module remained installed.

## Remaining hard limits

- Finance and inventory coordinators still enumerate broad eligible sets when
  manually retriggered; child acknowledgement is idempotent, but there is no
  single durable cross-run cursor for late finance changes.
- Actual worker-kill recovery was executed during the 10k Odoo 19 run; OCA
  resumed and the run completed with exact totals and no duplicate mappings.
- Odoo 18/17 uninstall isolation was not executed.
