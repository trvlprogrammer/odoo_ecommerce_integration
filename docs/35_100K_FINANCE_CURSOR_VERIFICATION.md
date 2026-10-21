# 100K Finance Cursor Verification

## Fixture

- Disposable Odoo 19 database `finance100k19`.
- 100,000 imported order mappings inserted for one Store/Backend.
- No remote Magento API calls and no 100,000 accounting documents.
- Actual Magento connector `_finance_window_ids` used.

## Selection results

- Window: 1,000 mappings.
- Forward cursor: 100 windows, 100,000 mappings, 0.081 s total (~0.81 ms/query).
- Reconciliation cursor: 100 windows, 100,000 mappings plus one wrapped window,
  0.08 s total (~0.80 ms/query).
- Maximum revisit interval at 30-minute finance scheduling: 50 hours for 100k.
- Continuous new mappings advance the forward cursor; the independent
  reconciliation cursor still reaches old mappings (no starvation).
- Query plan used the `(store_id, import_status)` index and returned bounded
  windows; no unbounded full table materialisation.

## Late-event behavior

Reconciliation revisits older orders independently. Financial processing remains
idempotent through existing invoice/payment/refund mappings. Late-event tests at
small scale pass; a 100k live Magento financial event stream was not generated.

## Latency policy

50 hours is the worst-case full-wheel revisit at 100k/30 minutes. Operators with
very large financial tables can reduce the finance interval or increase
`finance_batch_size`; the cursor logic remains bounded and starvation-free.
