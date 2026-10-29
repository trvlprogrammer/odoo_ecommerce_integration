# 04 — Data Models

## 1. Conventions

- Technical names use the `ecommerce.` prefix in core and `magento`-specific
  fields only in the connector.
- External IDs are `Char`, required when the external object has a durable ID,
  and preserved verbatim. Never cast a platform ID to an integer in core.
- Every mapping/state row carries `backend_id`, `store_id`, and a stored
  `company_id` related from the store.
- Mappings are archived (`active = False`), not hard-deleted, when history
  matters. Backend/store deletion is restricted while dependent rows exist.
- Odoo 19 uses `models.Constraint`; Odoo 17/18 use `_sql_constraints`. The
  logical constraints below are identical across versions.
- JSON fields are used only for non-critical metadata. Identity, state, money,
  and relationships are typed columns.
- Monetary fields use Odoo `Monetary` only where a currency is guaranteed;
  otherwise decimal storage is explicit and compared with Odoo rounding rules.

## 2. Abstract mixin

### `ecommerce.mapping.mixin` (abstract)

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `backend_id` | Many2one `ecommerce.backend` | yes | `ondelete="restrict"`, indexed |
| `store_id` | Many2one `ecommerce.store` | yes | `ondelete="restrict"`, indexed |
| `company_id` | Many2one `res.company` | yes | related `store_id.company_id`, stored, indexed, readonly |
| `external_id` | Char | yes | durable external identity, indexed; an intent row may temporarily use `local:<deterministic-key>` until the remote ID is known |
| `external_parent_id` | Char | no | parent identity where applicable |
| `external_code` | Char | no | SKU / method code / source code, indexed where used |
| `active` | Boolean | yes | default `True`; archive instead of delete |
| `sync_state` | Selection | yes | `pending`, `synced`, `failed`, `manual_review`, `disabled` |
| `last_synced_at` | Datetime | no | last successful synchronization |
| `last_error` | Char | no | sanitized code/message, never a payload or secret |
| `metadata` | Json | no | bounded non-identity metadata |

Common constraints:

- `store_id.backend_id = backend_id`
- `store_id.company_id = company_id`
- unique external identity per concrete model (below)
- `external_id` non-empty when the mapping is active

Common indexes:

- `(store_id, external_id)`
- `(company_id, active)`
- `(store_id, sync_state)`

## 3. Core models

### 3.1 `ecommerce.backend`

One external installation/credential set.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | Char | yes | human label |
| `code` | Char | yes | unique per company |
| `provider` | Char | yes | Installed provider code registered by a connector; the core supplies labels and capabilities |
| `company_id` | Many2one `res.company` | yes | default current company |
| `active` | Boolean | yes | archive to disable |
| `base_url` | Char | yes | normalized, no trailing slash |
| `allow_insecure_http` | Boolean | yes | default `False`; only loopback/dev |
| `verify_ssl` | Boolean | yes | default `True`; production must not disable |
| `timeout_seconds` | Integer | yes | default 30; bounded 5–120 |
| `job_user_id` | Many2one `res.users` | yes | dedicated integration user for scheduled jobs |
| `access_token` | Char (`password=True`) | yes | manager-only; never logged |
| `state` | Selection | yes | `draft`, `ready`, `error`, `disabled` |
| `last_test_at` | Datetime | no | last connection test |
| `last_test_error` | Char | no | sanitized |
| `capabilities` | Json | no | `msi_available`, `rma_available`, `webhooks_available` |
| `notes` | Text | no | no secrets/PII |

Constraints:

- unique `(company_id, code)`
- `provider` must be implemented by an installed adapter

Indexes:

- `(company_id, provider, active)`

Connector may add Magento columns by inheritance, e.g. `magento_version`,
`magento_edition`, but must not create a second connection table.

### 3.2 `ecommerce.store`

One commercial scope in an installation.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | Char | yes | label |
| `code` | Char | yes | unique per backend |
| `backend_id` | Many2one | yes | restrict |
| `company_id` | Many2one `res.company` | yes | must match backend |
| `active` | Boolean | yes | archive |
| `external_website_id` | Char | no | Magento website ID |
| `external_website_code` | Char | no | Magento website code |
| `external_store_view_id` | Char | no | Magento store view ID |
| `external_store_view_code` | Char | yes | REST path scope |
| `warehouse_id` | Many2one `stock.warehouse` | yes | company-owned |
| `stock_location_id` | Many2one `stock.location` | yes | child of warehouse stock location |
| `pricelist_id` | Many2one `product.pricelist` | no | company-owned |
| `currency_id` | Many2one `res.currency` | no | company-active |
| `auto_confirm_orders` | Boolean | yes | default `False` |
| `auto_post_invoice` | Boolean | yes | default `True` |
| `auto_register_payment` | Boolean | yes | default `False` in V1 |
| `inventory_use_on_hand` | Boolean | yes | default `True` |
| `inventory_subtract_reserved` | Boolean | yes | default `True` |
| `inventory_safety_stock` | Integer | yes | default `0`, min `0` |
| `order_sync_interval_minutes` | Integer | yes | default `5`, 1–1440 |
| `customer_sync_interval_minutes` | Integer | yes | default `30` |
| `catalog_sync_interval_minutes` | Integer | yes | default `60` |
| `inventory_sync_interval_minutes` | Integer | yes | default `15` |
| `shipment_sync_interval_minutes` | Integer | yes | default `15` |
| `last_preflight_at` | Datetime | no | |
| `last_preflight_error` | Char | no | sanitized |
| `can_preflight` | Boolean | computed | provider advertises `health.preflight` |
| `can_sync` | Boolean | computed | provider advertises any synchronization capability |
| `can_product_sync` | Boolean | computed | provider advertises `product.export` |

Constraints:

- unique `(backend_id, code)`
- partial unique `(backend_id, external_store_view_id)` when not null
- store company = backend company
- warehouse/location/currency/pricelist belong to store company

Indexes:

- `(company_id, active)`
- `(backend_id, external_store_view_code)`

### 3.3 `ecommerce.store.sync.wizard` (transient)

No persistent mapping data. Stores the selected `operation`, `data_type`,
`provider`, `backend_id`, `store_ids`, and a computed capability summary. Its
table is created or updated automatically and is safe to discard.

### 3.4 `ecommerce.product.mapping`

External parent product ↔ Odoo `product.template`.

Additional fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `odoo_template_id` | Many2one `product.template` | yes | restrict, indexed |
| `external_product_type` | Char | yes | `simple`, `configurable`, etc. |
| `mapping_method` | Selection | yes | `manual`, `sku_auto`, `export` |
| `external_sku` | Char | no | display/matching aid |
| `external_updated_at` | Datetime | no | remote catalog timestamp, when available |

Constraints:

- unique `(store_id, external_id)` while active
- unique `(store_id, odoo_template_id)` while active

### 3.5 `ecommerce.variant.mapping`

External sellable variant ↔ Odoo `product.product`. Operative grain for order
lines and inventory.

Additional fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `odoo_product_id` | Many2one `product.product` | yes | restrict, indexed |
| `product_mapping_id` | Many2one `ecommerce.product.mapping` | no | parent grouping |
| `external_sku` | Char | no | normalized matching aid |
| `external_barcode` | Char | no | optional |
| `mapping_method` | Selection | yes | manual/sku_auto/export |
| `last_pushed_quantity` | Integer | no | inventory idempotency; per source mapping |
| `last_pushed_at` | Datetime | no | |

Constraints:

- unique `(store_id, external_id)` while active
- unique `(store_id, odoo_product_id)` while active

Important: if several external variants map to one Odoo variant, order line
quantities cannot be attributed safely. The unique Odoo-side constraint prevents
this in V1.

### 3.6 `ecommerce.attribute.mapping`

Magento attribute code ↔ Odoo `product.attribute`.

Additional fields: `odoo_attribute_id` (required), `external_attribute_code`
(required), `external_attribute_type` (Char), `mapping_method`.

Constraint: unique `(store_id, external_attribute_code)` while active; unique
`(store_id, odoo_attribute_id)` while active.

### 3.7 `ecommerce.attribute.value.mapping`

Magento option value ↔ Odoo `product.attribute.value`.

Additional fields: `attribute_mapping_id` (required), `odoo_value_id` (required),
`external_option_id` (required), `external_label` (Char).

Constraint: unique `(attribute_mapping_id, external_option_id)` while active;
unique `(attribute_mapping_id, odoo_value_id)` while active.

### 3.8 `ecommerce.customer.mapping`

Magento customer ↔ Odoo `res.partner`.

Additional fields: `odoo_partner_id` (required), `external_customer_id`
(required), `external_website_id` (Char, required), `mapping_method`.

Constraint: unique `(store_id, external_customer_id)` while active. Website is
already part of the store scope; retain the external website for audit.

Guest orders have **no** customer mapping. A deterministic commercial partner is
reused by normalized email + store; the delivery/invoice address may be a child
partner. A guest order does not fabricate a Magento customer ID.

### 3.9 `ecommerce.order.mapping`

Magento order ↔ Odoo `sale.order`.

Additional fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `odoo_sale_order_id` | Many2one `sale.order` | no | restrict, indexed |
| `external_order_reference` | Char | no | increment ID, display |
| `external_state` | Char | no | Magento state |
| `external_status` | Char | no | merchant status |
| `external_customer_id` | Char | no | registered customer, if any |
| `is_guest` | Boolean | yes | default `False` |
| `odoo_partner_id` | Many2one `res.partner` | no | commercial |
| `odoo_invoice_partner_id` | Many2one `res.partner` | no | |
| `odoo_shipping_partner_id` | Many2one `res.partner` | no | |
| `currency_id` | Many2one `res.currency` | no | |
| `external_grand_total` | Monetary | no | |
| `odoo_amount_total` | Monetary | no | |
| `financial_check` | Selection | no | `unverified`, `matched`, `rounding`, `mismatch` |
| `import_status` | Selection | yes | `importing`, `imported`, `failed`, `skipped` |
| `confirmation_status` | Selection | yes | `not_requested`, `pending`, `confirmed`, `failed` |
| `create_attempted_at` | Datetime | no | uncertain-create adoption marker |
| `imported_at` | Datetime | no | |
| `last_error` | Char | no | sanitized code |

Constraints:

- unique `(store_id, external_id)`
- `external_id > 0` only if the adapter guarantees numeric IDs; core uses text
  and does not impose numeric semantics
- one Odoo sale order per mapping; do not reuse a sale order for two external
  orders

Indexes: `(store_id, import_status)`, `(store_id, external_order_reference)`,
`(company_id, imported_at)`.

### 3.10 `ecommerce.order.line.mapping`

Additional fields: `order_mapping_id` (required), `odoo_sale_order_line_id`
(required), `external_line_id` (required), `external_child_line_id` (no),
`external_product_id` (Char), `external_sku` (Char), `quantity` (Float),
`price_unit` (Monetary, currency related from the order mapping),
`discount_amount` (Monetary), `tax_amount` (Monetary).

Constraint: unique `(order_mapping_id, external_line_id)`.
Index: `(order_mapping_id, external_child_line_id)`.

### 3.11 `ecommerce.invoice.mapping`

Additional fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `order_mapping_id` | Many2one | yes | restrict |
| `odoo_move_id` | Many2one `account.move` | no | customer invoice |
| `external_increment_id` | Char | no | Magento increment ID for audit |
| `status` | Selection | yes | `pending`, `created`, `posted`, `failed`, `no_invoiceable_lines`, `manual_review` |
| `content_fingerprint` | Char | no | duplicate detection |
| `posted_at` | Datetime | no | |

`external_id` is the Magento invoice `entity_id`. If no Magento invoice exists,
use a deterministic local key such as `order:<order_mapping_id>:invoice`; do not
leave it blank.

Constraints:

- one active invoice mapping per order mapping in V1
- unique `(store_id, external_id)`

### 3.12 `ecommerce.payment.mapping`

Payment evidence ↔ Odoo `account.payment`.

Additional fields: `order_mapping_id` (required), `invoice_mapping_id` (no),
`odoo_payment_id` (no), `external_invoice_id` (no), `external_method_code` (no),
`amount` (Monetary), `currency_id` (no), `journal_id` (no), `payment_reference`
(Char), `status` (`pending`, `registered`, `manual_review`, `failed`, `skipped`).

`external_id` is the deterministic payment evidence key, e.g.
`magento_invoice:<entity_id>`. Never key a payment by amount + timestamp.

Constraints:

- unique `(store_id, external_id)`
- partial unique `(store_id, odoo_payment_id)` when not null

### 3.13 `ecommerce.shipment.mapping`

Odoo picking ↔ Magento shipment.

Additional fields: `order_mapping_id` (required), `odoo_picking_id` (required),
`tracking_number` (Char), `tracking_carrier` (Char), `content_fingerprint` (Char),
`status` (`pending`, `shipped`, `adopted`, `failed`, `skipped`).

`external_id` is the Magento shipment `entity_id` once known. The mapping is
created with a local pending identity based on the Odoo picking, then updated
after adoption/create.

Constraints:

- unique `(store_id, odoo_picking_id)`
- partial unique `(store_id, external_id)` when it is a remote identity

### 3.14 `ecommerce.refund.mapping`

Magento credit memo ↔ Odoo credit note.

Additional fields: `order_mapping_id` (required), `invoice_mapping_id` (no),
`odoo_credit_note_id` (no), `external_increment_id` (no), `amount` (Monetary),
`currency_id` (no), `content_fingerprint` (Char), `status` (`pending`,
`imported`, `posted`, `failed`, `manual_review`, `skipped`).

`external_id` is the Magento credit memo `entity_id`.

Constraints: unique `(store_id, external_id)`; unique
`(store_id, odoo_credit_note_id)` when not null.

Refund **payment** mapping is deferred in V1. If added later, it must be a
separate model because a credit memo and a gateway refund are different
economic events.

### 3.15 `ecommerce.inventory.source.mapping`

Additional fields: `warehouse_id` (required), `stock_location_id` (required),
`external_source_name` (Char), `active`.

`external_id` is the Magento `source_code`; `external_code` may mirror it for
generic filters.

Constraints: unique `(store_id, external_id)`; only one active source per store
in V1.

### 3.16 `ecommerce.carrier.mapping`

Additional fields: `delivery_carrier_id` (optional), `shipping_product_id`
(optional service product override), `external_label` (Char), `external_active`
(Boolean), `external_scope` (Char), `active`.

`external_id` is the stable Magento shipping method code. New mappings use the
Store default delivery carrier and its delivery product when configured. The
carrier delivery product is used when `shipping_product_id` is empty. The
obsolete Store-level shipping product is migrated into existing mappings.

Constraint: unique `(store_id, external_id)` while active.

### 3.17 `ecommerce.payment.method.mapping`

Additional fields: `journal_id` (`account.journal`, optional),
`external_label` (Char), `external_active` (Boolean), `external_scope` (Char),
`active`.

`external_id` is the stable Magento payment method code. New mappings use the
Store default payment journal when configured.

Constraint: unique `(store_id, external_id)` while active.

### 3.18 `ecommerce.sync.state`

Persistent cursor/watermark per store/resource/direction.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `backend_id` | Many2one | yes | restrict |
| `store_id` | Many2one | yes | restrict |
| `company_id` | Many2one | yes | related store |
| `resource` | Selection | yes | `product`, `customer`, `order`, `invoice`, `payment`, `inventory`, `shipment`, `refund`, `health` |
| `direction` | Selection | yes | `inbound`, `outbound` |
| `cursor_value` | Char | no | last committed external cursor/entity ID |
| `watermark` | Datetime | no | last committed source timestamp |
| `overlap_seconds` | Integer | yes | default 300 |
| `last_started_at` | Datetime | no | |
| `last_success_at` | Datetime | no | |
| `last_completed_at` | Datetime | no | includes failed runs |
| `status` | Selection | yes | `never`, `running`, `success`, `failed` |
| `last_error` | Char | no | sanitized |
| `metadata` | Json | no | counters/page info, bounded |

Constraint: unique `(store_id, resource, direction)`.

Cursor advances only after the batch/job succeeds. A failed page does not move
the cursor.

### 3.19 `ecommerce.sync.event`

Append-only operational history. Not an issue.

Fields: `backend_id`, `store_id`, `company_id`, `event_type` (Char/selection),
`severity`, `source`, `entity_model`, `entity_id`, `external_reference`, `title`,
`message`, `dedupe_key` (unique when not null), `details` (Json), `occurred_at`,
`created_by_id`.

Indexes: `(store_id, occurred_at)`, `(store_id, event_type, occurred_at)`,
unique `dedupe_key` when not null.

No secrets or raw API payloads. PII is minimized to an internal record link.

### 3.20 `ecommerce.sync.issue`

Actionable problem. Separate from events.

Fields: `backend_id`, `store_id`, `company_id`, `issue_type`, `severity`,
`status` (`open`, `resolved`, `ignored`), `entity_model`, `entity_id`,
`external_reference`, `title`, `summary`, `reason_code`, `fingerprint` (unique),
`occurrence_count`, `first_seen_at`, `last_seen_at`, `resolved_at`,
`resolution_note`, `last_event_id`, `details` (Json).

Fingerprint is deterministic, e.g.
`store:<id>|type:<issue_type>|entity:<model>:<id>|reason:<code>`.

### 3.21 `ecommerce.sync.run` and `ecommerce.sync.batch`

`ecommerce.sync.run` persists Store/provider/operation/resource, total, queued,
processed, succeeded, failed, skipped, state, timestamps, cursor, and last error.
`ecommerce.sync.batch` stores a unique `(run_id, key)` acknowledgement so queue
retries do not double-count progress. Both derive company from the Store and are
protected by company rules.

## 4. Ownership matrix

| Model | Owner | Connector may |
| --- | --- | --- |
| backend/store | core | inherit fields, add Magento config/validation |
| product/variant/attribute mappings | core | read/write through core rules |
| customer/order/order-line mappings | core | read/write |
| invoice/payment/shipment/refund mappings | core | read/write |
| inventory source/carrier/payment method | core | read/write |
| sync state/event/issue | core | read/write through services |
| Magento DTOs/client/error mapping | connector | owns |
| queue job function/channel data | connector (channels/functions) | owns Magento records |

## 5. Access rights

Groups:

- `group_ecommerce_user`: read-only backend/store (credentials hidden),
  mappings, states, events, issues.
- `group_ecommerce_operator`: user + create/write mappings, run manual sync,
  retry safe actions, resolve issues.
- `group_ecommerce_manager`: operator + backend/store configuration,
  credentials, schedules, destructive archival.
- `base.group_system`: emergency administration only; not a normal workflow.

ACL summary:

| Model | User | Operator | Manager |
| --- | --- | --- | --- |
| backend (non-secret fields) | read | read | CRUD |
| backend `access_token` | no | no | read/write |
| store | read | read | CRUD |
| all mappings | read | CRUD | CRUD |
| sync state/event/issue | read | create/write/resolve | CRUD |
| queue.job | own/related read | read | read/admin per OCA |

Record rules:

- global company rule on every `ecommerce.*` model:
  `[('company_id', 'in', company_ids)]`.
- backend/store rule additionally restricts to allowed companies.
- operators may act only on stores in their allowed companies.
- `ir.rule` is mandatory even if a field is readonly; UI hiding is not security.

Jobs run with `backend.job_user_id`, which must have the operator group and the
required sale/stock/account rights for the store companies. Do not run scheduled
jobs as the superuser.

## 6. External identity and uniqueness summary

| Entity | Durable key | Scope |
| --- | --- | --- |
| Magento order | `entity_id` | store |
| Order line | `item_id` | order mapping |
| Product parent | `entity_id` | store |
| Variant | `entity_id` | store |
| Attribute | `attribute_code` / ID | store |
| Attribute value | option ID | attribute mapping |
| Customer | `entity_id` + website | store |
| Invoice | `entity_id` | store |
| Payment evidence | invoice/evidence key | store |
| Shipment | `entity_id` | store |
| Credit memo | `entity_id` | store |
| Inventory source | `source_code` | store |
| Shipping method | method code | store |
| Payment method | method code | store |

## 7. Migration strategy

- No Alembic. Odoo module upgrades own schema changes.
- Add fields/tables in the module; Odoo updates `ir.model` and PostgreSQL.
- Use versioned upgrade scripts only for data backfills or renames:
  `migrations/19.0.1.1.0/pre-migrate.py`, etc.
- Never rewrite financial mappings silently. If an identity scheme changes,
  provide a dry-run migration and an issue/report for ambiguous rows.
- Core and connector versions move together within an Odoo major. A connector
  upgrade may require a minimum core version in its manifest/README.
- Test upgrade from the previous tag on a copy of the database; never on a
  production database.
