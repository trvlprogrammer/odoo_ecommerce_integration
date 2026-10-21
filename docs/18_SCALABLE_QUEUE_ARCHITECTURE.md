# Scalable Queue Architecture

## Flow

User / cron / stock event
→ provider-neutral Store enqueue
→ provider coordinator job
→ bounded child jobs
→ run/batch progress
→ mapping, state, event, and issue updates

The core owns the enqueue helper, run model, batch idempotency, company context,
scheduling discovery, and Dashboard reporting. Magento owns API discovery,
payloads, and per-batch execution.

## Run and batch tracking

- `ecommerce.sync.run`: Store, provider, operation, resource, total, queued,
  processed, succeeded, failed, skipped, status, timestamps, cursor, last error.
- `ecommerce.sync.batch`: unique `(run_id, key)` child-batch acknowledgement.
  Re-running the same batch does not double-count progress.
- Completion is recorded only after child batches report processed work.
- Cursor/watermark advancement happens on successful run completion.

## Operation fan-out

| Operation | Coordinator | Child unit |
| --- | --- | --- |
| Product import | Catalog coordinator | API page, configurable parent sorted first |
| Product export | Catalog export coordinator | Template batch |
| Product update | Catalog update coordinator | Mapped-template batch |
| Category import | Category coordinator | Top-level category subtree |
| Category export | Category export coordinator | Category batch |
| Customer import | Customer coordinator | API page |
| Order import | Order coordinator | Entity-ID batch |
| Finance import | Finance coordinator | Order-mapping batch |
| Shipment export | Shipment coordinator | Order-mapping batch |
| Inventory export | Inventory coordinator | Variant-mapping batch |
| Product wizard Export/Update | Store enqueue hook | 50-item product batch (configurable) |
| Stock cron/event | Existing targeted enqueue | Per-product or configured stock batch |

Batch sizes are Store fields with minimum/maximum validation. Defaults:
products/categories/customers 50, orders/finance 25, inventory 50,
shipments 100. Pagination has no silent 100/500/1,000 cap in coordinator paths.

## Failure isolation

- Provider page/batch workers catch record-level business errors, create
  fingerprint issues, and continue the batch.
- Retryable transport/auth errors still raise `RetryableJobError`.
- Child jobs retry independently through `queue.job.function` records.
- Permanent child failures are visible in run progress and Queue Jobs.
- One failed child does not stop unrelated children.
- Remote adoption/identity rules make replayed writes safe where possible.

## Scheduling

One core cron discovers due Store operations from provider-neutral
`_ecommerce_schedule_operations()`. It does not call provider APIs. Fixed
Magento crons are deactivated by migration; Store interval fields now determine
future enqueues.

## Known limits

- 10,000-record end-to-end Magento execution was not generated. The bounded
  chunking algorithm was unit-tested at 10,000 records (200 × 50).
- Finance coordinators rescan all imported orders into bounded child jobs;
  durable completed-record skipping is a future optimization.
- A permanently failed child leaves its batch unacknowledged; Queue Jobs and the
  failed job remain the operator signal.
