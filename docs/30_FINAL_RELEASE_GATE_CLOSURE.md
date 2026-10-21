# Final Release Gate Closure

## Gate results

| Gate | Status | Evidence |
| --- | --- | --- |
| G-01 genuine second Magento store-view order | PASS | Magento order 10, `store_id=2`; Odoo company 5, sale order 22, invoice 15 |
| G-02 Odoo 18 worker restart | PASS | Run 1: interrupted at 100/500, restarted, completed 500/500 |
| G-03 Odoo 17 worker restart | PASS | Run 1: interrupted at 100/500, restarted, completed 500/500 |
| G-04 scheduler multi-process concurrency | PASS | Two concurrent scheduler processes produced one active order job after unique identity index |
| G-05 Odoo 18 Dashboard matrix | PARTIAL | KPI accuracy, provider/backend/Store/date/Reset/drill-down pass; Company B is absent from the 18 fixture |
| G-06 Odoo 17 Dashboard matrix | PARTIAL | Same matrix as 18 via hash route; Company B absent |
| G-07 capability-aware wizard UX | PARTIAL | Execution blocked; unsupported options not dynamically removed |
| G-08 peak memory | PASS | 157,612 KB peak RSS, 500-update workload, 2 workers |
| G-09 finance cursor safety | PARTIAL | Separate new/reconcile cursors and no-starvation logic/test; 100k runtime fixture not executed |
| G-10 inventory race safety | PASS | Generation counter prevents clearing newer dirty state; deterministic test |
| G-11 cross-version regression | PASS | 76/76 on 19/18/17 |
| G-12 final release audit | CONDITIONALLY READY | Remaining Dashboard interaction and wizard UX limitations |

## Important finding and fix

During G-04 testing, two concurrent scheduler processes created duplicate active
order jobs despite advisory locking. OCA's identity index is non-unique. Core now
creates a unique partial index for `ecom:%` identities, safely cancels duplicate
active jobs during migration, and catches identity conflicts in the enqueue
helper. Re-test produced exactly one new active job.
