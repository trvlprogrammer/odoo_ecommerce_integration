# 10,000-Product Magento E2E Report

Status: **PASS** (Odoo 19, real local Magento REST API, real OCA jobrunner).

## Environment

- Magento Open Source 2.4.7-p3, local Docker environment.
- Odoo 19, disposable database `e2e_accept_19`.
- Two Odoo workers; one OCA queue jobrunner observed.
- Store batch/page size: 100 products.
- Test date: 2026-10-21.

## Fixture

- 10,000 deterministic simple products `SCALE10K-00000` … `SCALE10K-09999`,
  created through Magento REST `POST /rest/V1/products`.
- 16 bounded concurrent seeding workers; 0 seed failures; 965.5 seconds.
- Existing configurable/simple products, categories, customers, orders,
  invoices/payments, shipments, and inventory retained.
- Magento product total after seeding: 10,043.

## Import execution

- Triggered through `action_sync_catalog` → core enqueue → Magento catalog
  coordinator → one child job per 100-record API page.
- Run 7: total 10,043, processed 10,043, succeeded 10,043, failed 0,
  skipped 0, state `done`.
- Child jobs: 101, all `done`.
- Runtime: 06:54:12 → 07:08:29 = **857 seconds**.
- Throughput: **11.72 records/second**.
- Sum of child execution time: 833.05 seconds; average 8.25 s/child.
- Approximate import API requests: 102 (1 total-count discovery + 101 pages).
- Queue wait: approximately 24 seconds across the run (with one runner).
- Odoo database growth: 82.5 MB → 122.3 MB (≈39.8 MB).
- Peak worker memory was not captured; post-run worker RSS was ~130–157 MB each.
- Duplicate active external mappings: 0.
- Reconciliation: 10,000 `SCALE10K-*` Odoo templates; 10,000 active mappings
  for those templates. Exact match.

## Worker interruption during the run

The Odoo server was stopped at approximately 4,300 processed records and
restarted 8 seconds later. OCA queue_job re-queued the in-flight/pending work.
The run resumed, finished with exactly 10,043 processed, 0 failures, and no
duplicate mappings. This is actual worker-restart evidence, not a unit-only
simulation.

## Notes

- Total processed 10,043 includes pre-existing products; mappings for scale
  products are exactly 10,000 because some existing configurable children share
  parent mappings.
- Invalid/duplicate/error scenarios are covered by targeted automated tests,
  not by the 10k catalog fixture (Magento rejects duplicate/missing-SKU products
  at creation).
- Dashboard after the run loaded with 10,032 eligible Odoo products and 10,031
  mapped products, and the Product Mappings drill-down rendered 10,000+ records.
