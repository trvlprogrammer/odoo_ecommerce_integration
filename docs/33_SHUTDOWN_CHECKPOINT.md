# Shutdown-Safe Checkpoint — 2026-10-21

## Status

Work is stopped at a safe checkpoint. No production writes, pushes, deployments,
tags, or publications were performed.

Current release decision: **CONDITIONALLY READY**.

## Branches and HEADs

Core:
- 19.0: `48e6be9` (current branch)
- 18.0: `e144632`
- 17.0: `80ff646`

Magento:
- 19.0: `fdad69d` (current branch)
- 18.0: `c49ea61`
- 17.0: `ca73a5f`

Both working trees were clean before this checkpoint document was added. No
unrelated changes are present. All branches remain independent.

## Completed in this assignment

- Finance durable two-cursor design: forward `payment` cursor and independent
  `payment_reconcile` cursor; bounded windows; partial-safe advancement.
- Inventory dirty tracking with `inventory_dirty`, `inventory_dirty_at`, and
  generation counter `inventory_generation`; no-change reconcile queues zero.
- Inventory lost-update protection: a worker clears dirty only if the observed
  generation is unchanged when it finishes.
- Per-record savepoints for catalog, customers, orders, finance, shipments,
  product export/update, inventory, and category imports.
- Queue provider/backend/Store metadata and deterministic Dashboard filtering.
- Unique active eCommerce identity index for queue jobs plus migration cleanup of
  duplicate active jobs and IntegrityError fallback.
- Real Magento second store-view order: Magento order 10, `store_id=2`.
  - Odoo Company B (id 5), Store 7, Backend 14.
  - Order mapping 32, Sale Order 22, company 5, total 42.95.
  - Invoice mapping 15, posted invoice company 5, total 42.95.
- Odoo 18 and 17 worker restart tests:
  - Each interrupted at 100/500 processed, restarted, completed 500/500, 0 failed.
- Scheduler two-process race:
  - Before unique index: duplicate active order jobs.
  - After fix: exactly one new active job.
- Peak memory: 157,612 KB peak RSS, 500-product update workload, 2 Odoo workers.
- Dashboard filter reset control added; populated KPI/filter/drill-down verified
  on 19/18/17. Full date/reset matrix remains partial.

## Test evidence

- Odoo 19: 76/76 pass — `logs/final-gate19.log`
- Odoo 18: 76/76 pass — `logs/final-gate18.log`
- Odoo 17: 76/76 pass — `logs/final-gate17.log`
- 10k run id 7: done, 10,043 processed, 10,043 succeeded, 0 failed.
- Core-only installs pass on 19/18/17.
- Uninstall isolation passes on 19/18/17.
- Existing DB copy upgrades preserve mapping counts/hashes; scheduler adds one
  cron record.
- Dashboard KPI expected/actual exact on 19/18/17.

## Known limitations / pending work

1. Odoo 18/17 Dashboard full date/reset/filter permutation matrix is partial.
2. Capability-aware wizard still blocks execution via `can_queue`/server checks,
   but unsupported options are not dynamically removed from the selection list.
3. Finance cursor 100k synthetic runtime fixture not executed; no-starvation
   bounds are documented (≈50 h max revisit at 30-minute scheduling).
4. Peak memory measured on a 500-update workload, not the 10k catalog run.
5. G-01 separate Magento store-view E2E was executed on Odoo 19 only; 18/17 have
   equivalent connector logic tests.
6. The latest core docs qualification commit `48e6be9` is on 19.0 only; 18/17
   have the prior gate-closure docs but not this last documentation-only commit.

## Running processes at checkpoint

- Odoo 19 server on port 8092 was running before shutdown (DB
  `e2e_accept_19`, 2 workers, OCA jobrunner).
- Docker containers: `magento-e2e-nginx`, `magento-e2e-php`,
  `magento-e2e-opensearch`, `magento-e2e-db`, `odoo-dev-postgres`.
- Odoo 8092 was stopped as part of this shutdown checkpoint. Docker containers
  were intentionally left as-is for the host shutdown.

Start Odoo 19 resume command:

```bash
cd /home/ridho/Data/odoo-dev/19/odoo-src
/home/ridho/Data/odoo-dev/19/venv/bin/python odoo-bin \
  -c /home/ridho/Data/odoo-dev/19/config/odoo.conf -d e2e_accept_19 \
  --addons-path=/home/ridho/Data/odoo-dev/19/odoo-src/addons,/home/ridho/Data/odoo-dev/19/odoo-src/odoo/addons,/home/ridho/Data/odooapps/odoo_ecommerce_integration,/home/ridho/Data/odooapps/odoo_ecommerce_magento,/home/ridho/Data/odoo-dev/oca/queue \
  --load=web,queue_job --workers=2 --max-cron-threads=0 --http-port=8092
```

## Exact safe resume action

1. Confirm both repositories are clean and on `19.0`.
2. Restart Odoo 19 with the command above.
3. Continue with the remaining Dashboard date/reset matrix and wizard UX only
   after reviewing `docs/30_FINAL_RELEASE_GATE_CLOSURE.md` and
   `docs/31_FINANCE_CURSOR_AND_INVENTORY_RACE_VERIFICATION.md`.
4. Do not rerun the 10k catalog test unless catalog behavior changes.
5. Do not push, deploy, tag, or publish.
