# Architecture Ownership Audit (Odoo 19 baseline)

Date: 2026-10-20
Scope: `odoo_ecommerce_integration`, `odoo_ecommerce_magento`.
`odoo_ecommerce_shopify` inspected read-only and not modified.

## Baseline

- Core HEAD: `96481c0` (`19.0`)
- Magento HEAD: `49eefaa` (`19.0`)
- Core is a normal module; it has no dependency on Magento.
- Magento declares `depends = ["odoo_ecommerce_integration"]`.
- Existing test database `e2e_accept_19` baseline:
  - 4 backends, 2 stores
  - product mappings 16, variant mappings 20, category mappings 7,
    customer mappings 6, order mappings 8, invoice mappings 5,
    payment mappings 5, refund mappings 2, shipment mappings 5
  - 74 queue jobs, 8 Magento/eCommerce cron records

## Ownership Inventory

| Area | Current owner | Classification | Finding |
| --- | --- | --- | --- |
| `ecommerce.backend` | Core | CORE_GENERIC | Correct owner. Provider is a Char; capability contract is missing. |
| `ecommerce.store` | Core | CORE_GENERIC | Correct owner. Connector hooks are limited to product sync. |
| `ecommerce.mapping.mixin` | Core | CORE_GENERIC | Correct owner; provider/backend/store/company scope and constraints are generic. |
| Product mapping | Core | CORE_GENERIC | No move required. Populated core table. |
| Variant mapping | Core | CORE_GENERIC | No move required. |
| Attribute/value mappings | Core | CORE_GENERIC | No move required. |
| Category mapping | Core | CORE_GENERIC | Includes `external_name`; no move required. |
| Customer mapping / guest identity | Core | CORE_GENERIC | No move required. |
| Order and order-line mappings | Core | CORE_GENERIC | No move required. |
| Invoice mapping | Core | CORE_GENERIC | No move required. |
| Payment mapping | Core | CORE_GENERIC | No move required. |
| Refund mapping | Core | CORE_GENERIC | No move required. |
| Shipment mapping | Core | CORE_GENERIC | No move required. |
| Inventory-source mapping | Core | CORE_GENERIC | No move required. |
| Payment-method mapping | Core | CORE_GENERIC | No move required. |
| Carrier mapping | Core | CORE_GENERIC | No move required. |
| Sync state/event/issue | Core | CORE_GENERIC | Correct owner; monitoring is provider-neutral. |
| Product sync wizard | Core | CORE_GENERIC | Correct owner; uses connector enqueue hook. |
| Store-wide sync wizard | — | MIXED_REQUIRES_SPLIT | Missing. Must be core UI/validation, connector execution. |
| Provider registry | Core | SHARED_CONTRACT | Minimal code/label only. Needs capabilities. |
| `_ecommerce_supports_product_sync` | Core/Magento | SHARED_CONTRACT | Correct direction; generalize to capability checks. |
| `_ecommerce_enqueue_product_sync` | Core/Magento | SHARED_CONTRACT | Correct direction; Magento owns batching. |
| `_enqueue` queue helper | Magento store | CORE_GENERIC | Generic queue mechanics should live in core. |
| Store action methods (`action_sync_*`, etc.) | Magento | MAGENTO_SPECIFIC | Provider execution; keep in Magento. |
| Store action header (10 buttons) | Magento view | MAGENTO_SPECIFIC | UI ownership problem; replace with core primary actions and secondary legacy section. |
| Backend test connection | Magento | MAGENTO_SPECIFIC | Correct owner. |
| Product `action_export_to_magento` | Magento | MAGENTO_SPECIFIC | Correct owner; legacy compatibility kept. |
| Stock move/quant hooks | Magento | MAGENTO_SPECIFIC | Correct owner; they select Magento stores. |
| Magento client/errors | Magento | MAGENTO_SPECIFIC | Correct owner. |
| Magento sync service | Magento | MAGENTO_SPECIFIC | Correct owner; all payload/endpoint logic remains. |
| Queue channels | Magento data | MAGENTO_SPECIFIC | Keep to avoid migration risk; core provides generic enqueue helper. |
| Queue job function registration | Magento data | MAGENTO_SPECIFIC | Provider methods remain Magento-owned. |
| Magento cron records | Magento data | MAGENTO_SPECIFIC | Preserve; polling semantics are provider-specific. |
| Core menus/views/ACLs | Core | CORE_GENERIC | Correct; only expose real models. |
| Magento backend/store view extensions | Magento | MAGENTO_SPECIFIC | Extend core forms only with provider fields. |
| `mrp` dependency | Core manifest | MIXED_REQUIRES_SPLIT | Only Magento stock code uses MRP; move dependency from core to Magento. |
| `website_sale`, `delivery`, accounting dependencies | Core | CORE_GENERIC | Required by shared mapping targets. |

## Proposed Changes

1. Core provider capability contract:
   - Registry entries gain `capabilities`.
   - Core exposes provider selection, supported `(resource, operation)` pairs,
     and store-level capability booleans used by the UI.
   - Connector stores implement generic enqueue hook; Magento maps it to
     existing `action_*` queue methods.
2. Core Store Sync wizard:
   - New transient model/views/action/ACL.
   - Operations: Import, Export, Update (Update only for mapped products).
   - Data types: Products, Categories, Customers, Orders, Inventory,
     Shipments, Financial Documents.
   - Rejects unsupported combinations before queueing.
   - No synchronous provider API calls.
3. Core queue helper:
   - Move generic job-user/`with_delay` mechanics to `ecommerce.store`.
   - Magento keeps method names, channels, identities, batching, retry logic.
4. Store form:
   - Header: Test / Preflight, Sync Now, View Jobs.
   - Tabs: General, Catalog, Orders & Finance, Inventory & Fulfillment,
     Diagnostics.
   - Legacy Magento operations remain available under Diagnostics as secondary
     buttons; existing model methods and queue identities are unchanged.
5. Dependency cleanup:
   - Remove `mrp` from core manifest; add to Magento manifest.
   - No model or table movement.

## Database and Migration Impact

- Generic mapping tables already belong to core. No table rename, no raw SQL,
  no drop/recreate operation is required.
- New wizard is transient; PostgreSQL creates its transient table during module
  update. No populated table is rewritten.
- New store capability fields are computed non-stored; no schema change.
- Existing XML IDs and mapping constraints are preserved.
- `mrp` metadata change does not uninstall MRP from existing databases.
- Required verification: copy `e2e_accept_19`, upgrade core and Magento, then
  compare all mapping counts, external IDs, sale orders, invoices, payments,
  credit notes, shipments, queue jobs, cron records, menus, ACLs, and views.

## Test Coverage Plan

- Core-only install without Magento.
- Fake provider capability discovery and generic enqueue.
- Product wizard existing export/update behavior (Magento suite).
- Store wizard capability rejection and successful enqueue.
- Multi-company filtering.
- Existing database upgrade preservation.
- Odoo 19/18/17 suites.
- Targeted real Magento smoke: connection, category/product, order, finance,
  shipment, inventory, store wizard, queue runner.
