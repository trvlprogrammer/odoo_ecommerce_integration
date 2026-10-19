# 01 — Architecture

## 1. Objective

Build native Odoo modules that synchronize Magento Open Source and Odoo without
the SaaS runtime. Odoo is the system of record for products, stock, customers,
sales orders, invoices, payments, deliveries, and credit notes. Magento remains
the commerce system of record for its catalog presentation and shopper orders.

The free core provides shared identity, mappings, orchestration, queue jobs,
logging, monitoring, and security. The paid connector provides Magento API
behavior, Magento-specific configuration, and Magento workflows.

## 2. Non-goals for Phase 1

- No Shopify implementation. Shopify must fit the shared interfaces later, but
  no speculative Shopify fields or workflows are added now.
- No Magento Admin UI replacement.
- No custom Magento module.
- No SaaS dependency, FastAPI process, external PostgreSQL, or Next.js UI.
- No multi-source MSI, RMA, product images, bundle/grouped/downloadable,
  post-import order editing, or automatic refund payment in V1.
- No Odoo 18/17 code until the preceding acceptance gate passes.

## 3. Module boundaries

```
                    +--------------------------------------+
                    | odoo_ecommerce_integration (LGPL-3)  |
                    | backend/store, mappings, state,      |
                    | events/issues, queue orchestration,  |
                    | security, native views               |
                    +------------------+-------------------+
                                       |
                         depends on    |    depends on
                                       v
                    +--------------------------------------+
                    | odoo_ecommerce_magento (OPL-1)       |
                    | Magento config, REST adapter,        |
                    | catalog/customer/order/finance/       |
                    | inventory/shipment jobs              |
                    +------------------+-------------------+
                                       |
                                       v
                    Magento Open Source REST Admin API

External, independently installed dependency:

                    OCA queue_job (LGPL-3) -> PostgreSQL job table
```

The core **must not import** any Magento module. The connector may import core
models and services. The connector owns all Magento field names, URLs, payloads,
and error mappings.

Core dependencies in the eventual manifest:

`base`, `mail`, `sale_management`, `stock`, `account`, `queue_job`

The sale/stock/account dependencies are deliberate: core mappings point to real
Odoo records (`sale.order`, `stock.picking`, `account.move`, `account.payment`).
Generic integer links or `ir.model` indirection would weaken referential
integrity and record rules.

The connector manifest depends on `odoo_ecommerce_integration` and declares
`license: OPL-1`. It does not vendor `queue_job`.

## 4. Core design decisions

### 4.1 Backend versus store

- `ecommerce.backend` = one external installation and credential set.
  For Magento: one base URL and one integration token.
- `ecommerce.store` = one commercial scope inside that installation.
  For Magento: one website plus one store view, one Odoo company, one warehouse,
  one pricelist/currency policy, and one set of workflow flags.

One Magento installation may expose several websites/store views. Creating one
backend per website would duplicate credentials and make connection testing
ambiguous. One store per website/store-view pair preserves scope isolation.

Every mapping and state row belongs to both a backend and a store. The store's
company is stored/related on the row for fast record rules and indexes.

### 4.2 Mapping grain

- External **parent product** ↔ `product.template` via product mapping.
- External **sellable variant** ↔ `product.product` via variant mapping.
- Order lines and inventory always use the **variant mapping**.
- Magento simple products receive a template mapping and a variant mapping; the
  single Odoo variant is the operative sellable row.
- Magento configurable parents map to an Odoo template and their children map to
  Odoo variants. Attribute/value mappings preserve the option identity.

### 4.3 External identity

External ID formats are preserved as text. The core does not assume numeric IDs,
Shopify GIDs, UUIDs, or any prefix. Durable identity is:

- Magento order: `entity_id` (name/increment ID is display data, not identity).
- Magento product: `entity_id`; SKU is a matching aid, not the sole key.
- Magento customer: `entity_id` plus website/store scope.
- Magento invoice, shipment, credit memo: respective `entity_id`.
- Magento source: `source_code`.
- Magento order item: `item_id`.

Uniqueness is always scoped to a store (which is scoped to a backend and
company). No global external-ID unique constraint is allowed.

### 4.4 Synchronous versus asynchronous

Configuration edits and list/form reads are synchronous. All API-bound work runs
through OCA `queue_job`:

- catalog discovery/import/export
- customer discovery/import
- order discovery/import/confirmation
- invoice/payment workflows
- inventory calculation/push
- shipment creation/adoption
- credit memo import
- reconciliation and scheduled polling

A save button may create a job and return immediately. It must not perform an
unbounded API operation inside the web request.

### 4.5 Transaction boundaries

Each queue job runs in its own Odoo transaction. Within a job:

1. Re-read local state inside the transaction.
2. Perform remote reads.
3. Persist local intent/state before a non-idempotent remote write where needed.
4. Perform the remote write.
5. Persist the durable mapping locally.

If the remote write outcome is uncertain, the next attempt searches for the
remote object by a durable fingerprint before creating anything. Ambiguity is a
manual-review issue, never a blind retry.

## 5. Data flows

### 5.1 Inbound order

```
Magento order (entity_id)
  -> connector adapter (typed DTO)
  -> order mapping (importing)
  -> validate store scope, lines, product variant mappings
  -> create/adopt res.partner contacts and sale.order
  -> enrich order lines from Magento amounts (price, discount, shipping)
  -> compare Odoo total to Magento grand total
  -> optional action_confirm only when total is matched/within tolerance
  -> persist order/line mappings
  -> event; issue on failure
```

`sale.order.name` uses Magento `increment_id` for merchant recognition. Durable
idempotency remains the order mapping keyed by `entity_id`. If the increment ID
collides with an unrelated Odoo order, import fails safely rather than merging.

### 5.2 Financial workflow

```
Magento paid invoice evidence
  -> order mapping must be imported
  -> create Odoo invoice from sale.order; post it
  -> match Magento payment method code to Odoo journal
  -> find existing Odoo payment by deterministic memo before creating one
  -> register payment only when amount/currency/residual checks pass
  -> persist invoice/payment mappings
  -> event; manual-review issue on ambiguity
```

Odoo invoice is the primary accounting document. A Magento invoice ID is attached
when present, but the workflow does not depend on Magento having created an
invoice first. Magento paid invoices are payment evidence, not an instruction to
duplicate an accounting document.

### 5.3 Outbound inventory

```
Odoo product variant + mapped warehouse stock location
  -> on-hand / reserved / safety / phantom-kit calculation
  -> absolute integer target per Magento source_code
  -> skip when last successful target is unchanged
  -> POST SourceItem quantity
  -> persist last pushed quantity only after success
```

Only one active Magento source mapping per store in V1. Odoo is the quantity
source. Magento reservations/salable aggregation are not overwritten.

### 5.4 Outbound shipment

```
Odoo completed outgoing delivery (stock.picking)
  -> determine delivered quantities from done moves
  -> convert to Magento order item quantities, including configurable parents
  -> adopt an existing Magento shipment only on exact item/quantity match
  -> create Magento shipment with optional tracking
  -> persist shipment mapping
```

After the Magento shipment exists, later tracking changes in Odoo are not pushed
in V1. This is an accepted limitation inherited from the SaaS reference.

### 5.5 Inbound credit memo

```
Magento credit memo (entity_id)
  -> require imported order and an existing Odoo invoice
  -> map credit lines to invoice lines / products
  -> create and post Odoo credit note
  -> persist refund mapping
  -> manual review if identity or amount is ambiguous
```

RMA is not implemented for Magento Open Source. Refund payment registration is
manual/out of scope for V1 unless a later explicit milestone expands it.

## 6. Scheduled orchestration

Odoo cron methods are thin dispatchers. They enqueue queue jobs; they do not
perform API work directly.

Suggested schedules:

| Work | Default interval | Job |
| --- | --- | --- |
| Order polling | 5 minutes | per-store order discovery |
| Customer polling | 30 minutes | per-store customer discovery |
| Catalog polling | 60 minutes | per-store catalog reconciliation |
| Inventory push | 15 minutes | per-store inventory sync |
| Shipment scan | 15 minutes | per-store completed-delivery scan |
| Credit memo scan | 30 minutes | per-store credit memo scan |
| Connection health | 30 minutes | per-store connection test |

Intervals are stored on the store, not hard-coded in cron XML. Manual sync
buttons enqueue the same jobs. Disabled scheduled sync does not block an
authorized manual sync.

## 7. Multi-company and multi-store

- `ecommerce.backend.company_id` is required.
- `ecommerce.store.company_id` is required and must match its backend.
- Every mapping/state row has `company_id` related from its store.
- Record rules restrict all core records to the user's allowed companies.
- A user with access to company A cannot see, enqueue, retry, or resolve company B
  records.
- Odoo product/partner/sale/stock/account lookups are executed with the store's
  company in context. Cross-company records are rejected.
- Two stores may share one Odoo company or use different companies, but a store
  has exactly one company.
- One Odoo variant may be mapped in several stores; mapping uniqueness is per
  store, not global.

## 8. Security boundaries

- Credentials live only on the backend and are readable only by the manager
  group. They are never included in events, issues, job descriptions, or logs.
- Magento base URLs are normalized and validated. Outbound requests must not
  follow redirects to a different host. HTTP is allowed only for explicit
  loopback development.
- External API errors are sanitized before storage; Magento may echo request
  bodies or customer data.
- Record rules enforce company isolation at ORM level.
- Mapping edits are privileged operations; ordinary users may read status.
- Financial actions require manager/accounting rights and are auditable.

## 9. Native views

Minimum UI:

- Backends: connection, store scopes, test connection, capability flags.
- Stores: company, warehouse, source, currency, workflows, schedules.
- Mappings: product/variant/customer/order lists with filters and manual link.
- Sync state: cursor/watermark, last run, status, error.
- Events: chronological log with severity and entity links.
- Issues: open/resolved, retry safe action, manual review.
- Queue jobs: standard OCA `queue.job` views; no custom job engine.

No custom frontend. Use Odoo list/form/search views, menus, status ribbons, and
smart buttons. Long operations use buttons that enqueue jobs and show a
notification; list views must not trigger network calls per row.

## 10. Portability to Odoo 18/17

The core's business models and mappings remain stable. Porting differences are
isolated in:

- ORM constraint declaration (`models.Constraint` on 19; `_sql_constraints` on
  17/18).
- OCA `queue_job` branch/version and any API changes.
- Odoo account/sale/stock method signatures used by the connector.
- View/asset syntax where changed.

The connector must not copy 19.0 source blindly. Each version branch is
independently installed, migrated, and accepted. See `09_ODOO_18_17_PORTING_PLAN.md`.

## 11. What is deliberately not in the core

- Magento URLs, headers, payload builders, or error codes.
- Shopify GIDs or Shopify-specific fields.
- Magento product-type rules, MSI source semantics, or credit memo logic.
- Any financial calculation that invents data not present in Odoo or Magento.
- Any background worker process outside OCA `queue_job`.

## 12. Architecture acceptance criteria

- Core installs with only its declared dependencies on Odoo 19.
- Connector installs after core and `queue_job`, with no vendored OCA code.
- No module imports the SaaS codebase.
- Every external entity has a store-scoped durable mapping.
- Every API-bound operation is a queue job.
- No record can cross company boundaries through UI, ORM, jobs, or mappings.
- Financial and shipment writes pass adopt-before-retry tests.
- Removing the connector leaves core installed and functional.
