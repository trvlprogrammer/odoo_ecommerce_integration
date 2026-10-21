# 13 — Execution Checkpoints

## Current checkpoint

| Field | Value |
| --- | --- |
| Date | 2026-10-20 |
| Phase | V1 remediation, real Magento E2E acceptance, and version ports |
| Current branch | `18.0` |
| Application code | Both allowed repositories, branches `19.0`, `18.0`, `17.0` |
| Protected repositories | Unchanged (verified clean) |
| Release status | **READY FOR RELEASE** |
| Next safe action | Human review, then version tags and push with separate authorization |

## Verified environment

| Item | Value |
| --- | --- |
| Odoo 19 | `20f5882e87e818e94a79ad07ac00530842d7045b`, Python 3.12 |
| Odoo 18 | `8e50ecb100695e2d4c98bf3bd88463f2cfb53cad` |
| Odoo 17 | `02d3a1d847bb4c3f784e3b018b581ee4d8f3fe4e` |
| OCA queue 19 | `19.0.2.1.6` |
| OCA queue 18 | `18.0.4.1.1` |
| OCA queue 17 | `17.0.1.5.4` |
| PostgreSQL | `postgres:16` on loopback |
| Magento | Open Source `2.4.7-p3`, PHP 8.3, MySQL 8.0, OpenSearch 2.12, nginx |
| Magento API | `http://127.0.0.1:8083`, local disposable admin token |
| Magento MSI | Installed from public `magento/inventory` `1.2.7-p3` source |
| Test databases | `e2e_final_19`, `port18_test`, `port17_test`, `e2e_accept_19`, `e2e_uninstall_19` |

## Commits

| Branch | Integration core | Magento connector |
| --- | --- | --- |
| `19.0` | `eb7bc86` + `614528f` + `28843a9` | `d1e52a8` + `614528f` + `3f64a0c` |
| `18.0` | `f0278b9` + `397128d` | `ac13e8d` + `5f26873` + `1552472` |
| `17.0` | `1ae35d5` + `997eb61` | `dc9a51f` + `fe4a28d` |

All commits are local. Nothing was pushed, tagged, or deployed.

## Automated test results

| Version | Command summary | Result |
| --- | --- | --- |
| Odoo 19 | clean install + `/odoo_ecommerce_integration,/odoo_ecommerce_magento` | **41 tests, 0 failed, 0 errors** |
| Odoo 18 | clean install, isolated addons path | **40 tests, 0 failed, 0 errors** |
| Odoo 17 | clean install, isolated addons path | **40 tests, 0 failed, 0 errors** |

Odoo 18/17 tests used isolated addons paths so that protected repositories on
`19.0` were never loaded or modified.

## Real Magento E2E — Odoo 19

All operations were executed through the real OCA `queue_job` runner with
`--load=web,queue_job --workers=2`.

| Scenario | Result |
| --- | --- |
| Connection, store views, MSI sources | PASS |
| Category import (Default, Apparel, Tops, Shoes) and hierarchy | PASS |
| Simple product import/replay | PASS |
| Configurable parent + Red/Blue child variants + attribute/value mappings | PASS |
| Order `000000002` import: 2 simple + 1 configurable, 10% tax, 15 shipping | PASS (total 53.50 matched) |
| Order `000000003` kit parent import | PASS (76.00 matched) |
| Order `000000004` 10% coupon discount | PASS (49.65 matched, discount 3.50) |
| Order `000000005` repeat guest (same email/name/address) | PASS (same Odoo partner reused) |
| Canceled Magento order `000000001` | PASS (skipped intentionally) |
| Invoice/posting and exact payment amounts (53.50/76.00/49.65/16.00) | PASS |
| Partial credit memo `26.00` (item + shipping, tax preserved) | PASS |
| Full credit memo `16.00` | PASS |
| Credit notes linked to invoice, not auto-reconciled | PASS |
| No duplicate payments on finance replay | PASS |
| Partial delivery, backorder, second delivery | PASS |
| Adopt existing Magento shipments 1 and 2 (no duplicates) | PASS |
| Create Magento shipments for orders 4/5/6 with tracking | PASS |
| Kit shipment conversion (2×A + 1×B → 1 kit item) | PASS |
| Periodic stock cron → bounded queue jobs → absolute quantities | PASS |
| Event-driven stock change → targeted job → Magento quantity 42 | PASS |
| Category export with parent/child hierarchy | PASS |
| Simple product export + update + repeat (price 19.50) | PASS |
| Configurable product export `ODOO-EXP-CONF6` (parent, 2 children, options) | PASS |
| Configurable export repeat (no duplicates) | PASS |
| Second store view order sync (0 cross-store imports) | PASS |
| Unreachable backend job retry (`pending`, ETA) | PASS |
| Invalid backend URL permanent failure (`failed`) | PASS |
| Integration user used as job user | PASS |
| Module uninstall removes only connector queue jobs (1 → 0) | PASS |
| Protected repositories unchanged | PASS |

## Real Magento E2E — Odoo 18

| Scenario | Result |
| --- | --- |
| Catalog import through real API | PASS (10 product mappings, 6 category mappings) |
| Order import (`000000002`, `3`, `4`, `6`, `7`) | PASS (all financial checks matched) |
| Finance: invoices, exact payments, credit note 26.00 linked/open | PASS |
| Shipment create for order `000000007` with tracking | PASS |
| Event stock push (31 absolute) | PASS |
| Job user `ecommerce_integration` | PASS |

## Real Magento E2E — Odoo 17

| Scenario | Result |
| --- | --- |
| Catalog import through real API | PASS |
| Order import (`000000002`, `3`, `4`, `6`, `7`) | PASS (all financial checks matched) |
| Finance: invoices, exact payments, credit note 26.00 linked/open | PASS (Odoo 17 payment state `posted`) |
| Shipment adoption (Magento shipment 7, no duplicate) | PASS |
| Event stock push (27 absolute) | PASS |

## Defects fixed

- Cross-store order discovery now places all filters in one Magento filter group
  (AND) and revalidates the returned `store_id`.
- Payment amount is capped at invoice residual; overpayment records an issue.
- Existing `account.payment` is adopted by deterministic reference.
- `auto_register_payment` is honored; paid invoices become `skipped` mappings.
- `auto_confirm_orders` is honored by finance sync.
- Credit memos import independently of paid invoices; credit notes are linked
  to the invoice but not auto-reconciled; refund cash is opt-in.
- Integer Magento invoice state `2` is treated as paid.
- Configurable order child lines are skipped; kit component moves convert back
  to the kit order item.
- Currency mismatch and missing currency now stop the import.
- Order number collisions stop the import with an actionable error; the
  Magento `increment_id` is used from creation.
- SKU ambiguity stops product import instead of creating a duplicate.
- SSRF: DNS resolution, private/loopback/link-local/metadata rejection, no
  redirects, TLS verification. `allow_private_network` is an explicit
  development switch.
- `job_user_id` is used for every queued job; crons enqueue only and never call
  Magento directly.
- Cron records use a dedicated integration user.
- Module uninstall removes connector queue jobs.
- Configurable product import creates parent attributes, values, variants, and
  child mappings; export creates a Magento configurable parent, children,
  options, and category links.
- Product categories use `product.public.category` with hierarchy and
  per-store mapping.
- Guest deduplication uses normalized email + website scope, with last
  name/phone/postcode disambiguation and an advisory transaction lock.
- Shipments use exact `sale_line_id` identity, cap quantities against ordered
  quantities, never reuse a remote shipment twice, and send tracking.
- Periodic stock sync enqueues bounded batches; event sync enqueues targeted
  product jobs; both push absolute stock, including phantom-kit availability.
- Initial stock push now happens for zero-quantity mappings
  (`last_pushed_quantity` default `-1`).


## Repository restructuring (2026-10-20)

Both repositories now use the repository-container layout:

```text
odoo_ecommerce_integration/
  odoo_ecommerce_integration/   # Odoo addon
odoo_ecommerce_magento/
  odoo_ecommerce_magento/       # Odoo addon
```

- `docs/`, `README.md`, `LICENSE`, `.gitignore`, `tools/`, and Odoo Apps
  description assets remain at repository level.
- Technical module names are unchanged; imports, manifests, XML/CSV paths,
  security, views, data, tests, hooks, and queue_job integration are unchanged.
- `addons_path` must contain each repository root. Local development symlinks
  under `/home/ridho/Data/odoo-dev/{19,18,17}` were retargeted to the nested
  addon directories; queue_job symlinks were not changed.
- `LICENSE` files and `static/description/index.html` assets were added for
  Odoo Apps distribution.
- `requests` is declared as an external Python dependency of the connector.
- Clean nested-layout installations passed:
  - `restruct19`: **41 tests, 0 failed, 0 errors**
  - `restruct18`: **40 tests, 0 failed, 0 errors**
  - `restruct17`: **40 tests, 0 failed, 0 errors**
- Live Magento configurable export after restructuring:
  - Odoo 18: parent `RESTRUCT-18-CONF`, 2 simple children at 88.00, two option
    values, repeat export produced 3 products total.
  - Odoo 17: parent `RESTRUCT-17-CONF`, 2 simple children at 99.00, two option
    values, repeat export produced 3 products total.
- Queue_job dependency, discovery, runner, retry classification/limit, job user,
  deduplication, uninstall cleanup, and stock jobs were unaffected.
- Protected repositories remained clean.


## Odoo Apps listing preparation (2026-10-20)

- Magento Connector manifest: `price: 280.0`, `currency: USD`, license OPL-1.
- Free core: no price, license LGPL-3.
- Both addons received `static/description/icon.png`, `banner.png`,
  screenshots, and an embedded customer-facing listing page.
- Magento listing contains the complete 16-step customer setup guide,
  dependency installation, multi-store configuration, financial and inventory
  workflows, queue monitoring, troubleshooting, and known limitations.
- Free core listing explains that it is a framework dependency and does not
  connect to Magento or Shopify by itself.
- Four genuine GIF demonstrations were captured from a running Odoo 19
  environment with synthetic data: product import, order import, configurable
  product, and delivery workflow.
- Screenshots use real Odoo views and synthetic data. Credentials are masked.
  Screenshots from Odoo 19 are reused on 18/17 where the UI and features are
  equivalent.
- Local render validation at 1440px and 390px produced no broken image or
  network requests. GIFs were verified by direct playback and frame extraction.
- User guides were added under each repository's `docs/user_guide/`.
- Mapping menus were added for categories, inventory sources, payment methods,
  carriers, and financial/shipment/refund monitoring.
- Regression after listing/menu changes:
  - Odoo 19: 41 tests, 0 failed, 0 errors.
  - Odoo 18: 40 tests, 0 failed, 0 errors.
  - Odoo 17: 40 tests, 0 failed, 0 errors.
- No push, tag, deployment, or Odoo Apps publication was performed.
- Protected repositories remain unchanged.

## UX and manual E2E remediation (2026-10-20)

- Magento Admin root cause: nginx served `/static/version.../` without stripping
  the deployed-version prefix, so `static.php` rejected every asset. Local nginx
  now rewrites the version prefix and falls back to `static.php?resource=` with
  the `/static/` prefix removed. Static content was deployed for adminhtml and
  frontend. Admin CSS/JS, category/product pages, order pages, credit memos,
  and shipments render with no failed asset requests or page errors.
- Backend `Last Test At` and `Last Test Error` are model-readonly and populated
  by the connection workflow; success clears stale errors.
- Free core now owns a provider-neutral **Sync to eCommerce** transient wizard:
  provider registry, backend/store selection, Export vs Update, mapping status,
  company/store validation, and queue_job orchestration. Magento implements the
  provider hook; no Magento import exists in the free core.
- Export refuses an already-mapped product; Update refuses a missing mapping.
  Multi-store selection is supported; batches are bounded at 50 products and
  duplicate identity keys are deduplicated by queue_job.
- Navigation is provider-neutral: Configuration (Backends, Stores, Inventory
  Sources, Payment Methods, Delivery Carriers), Mappings (Products, Variants,
  Customers, Orders, eCommerce Categories, Payment Transactions, Invoices,
  Refunds, Shipments), Monitoring (Issues, Queue Jobs, History, States).
- Category mappings expose external name, identity, parent, Odoo eCommerce
  category, sync state, and last sync; import/export preserve `external_name`.
- Manual Magento Admin UI E2E passed: created `UI-CATALOG-2` and `UI Category`
  through Admin, imported both into Odoo through queue_job, opened orders,
  credit memos, and shipments without Admin errors. Created
  `UI-ODOO-EXPORT-1` in Odoo, exported it through the wizard, updated it through
  Update, and verified one Magento product with the updated price.
- Regression: Odoo 19 47 tests, Odoo 18 46 tests, Odoo 17 46 tests; all pass.
- Listing screenshots were replaced for the generic wizard, configurable
  product, stock, and category views; `Export to Magento` references removed.
- No push, tag, deployment, or publication was performed. Protected
  repositories remain unchanged.


## Core architecture consolidation (2026-10-21)

- Audit: `docs/16_ARCHITECTURE_OWNERSHIP_AUDIT.md`. Generic mapping tables were
  already core-owned; no populated mapping table was moved or recreated.
- Core provider contract now publishes capability codes, provider definitions,
  store support checks, and capability flags. Magento registers product,
  category, customer, order, inventory, shipment, finance, and preflight
  capabilities.
- Core owns the generic queue enqueue helper and a provider-neutral Store Sync
  wizard. Magento maps the generic hook to its existing queued methods and adds
  a bounded mapped-product update job.
- Store UI now has Test / Preflight, Sync Now, and View Jobs; tabs are General,
  Catalog, Orders & Finance, Inventory & Fulfillment, Scheduling, Diagnostics.
  Legacy Magento buttons remain under Diagnostics.
- `mrp` moved from the core manifest to the Magento manifest.
- Existing DB copy `arch_upgrade_19` upgraded with 30/30 baseline values
  unchanged (mapping counts and identity hashes, sale orders, invoices, credit
  notes, payments, pickings, queue jobs, cron, mappings).
- Test-only fake provider proves discovery, capability filtering, generic
  enqueue, mapping resolution, and unsupported-operation rejection.
- Odoo 19: 57 tests passed. Odoo 18: 56 passed. Odoo 17: 56 passed.
- Core installs without Magento and without `mrp` on all three versions.
- Real Magento smoke: queued connection test, product export, product update,
  category import, customer/order import path, inventory export, shipment
  export, finance import, and Store Sync inventory export all reached `done`.
  Magento product `ARCH-ODOO-SMOKE-1` updated from 12.34 to 19.87.
- Listing now uses the compact Store form and Store Sync wizard screenshots.
- No push, tag, deployment, or publication performed.


## Multi-company hardening, scalable queues and Dashboard (2026-10-21)

- Added server-side Operator checks for backend tests, preflight, Store Sync,
  product Sync, legacy export, and both wizards.
- Queue jobs are created with the Store company and allowed-company context;
  stock hooks and scheduling filter by company.
- Mapping targets are company-validated; Store/Backend company reassignment is
  blocked after dependent records exist; SKU lookup is company-aware.
- Added run/batch progress models and bounded coordinator/child jobs for product
  import/export/update, categories, customers, orders, finance, shipments,
  inventory, and stock events. Batch sizes are Store fields with validation.
- Added one provider-neutral core scheduler and retired fixed Magento cron
  intervals through migration.
- Added the core eCommerce Dashboard with company/provider/backend/Store/date
  filters, KPI cards, coverage charts, queue/activity charts, drill-down,
  recent runs, failed jobs, issues, and Store health.
- Odoo 18/17 now use partial active unique indexes with safe migration; 19 uses
  native partial constraints.
- Tests: 19.0 66 passed; 18.0 66 passed; 17.0 66 passed. Core-only installs pass
  on all three. Existing DB copies preserve mapping counts/hashes; only the new
  scheduler adds one cron record.
- Real Magento 19 smoke passed for connection, catalog/category/order/finance/
  inventory/product update through the real jobrunner.
- Odoo 18/17 Dashboard browser rendering remains to be verified.

## Known limitations

- Newly created Magento attributes can require one queue retry (60 s) before
  Magento's attribute metadata/cache accepts configurable child links. The
  connector handles this with `RetryableJobError` and recreates stale children.
- Magento configurable parent price is `0` by Magento convention; child prices
  carry the value (children are verified at the configured price).
- Partial kit availability is defined as complete kits only (minimum component
  availability). Partial-component shipping is documented, not auto-converted.
- Refund cash payments are only registered when `auto_register_refund` is on;
  otherwise the credit note remains open and linked for manual refund.
- Multi-source MSI routing, RMA, webhooks, product images, bundle/grouped
  products, and post-import Magento order edits remain out of V1 scope.
- Performance/throughput and 10k-product benchmarks were not executed.
- Odoo 18/17 live configurable export was verified after the restructure
  (`RESTRUCT-18-CONF`, `RESTRUCT-17-CONF`) including options, children, prices,
  category links, repeat export, and no duplicate products.

## Evidence locations

- Odoo 19 final tests: `/home/ridho/Data/magento-e2e/logs/final19b.log`
- Odoo 19 acceptance install: `/home/ridho/Data/magento-e2e/logs/accept_install.log`
- Odoo 18 tests: `/home/ridho/Data/magento-e2e/logs/port18e.log`
- Odoo 17 tests: `/home/ridho/Data/magento-e2e/logs/port17d.log`
- Real Magento stack and scripts: `/home/ridho/Data/magento-e2e/`
- Magento API scripts: `/home/ridho/Data/magento-e2e/scripts/`

## Next safe action

1. Human review of the local commits and limitations.
2. Optional live configurable-export run on Odoo 18 and 17.
3. Only after review, create version tags and push with separate authorization.
