# 06 — Magento API Adapter

## 1. Scope

The adapter is the only place that knows Magento REST URLs, authentication,
payloads, pagination, and Magento error shapes. Core code must not import it.

Target:

- Magento Open Source `2.4.7-p3` (pinned reference)
- REST Admin API, PaaS-style path: `/rest/<store_code>/V1/...`
- Integration access token (Bearer) for V1
- Store view code as the REST scope; website ID for MSI/customer scope

OAuth 1.0a, Adobe Commerce as a Cloud Service/IMS, GraphQL storefront, and custom
Magento modules are out of V1.

## 2. Connection configuration

Stored on `ecommerce.backend` (core) plus Magento extension fields:

| Field | Example | Rule |
| --- | --- | --- |
| `base_url` | `https://magento.example.com` | normalized, no trailing slash |
| `access_token` | `<redacted>` | manager-only, never logged |
| `store_scope_code` | `all` or a store view code | backend admin scope is `all` by default |
| `verify_ssl` | `True` | production must be true |
| `timeout_seconds` | `30` | 5–120 |
| `allow_insecure_http` | `False` | only for loopback development |

The store's `external_store_view_code` is used for catalog/order/customer REST
calls. The backend's `all` scope is used only for installation-level probes and
administrative discovery.

## 3. Authentication

V1 uses an Integration access token:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

The token must come from a least-privilege Magento Integration with only the
resources needed for V1. Admin username/password tokens are for isolated local
bootstrap only; they are not stored in the connector. 2FA/admin token behavior
is a local-environment concern, not a product feature.

Authentication failures map to `MagentoAuthenticationError`; the connector does
not retry a clearly rejected token indefinitely. It revalidates once, then
raises a permanent/auth issue.

## 4. URL and transport safety

`normalize_base_url` must:

1. Require `https` unless `allow_insecure_http` and the host is loopback.
2. Reject userinfo, query strings, fragments, and non-HTTP schemes.
3. Reject whitespace/control characters and malformed ports.
4. Remove a trailing slash and collapse duplicate path separators.
5. Reject `169.254.169.254` and known metadata endpoints.
6. Allow private/on-prem hosts only because the configuration is manager-only;
   the threat model is a malicious administrator/compromised account, not an
   anonymous web input.

Transport rules:

- `verify_ssl = True` in production; do not ship a “disable SSL” convenience.
- Do not follow redirects automatically. A redirect is an error unless it stays
  on the same scheme/host and is explicitly handled.
- Bounded read: reject responses over 10 MiB.
- Connect timeout 10s, read timeout `timeout_seconds`.
- No credentials in URLs, query strings, logs, exceptions, or event metadata.
- Strip `Authorization`, cookies, request bodies, and customer fields from any
  retained error text.

## 5. Pagination and incremental reads

Magento `searchCriteria` conventions:

```
searchCriteria[pageSize]=100
searchCriteria[currentPage]=1
searchCriteria[sortOrders][0][field]=entity_id
searchCriteria[sortOrders][0][direction]=ASC
```

Rules:

- Products/catalog: page size 100, sorted by `entity_id`.
- Orders: page size 50–100, sorted by `entity_id`, incremental by
  `entity_id > cursor`.
- Customers: page size 50–100, website-filtered; store scope must not leak
  another website's customers.
- Invoices/shipments/credit memos: search by `order_id`.
- A page loop is owned by the connector service job, not the HTTP client.
- Stop on `has_next_page == False` or `currentPage * pageSize >= total_count`.
- Never advance the persisted cursor until the page/batch commits successfully.
- Use an overlap window for `updated_at`-based reconciliation; use `entity_id`
  cursor for append-only order discovery.
- Guard against a Magento `total_count` that changes during a long scan.

## 6. DTO boundary

Connector DTOs (dataclasses or lightweight objects) isolate ORM code from raw
Magento shapes:

| DTO | Required fields |
| --- | --- |
| `MagentoWebsite` | `id`, `code`, `default_store_view_code` |
| `MagentoStoreView` | `id`, `code`, `website_id`, `name` |
| `MagentoProductRef` | `entity_id`, `sku`, `type_id`, `parent_id`, `name`, `price`, `status`, `visibility`, `updated_at` |
| `MagentoConfigurableChild` | parent SKU, child SKU, option attributes/values |
| `MagentoCustomerRef` | `entity_id`, `website_id`, `email_present`, `name_present` (no PII in logs) |
| `MagentoOrderRef` | `entity_id`, `increment_id`, `state`, `status`, `store_id`, `customer_id`, `is_guest`, currency, totals, addresses, items |
| `MagentoOrderItemRef` | `item_id`, `product_id`, `parent_item_id`, `child_item_id`, `sku`, `qty_ordered`, `qty_shipped`, `price`, `discount_amount`, `tax_amount`, `name`, `product_type` |
| `MagentoInvoiceRef` | `entity_id`, `increment_id`, `state`, totals, currency, items |
| `MagentoPaymentEvidence` | method code, amount paid, currency, safe reference |
| `MagentoShipmentRef` | `entity_id`, `order_id`, `increment_id`, items (`order_item_id`, qty), tracks |
| `MagentoCreditMemoRef` | `entity_id`, `increment_id`, amount, currency, items |
| `MagentoInventorySource` | `source_code`, `name`, `enabled` |
| `MagentoShipmentWrite` | `order_item_id`, `qty`; optional tracks |

DTOs must be immutable or treated as read-only. No DTO contains an access token.

## 7. Endpoint catalogue

Exact paths must be checked against the installed Magento 2.4.7-p3 instance
before each connector milestone. This table is the implementation contract.

### 7.1 Connection / scope

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/V1/store/websites` | websites |
| GET | `/V1/store/storeViews` | store views |
| GET | `/V1/store/storeConfigs` | store view config/locale/currency |
| GET | `/V1/inventory/sources` | MSI sources/capability probe |
| GET | `/V1/inventory/stocks` | stocks/websites probe |
| POST | `/V1/integration/admin/token` | local dev bootstrap only |

`test_connection` records `msi_available`, `rma_available` (expected false on
Open Source), and `webhooks_available` without writing commerce data.

### 7.2 Catalog

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/V1/products` | paged product discovery |
| GET | `/V1/products/{sku}` | product read |
| POST | `/V1/products` | create simple product |
| PUT | `/V1/products/{sku}` | update owned fields |
| GET | `/V1/products/attributes` | attributes |
| POST | `/V1/products/attributes` | create select attribute |
| GET | `/V1/products/attributes/{code}/options` | attribute options |
| POST | `/V1/products/attributes/{code}/options` | create option |
| POST | `/V1/configurable-products/{parentSku}/options` | add configurable option |
| POST | `/V1/configurable-products/{parentSku}/children` | link child |
| GET | `/V1/configurable-products/{parentSku}/children` | read children |
| GET | `/V1/configurable-products/{parentSku}` | parent structure |

V1 supports simple and configurable products. Before writing a product, inspect
its type. Bundle/grouped/virtual/downloadable are rejected with a clear issue.

### 7.3 Customers

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/V1/customers/search` | paged, website-filtered discovery |
| GET | `/V1/customers/{id}` | customer detail |
| POST | `/V1/customers` | optional V1 create in Magento (only if explicitly enabled) |

Customer create in Magento is not required for order import. The V1 reference
creates/uses Odoo partners from Magento orders; it does not push every Odoo
partner to Magento. Do not add an unrequested customer export path.

### 7.4 Orders and financial documents

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/V1/orders` | order discovery |
| GET | `/V1/orders/{id}` | order detail |
| GET | `/V1/invoices?searchCriteria...` | invoices for order |
| GET | `/V1/creditmemo?searchCriteria...` | credit memos for order |
| GET | `/V1/shipments?searchCriteria...` | shipments for order |
| POST | `/V1/order/{orderId}/ship` | create shipment |
| POST | `/V1/order/{orderId}/invoice` | out of V1 unless explicitly approved |
| POST | `/V1/order/{orderId}/refund` | out of V1 |

V1 does not create Magento invoices or refunds. Odoo invoices and credit notes
are the accounting documents; Magento invoice/credit memo payloads are read as
external evidence.

### 7.5 Inventory

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/V1/inventory/sources` | source discovery |
| GET | `/V1/inventory/stocks` | stock/website mapping |
| POST | `/V1/inventory/source-items` | absolute SourceItem quantity write |

Only `source-items` is a V1 write target. Do not write aggregated `StockItem`
salable quantities; Magento reservations and MSI aggregation are Magento-owned.

## 8. Domain behavior

### 8.1 Connection test

1. Authenticate with the configured token.
2. Read websites/store views.
3. Read MSI sources; record capability.
4. Verify the selected store view belongs to the selected website.
5. Verify required scope fields are present.
6. Persist state/error and emit an event.

No commerce writes. A missing MSI capability blocks inventory features but does
not necessarily block order import; the store preflight reports exact blockers.

### 8.2 Catalog import

- Page products; select simple/configurable.
- Store parent/child identities and SKU.
- Map/reconcile attributes and values.
- Resolve Odoo templates/variants by existing mapping, then unique SKU.
- Never guess a variant from a display label if option IDs conflict.
- Ambiguous SKU/attribute/value mapping → issue and skip that product.
- Unsupported product types → issue, no partial import.
- Price/status/visibility updates are explicit field-ownership operations.

### 8.3 Catalog export

- Export only Odoo products explicitly selected/eligible.
- Create/update simple and configurable products.
- Use SKU as the Magento upsert key but persist `entity_id` mapping.
- Configurable parent/child order: create children, create parent, add options,
  link children. A partial failure leaves a mapping/issue, never a duplicate.
- Product images, categories beyond minimal assignment, and unsupported types
  are out of V1.

### 8.4 Customer import

- Read customers scoped to the store's website.
- Map by external customer ID first; email matching is an explicit, audited
  action, not a fuzzy auto-merge.
- Odoo partner company follows the store company.
- Guest orders are handled by order import, not customer import.
- Do not import password hashes, tokens, or unnecessary PII.

### 8.5 Order import

- Fetch full order by `entity_id`.
- Reject unimportable states (e.g. canceled) with a skipped mapping/event.
- Require `increment_id` for the merchant-facing sale order name.
- Require every order line to resolve to a variant mapping.
- Preserve address lines, email, phone, and name only as needed for the Odoo
  partner/order.
- Convert Magento item discount amount to an Odoo line discount percentage using
  the line gross; preserve the resulting total.
- Add a shipping line from the net shipping amount using the configured shipping
  product; map the carrier by method code.
- Resolve currency; never invent an exchange rate.
- Compare Odoo total to Magento grand total. Exact match or configured rounding
  tolerance is acceptable; otherwise create a mismatch issue and do not
  auto-confirm.
- Create/adopt sale order by deterministic origin and mapping. Persist line maps.
- Confirm only if `auto_confirm_orders` and financial check is acceptable.

### 8.6 Financial sync

- Require imported order mapping and sale order.
- Read Magento invoices and payment evidence.
- Create/post one Odoo invoice per order mapping in V1.
- For each paid Magento invoice, create a deterministic evidence key.
- Resolve method code → journal mapping; missing mapping is an issue.
- Search Odoo payments by deterministic memo before creating.
- Validate currency, residual, and amount; ambiguous/overpaid → manual review.
- Register payment only when all checks pass.
- Read credit memos and create/post Odoo credit notes only against an existing
  Odoo invoice. RMA is unsupported.

### 8.7 Inventory push

- Require one active source mapping and a store warehouse.
- Compute per variant using on-hand/reserved/safety and phantom-kit rules.
- Skip services, non-stocked products, and unsupported kits with status.
- Send absolute quantity + status (`1` if >0 else `0`) to SourceItem.
- Skip unchanged targets; persist last pushed only after success.
- A 429/5xx is retryable; a permanent 4xx is an issue.

### 8.8 Shipment push

- Read completed outgoing deliveries for the imported sale order.
- Compute delivered quantities from done moves (not ordered quantities).
- Convert kits to the Magento parent item quantity.
- List existing Magento shipments; adopt only an exact item/quantity signature.
- Create shipment with optional tracks. No post-create tracking updates in V1.
- Persist mapping by Odoo picking. Partial deliveries create separate mappings.

## 9. Error taxonomy

| Adapter condition | Error | Job behavior |
| --- | --- | --- |
| DNS/connect/read timeout | `MagentoUnavailableError` | retry |
| HTTP 401/403 | `MagentoAuthenticationError` | revalidate once, then issue |
| HTTP 404 on expected entity | `MagentoNotFoundError` | business decision; often skip/issue |
| HTTP 409/422 | `MagentoValidationError` | permanent issue |
| HTTP 429 | `MagentoRateLimitError` | retry with `Retry-After` |
| HTTP 5xx | `MagentoServerError` | retry |
| Invalid JSON/schema | `MagentoProtocolError` | permanent issue |
| Unsupported product type | `MagentoUnsupportedError` | permanent issue |
| Ambiguous write outcome | `MagentoAmbiguousWriteError` | manual review, no retry |
| Local mapping/config missing | core business error | permanent issue |

Never expose Magento's raw exception body to users. Store a sanitized reason code
and a short message; retain a redacted diagnostic only if needed and only under
manager access.

## 10. Adoption fingerprints

| Write | Fingerprint |
| --- | --- |
| Shipment | order entity ID + sorted (`order_item_id`, qty) |
| Product create | store + SKU + type |
| Configurable child link | parent SKU + child SKU |
| Inventory SourceItem | SKU + source code (absolute, naturally idempotent) |
| Payment | store + evidence key + reference memo |
| Invoice | order mapping + document kind |
| Credit note | store + credit memo entity ID |

If an adopt query returns zero or more than one match, stop. Do not choose the
“closest” row.

## 11. Contract tests

- Unit test URL/path construction and escaping (SKU/store code).
- Test token redaction in every error path.
- Test 401, 403, 404, 409, 422, 429, 500, timeout, invalid JSON.
- Test page-size clamping and `has_next_page` logic with total-count changes.
- Test store-view isolation for orders/customers.
- Test SSRF/redirect/insecure-scheme rejection.
- Record sanitized fixtures from an isolated Magento instance; never commit
  production payloads.
- Live contract test only against the isolated `2.4.7-p3` stack.

## 12. Open adapter questions for M1/M3

1. Exact shipment and credit memo response shapes on `2.4.7-p3` (validate against
   the live OpenAPI/schema).
2. Whether every payment method exposes usable evidence on Open Source; retain
   manual review when not.
3. Exact incremental filter behavior for customers/products (`updated_at` vs
   `entity_id`); orders use `entity_id` in V1.
4. Rate-limit headers/limits on the target deployment; implement `Retry-After`
   generically.
5. Multi-website customer email uniqueness behavior; never assume global email
   uniqueness.
