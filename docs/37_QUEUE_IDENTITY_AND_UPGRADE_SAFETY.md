# Queue Identity and Upgrade Safety

## Index

```sql
CREATE UNIQUE INDEX queue_job_ecommerce_identity_active_uniq
ON queue_job (identity_key)
WHERE identity_key LIKE 'ecom:%'
  AND state IN ('pending', 'enqueued', 'wait_dependencies');
```

- NULL identity keys are excluded.
- Unrelated OCA jobs are unaffected.
- Integration identity keys include Store scope, preventing cross-Store dedupe.
- Provider/Store/backend metadata remains on each job.

## Concurrency

Two independent scheduler processes created duplicate active jobs before the
index. After migration and index creation, the same race produced one active job.
The enqueue helper uses a savepoint and returns the existing job on IntegrityError.

## Migration

Pre-migrate cancels only duplicate active `ecom:%` identities, keeping the lowest
id and marking the rest cancelled. Completed/failed history is untouched.
Migration is idempotent.

## Uninstall/lifecycle

Magento uninstall isolation passes on 19/18/17: Magento-method jobs removed;
core and unrelated jobs retained. Core module remains installed.
