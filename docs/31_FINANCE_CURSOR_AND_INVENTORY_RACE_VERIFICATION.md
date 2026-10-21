# Finance Cursor and Inventory Race Verification

## Finance

Two independent cursors:
- `payment` — forward discovery of new imported order mappings.
- `payment_reconcile` — rolling reconciliation of older mappings.

Window = `finance_batch_size × 40` (default 1,000 order mappings). Each run
processes a bounded forward window and, independently, a bounded reconciliation
window. Continuous new orders cannot starve old orders.

Revisit latency at finance interval 30 minutes:
- 1,000 mappings: ≤1 run (~0.5 h)
- 10,000 mappings: ≤10 runs (~5 h)
- 100,000 mappings: ≤100 runs (~50 h)

`advance_cursor_on_partial=True` prevents a permanently invalid order from
blocking the cursor; its issue remains visible and a later wheel revisits it.
Financial mappings are reused, so retries do not duplicate invoices/payments/
credit notes.

Test: new window processes 5 synthetic mappings, then the independent reconcile
run processes the same 5 after forward cursor completion. The 1k/10k/100k
figures above are calculated bounds; a 100k live fixture was not generated.

## Inventory

`inventory_generation` is incremented on each stock event. A worker records the
generation before calculating quantity and clears `inventory_dirty` only if the
generation is unchanged at acknowledgement. A concurrent stock change therefore
leaves the mapping dirty and a later job pushes the newer absolute quantity.

Deterministic test patches the Magento client to bump the generation during the
remote write; the mapping remains dirty. The next stable run clears it and
records the latest quantity.

No-change scheduled reconcile queues zero mappings. Manual full resync remains
available.
