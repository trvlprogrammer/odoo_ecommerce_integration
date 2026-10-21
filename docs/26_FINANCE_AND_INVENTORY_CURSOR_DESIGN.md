# Finance and Inventory Cursor Design

## Finance

Finance uses a bounded, wrapping reconciliation window over imported order
mappings.

- State: `ecommerce.sync.state` resource `payment`, cursor = last order-mapping id.
- Window: `finance_batch_size × 10` (default 25 × 10 = 250 orders/run).
- Coordinator selects imported order mappings with `id > cursor`.
- At the end of the sequence it wraps to the first window; this guarantees
  eventual reconciliation of late invoices, payments, and credit memos without
  an unbounded scan every run.
- Child batches are independently queued and acknowledged through
  `ecommerce.sync.batch`.
- Cursor advances only when the run completes. `advance_cursor_on_partial=True`
  lets finance move past permanently invalid records while keeping their issues
  visible; they are revisited in a later reconciliation cycle.
- No Odoo financial document is created twice: existing invoice/payment/refund
  mappings are reused.

Limitation: late financial events are discovered on the next reconciliation
window that reaches the relevant order, not necessarily on the immediately next
run. This is an explicit eventual-completeness tradeoff.

## Inventory

Inventory uses dirty tracking rather than an append-only cursor.

- `ecommerce.variant.mapping.inventory_dirty` defaults to true.
- Stock move/quant events mark affected Store mappings dirty and enqueue
  targeted product jobs.
- Successful or unchanged pushes clear the dirty flag; failures leave it set.
- The generic scheduler calls `inventory` / `reconcile`, which processes only
  dirty mappings in bounded batches.
- Manual `action_push_inventory` remains a full resynchronization of all active
  mappings for that Store.
- Quantities are recalculated at execution time and written as absolute values,
  avoiding stale queued quantities overwriting newer stock.
- No-change reconciliation therefore queues zero mappings.

## Migration

New fields:
- `ecommerce.sync.run.advance_cursor_on_partial`
- `ecommerce.variant.mapping.inventory_dirty`
- `ecommerce.variant.mapping.inventory_dirty_at`

Odoo creates these columns during module upgrade. No populated mapping table is
recreated. Existing variants become dirty and are reconciled once.
