# 03 — SaaS Feature Parity Matrix

## 1. Method and limits

This matrix compares the read-only SaaS Magento V1 reference with the intended
native Odoo connector. It is **evidence-based**, not a claim that all SaaS
behavior transfers mechanically.

Evidence used:

- SaaS source under `app/providers/magento/`, `app/services/magento_*`,
  `app/models/magento_*`.
- SaaS tests under `tests/test_magento*.py` (17 modules, ~4,007 lines).
- SaaS Magento docs under `docs/magento/`.
- Historical SaaS acceptance claim: 1,676 backend tests, 12/12 live Magento
  scenarios, 2026-10-17. **Not re-executed in this phase.**

Status legend:

| Status | Meaning |
| --- | --- |
| `SAAS-FULL` | Implemented and covered by SaaS tests/docs |
| `SAAS-PARTIAL` | Implemented with a documented limitation or weak evidence |
| `SAAS-DIFF` | Native Odoo must use a different mechanism |
| `NATIVE-NEW` | Not implemented in SaaS; required for a safe native module |
| `DEFERRED` | Explicitly out of V1 |

## 2. Connection and scope

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Magento authentication | Integration access token; `test_magento_provider.py`, `test_magento_connections.py` | Backend stores base URL + token; test connection is explicit; auth failure produces sanitized issue | `ecommerce.backend`, REST token | Health job | Valid token succeeds; bad token fails without secret leakage | Admin user/password token not default |
| Multiple stores | One SaaS Store ↔ website + store view; `test_magento_store_views.py` | Many `ecommerce.store` rows per backend; each with website/view scope | `ecommerce.store` | Per-store jobs | Two scopes import isolated orders | One store view per store; duplicate binding rejected |
| Websites / store views | `list_website_scopes`, website `base`, views `default`/`id` | Discover and bind; store view code selects REST scope | Magento `/V1/store/...` | Setup action | Binding validates remote existence | Store group is not a store scope |
| Connection validation | MSI and store scope probes; capability flags | Test connection + capability flags (MSI, RMA, webhooks) without writes | `/V1/store/storeViews`, `/V1/inventory/sources` | On demand | Ready only if required capabilities exist | RMA false on Open Source |
| Credential management | Encrypted secret store in SaaS | Odoo backend fields restricted to manager; no event/job/log exposure | `ecommerce.backend` | None | Token never appears in UI list, logs, jobs, issues | Native at-rest behavior documented in `11` |
| Company pairing | Store ↔ Odoo company | Store.company_id required; lookups forced to company | `ecommerce.store` | All jobs | Cross-company store cannot be used | One company per store |

## 3. Catalog

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Product discovery | `magento_catalog_sync.py`, `test_magento_catalog.py` | Paginated import of simple/configurable products into mapping/cache | `/V1/products` searchCriteria | Catalog job | Full page loop completes; no duplicate mapping | Page size bounded |
| Simple products | Both directions; `test_magento_product_sync.py` | Import/create `product.template` + `product.product`; template/variant mappings | `/V1/products`, `/V1/products/{sku}` | Catalog job | Round trip by SKU is idempotent | Images deferred |
| Configurable products | Parent/child, options, child links; `test_magento_product_sync.py` | Create Odoo attributes/values and variants; parent template mapping, child variant mappings | `/V1/products`, `/V1/products/attributes`, `/V1/configurable-products/*` | Catalog job | Round trip T-Shirt S/M/L idempotent | Rebuild with unsafe deltas blocked |
| Variants | Child `entity_id` is mapping grain | `product.product` ↔ external child/variant | Variant mapping | Catalog job | Order line resolves to exact variant | No bundle/grouped/virtual/downloadable |
| Product attributes | Attribute discovery/ensure select attribute | `product.attribute` mapping by external code/ID | `/V1/products/attributes` | Catalog job | Attribute reuse does not duplicate | Magento attribute sets not fully modeled |
| Attribute values | Option labels/values | `product.attribute.value` mapping | `/V1/products/attributes/{code}/options` | Catalog job | Value mapping stable across runs | Locale/label changes require reconciliation |
| Product mapping | `magento_product_mappings`; unique active external/Odoo per store | Core product + variant mappings; manual and SKU auto methods | Core mapping models | Mapping action | Duplicate active mapping impossible | SKU is not a global key |
| SKU matching | Normalized SKU auto-map | Normalize case/space per documented rule; ambiguity → issue | Variant mapping | Mapping job | Unique SKU auto-maps; duplicate SKU fails | No silent overwrite |
| Product updates | Field ownership and export/import flows | Update only owned fields; no destructive structural rewrite | Product endpoints | Catalog job | Repeat sync is idempotent; conflicting fields produce issue | Post-import order edits not relevant |
| Publication / visibility | Explicit status/visibility handling | Explicit publish/unpublish action; never implicit | `/V1/products` status/visibility | Catalog job | Hidden product stays hidden unless requested | No Shopify-style publishable semantics |
| Inventory (catalog view) | Separate inventory V1 | Inventory is not part of catalog job | SourceItem | Inventory job | See inventory section | No product/catalog write in inventory job |

## 4. Customers

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Customer discovery | `magento_customer_mapping.py`, `test_magento_customers.py` | Paginated website-scoped discovery; never cross-website merge | `/V1/customers/search` | Customer job | Website filter applied; mapping isolated | Customer email not globally unique |
| Customer mapping | `magento_customer_mappings` keyed by customer + website | `res.partner` ↔ customer ID + store; unique per store | `ecommerce.customer.mapping` | Customer job | Repeat mapping does not duplicate | Guest has no customer mapping |
| Create in Odoo | Explicit create action; uncertain outcome handling | Create partner; persist mapping before/after with adoption by email + external ID | `res.partner` | Customer job | Retry adopts, no duplicate partner | PII minimized |
| Billing address | Order billing address | Use/create invoice partner; preserve address lines | `res.partner` | Order job | Address matches Magento order | Address normalization limited |
| Shipping address | Order shipping address | Use/create delivery partner; preserve address lines | `res.partner` | Order job | Address matches Magento order | No address book sync |
| Guest customers | Guest orders; no customer mapping; deterministic reuse | Reuse one commercial partner per email/store; delivery child; no guest mapping | `res.partner` order fields | Order job | Repeated guest orders reuse commercial partner | Ambiguous email identity → issue |
| Duplicate prevention | Email/customer mapping checks | Store-scoped constraints plus explicit match; no fuzzy merge | Mapping + partner | Order/customer job | Re-run does not create second partner | Manual review for conflicts |

## 5. Orders and economics

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Order import | `magento_order_import.py`, `test_magento_orders.py`, `test_magento_order_fidelity.py` | Create/adopt sale.order from Magento order | `/V1/orders/{id}` | Order job | Order created exactly once | No post-import edits |
| Incremental sync | `entity_id_gt` cursor + bounded pages | `ecommerce.sync.state` entity cursor + overlap window | `/V1/orders` search | Discovery job | No gaps/duplicates across pages | Cursor must not advance on failure |
| Order line mapping | `magento_order_line_mappings` per item | Unique order mapping + item ID; optional child item ID | Core order line mapping | Order job | Every line maps to one Odoo line | Configurable parent/child identity preserved |
| Order status | Magento `state` + `status` recorded | Store external state/status; Odoo state is native | Order mapping | Order job | State not overwritten by import retry | No full state machine mirror |
| Confirmation | Optional auto-confirm; blocked on mismatch | `action_confirm` only after total check; failure issue | `sale.order` | Order job | Confirmed once; mismatch never auto-confirms | No cancellation automation |
| Discounts | Item discount amount converted to line discount | Preserve gross price and discount; compare totals | Order line | Order job | Odoo total within tolerance or issue | Exotic Magento rules may mismatch |
| Shipping charges | Net shipping amount on a mapped delivery method | Carrier mapping product or carrier delivery product | Core carrier mapping | Order job | Shipping charge and description preserved | Missing delivery mapping fails safely |
| Tax calculations | Magento tax amounts recorded; Odoo taxes drive totals | Use Odoo product/shipping taxes; compare Magento total | Odoo taxes | Order job | Mismatch creates issue and blocks auto-confirm | No tax-rate mapping table in V1 |
| Currency | Magento currency resolved in Odoo | Resolve active currency; fail if missing | `res.currency` | Order job | Currency matches order | No FX conversion invention |
| Idempotency | `entity_id` unique per store; adopt sale order by origin | Core unique constraint; adopt by durable origin/name | Order mapping | Order job | Re-import returns existing mapping | Increment ID collision fails safely |
| Order name | `increment_id` as sale.order.name (post-freeze change) | Use increment ID for new orders; never rename existing | `sale.order.name` | Order job | Merchant-facing name matches Magento | Durable key remains entity_id |
| Guest order addresses | Commercial + invoice + delivery contacts | Same, with deterministic reuse | `res.partner` | Order job | One commercial partner on repeat guest email | No marketing consent sync |

## 6. Financial workflows

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Invoice creation | `magento_financial.py`, `test_magento_financial.py` | Create invoice from imported sale.order | `account.move` | Finance job | One invoice per order mapping | Odoo invoice is primary |
| Invoice posting | Post after create | `action_post`; persist posted state | `account.move` | Finance job | Posted once; retry detects existing | Posting failure issue |
| Payment registration | Paid Magento invoice evidence + method → journal | Register payment against posted invoice; match memo first | `account.payment` | Finance job | One payment per evidence key | Manual if method/amount ambiguous |
| Payment adoption | Search Odoo payments by deterministic memo | Adopt exactly one; >1 → manual review | Payment mapping | Finance job | Crash/retry does not double-pay | No fuzzy amount/time matching |
| Payment method mapping | Stable method code → journal | Core payment method mapping per store | `ecommerce.payment.method.mapping` | Config + finance job | Unmapped method blocks with issue | No guessing by label |
| Refund / credit memo | `magento_refund.py`, `test_magento_refunds.py` | Import credit memo to Odoo credit note | `/V1/creditmemo` | Refund job | Credit note once; amount/line fidelity | Requires existing Odoo invoice |
| Credit memo idempotency | `entity_id` mapping | Unique store + credit memo ID | Refund mapping | Refund job | Retry adopts, no duplicate credit note | Manual if invoice missing |
| Refund payment | Weak gateway evidence; often manual | Out of V1 unless explicit later milestone | `account.payment` | Deferred | No invented refund payment | Magento payment evidence edition/gateway dependent |
| Financial state transitions | Invoice/payment/credit status persisted | Mapping state + Odoo document state; no fake states | Financial mappings | Finance job | State transitions are monotonic and auditable | Partial flows require review |
| Duplicate economic documents | Unique mappings + memo adoption | Database constraints + adoption queries | Financial mappings | Finance job | Cannot create two invoices/payments/credit notes for one evidence key | Manual resolution for pre-existing duplicates |

## 7. Inventory and fulfillment

| Capability | SaaS evidence | Native Odoo expectation | API / models | Queue | Acceptance | Limits |
| --- | --- | --- | --- | --- | --- | --- |
| Inventory source mapping | One source per store; `test_magento_inventory.py` | Odoo warehouse/stock location ↔ Magento `source_code` | `ecommerce.inventory.source.mapping` | Config | Missing source blocks sync | Multi-source V1 not supported |
| Quantity calculation | On-hand − reserved − safety; kit complete units | Same formula, company/warehouse scoped | `stock.quant`, phantom BOM | Inventory job | Matches SaaS fixture formulas | Magento reservations not mirrored |
| Absolute push | `SourceItem` POST | Absolute quantity, not delta | `/V1/inventory/source-items` | Inventory job | Repeated push is idempotent | Writing salable directly forbidden |
| Kits | Phantom BOM complete kits, safety once | Same, fail ambiguous BOM | `mrp.bom` | Inventory job | Kit SKU receives floor(complete kits) | Only one phantom BOM |
| Inventory idempotency | Last pushed quantity | Store per variant/source last successful target | Sync state / mapping | Inventory job | Unchanged target performs no write | Last pushed only after success |
| Picking identification | Completed outgoing deliveries for sale order | Use done `stock.picking` / moves in store company | `stock.picking` | Shipment job | Only completed outgoing deliveries | Backorders supported as separate pickings |
| Shipment creation | `magento_shipment_sync.py`, `test_magento_shipments.py` | Create Magento shipment from delivered quantities | `/V1/order/{id}/ship` | Shipment job | Partial shipment correct | No post-create tracking update |
| Tracking | Optional tracks at creation | Push tracking when present | Shipment API | Shipment job | Tracking copied once | Later Odoo tracking changes not synced |
| Fulfillment idempotency | One mapping per store+picking; exact adoption | Unique picking mapping; adopt exact item/qty signature | Shipment mapping | Shipment job | Retry does not duplicate shipment | Ambiguous adoption → issue |
| Kit shipment | Complete kit quantity to parent item | Convert delivered components to parent quantity | Order line mapping | Shipment job | Kit parent qty correct | Complex BOMs manual |
| Unsafe quantities | Guard against over-shipment | Cap by ordered/shipped quantities; fail if unsafe | Shipment mapping | Shipment job | Never ship more than ordered | Manual for rounding ambiguity |

## 8. Operational behavior

| Capability | SaaS evidence | Native Odoo expectation | Acceptance | Limits |
| --- | --- | --- | --- | --- |
| Pagination | Products 100/page; orders/customers 50/page | Bounded pages; no unbounded loop | Full catalog/order set completes | Magento `total_count` may be approximate |
| API timeout | `httpx` default timeout | Explicit connect/read timeout in adapter | Timeout raises retryable error | No infinite waits |
| Retries | Automation retry, not explicit HTTP retry | OCA `queue_job` retryable exceptions + backoff | 429/5xx/timeouts retry; 4xx business errors do not | Writes adopt-before-retry |
| Rate limits | No explicit `429/Retry-After` handling found | Respect `Retry-After`, backoff, bounded concurrency | 429 does not hammer Magento | Needs live verification |
| Incremental cursors | Order `entity_id_gt`; overlap in SaaS design | Persistent cursor + overlap; cursor advances only after job success | No missed entity on retry | Products/customers need explicit strategy |
| Multi-company isolation | SaaS org/store scoping | Odoo record rules + company context | Cross-company access denied | Admin bypass is expected Odoo behavior |
| Logging | IntegrationEvent, redaction | Core event log; no secrets/PII | Event trace per operation | Retention policy required |
| Recovery | Adopt-before-retry, manual review, safe actions | Queue requeue + state re-check + issue resolution | Crash/retry safe | No arbitrary “retry all” |
| Concurrency | SaaS advisory locks/automation | queue channel capacity + Postgres advisory lock per store/resource | No duplicate concurrent sync | Must not block unrelated stores |
| Monitoring | Deterministic rules/issues | Core issue model with fingerprints and severities | Repeated failure deduplicates | No AI-driven recovery |
| UI | Next.js operations UI | Native Odoo views/menus/buttons | All operations reachable in Odoo | No frontend duplication |

## 9. Native differences that must not be copied blindly

| SaaS pattern | Native Odoo pattern |
| --- | --- |
| SQLAlchemy models + Alembic | Odoo ORM models + module upgrade scripts |
| FastAPI endpoints | Model methods, buttons, cron dispatchers |
| External JSON-2 Odoo API | Direct ORM inside Odoo |
| SaaS PostgreSQL mappings | Native Odoo mapping tables |
| Background worker/automation tables | OCA `queue_job` + Odoo cron |
| Next.js UI | Odoo list/form/search/kanban views |
| Fernet secret store | Odoo manager-only credential fields + deployment controls (see `11`) |
| SaaS tenant/organization | Odoo company + record rules |
| SaaS cursor tables | `ecommerce.sync.state` |

## 10. Deferred V1 capabilities

- Magento product images
- Bundle, grouped, virtual, downloadable products
- Multi-source MSI and allocation algorithms
- Adobe Commerce RMA
- Post-import order edits and cancellations
- Refund payment registration from weak gateway evidence
- Tax-rate mapping/automatic tax correction
- Webhooks/event bus
- Shopify implementation

## 11. Parity conclusion

The SaaS reference demonstrates the required V1 business outcomes for
connection, catalog, customers, orders, financial documents, inventory, shipment,
and monitoring. It also demonstrates where ambiguity must fail to manual review.

Native Odoo changes the implementation mechanism substantially. The connector is
therefore a behavior-preserving port, not a line-by-line port. Each row marked
`SAAS-DIFF` or `NATIVE-NEW` requires an explicit Odoo acceptance test before the
M9 gate can pass.
