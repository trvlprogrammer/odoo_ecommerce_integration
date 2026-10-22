# Odoo Apps Packaging and Listing

Date: 2026-10-22

## Packages

| Package | Technical name | License | Price | Application |
|---|---|---|---|---|
| eCommerce Integration Core | `odoo_ecommerce_integration` | LGPL-3 | Free | No |
| Magento Connector for Odoo | `odoo_ecommerce_magento` | OPL-1 | USD 280 | Yes |

Versions remain `19.0.1.3.0`, `18.0.1.3.0`, and `17.0.1.3.0` on their
respective branches. The nested addon layout is unchanged:
the repository root is added to `addons_path`, not the nested addon folder.

## Core listing structure

1. Hero and provider-neutral positioning.
2. Live demo block.
3. Core capabilities and explicit "not a standalone connector" notice.
4. Provider architecture and workflow.
5. Dashboard screenshot.
6. Mapping and operational screenshots.
7. Ten-step setup and daily-use guide.
8. Installation order and dependency table.
9. Support contact and footer.

The Core listing does not advertise Magento-only workflows as Core features.
It states that a provider connector is required for external synchronization.
The README dependency list was corrected to remove Manufacturing (`mrp`);
Core does not depend on Magento or MRP.

## Magento listing structure

1. Hero and native Magento positioning.
2. USD 280 price block and tested Magento version.
3. Live demo block.
4. Benefits and feature overview.
5. Supported inbound/outbound directions.
6. "How it works" pipeline and five operational flows.
7. Real screenshots, including products, variants, media, orders, kits,
   deliveries, invoices, payments, credit notes, queue, and issues.
8. Magento API setup, Backend, Store View, product, customer, order,
   fulfillment, finance, refund, stock, monitoring, and troubleshooting guide.
9. Supported feature matrix, explicit limitations, support contact.

## Live demo

Published exactly as authorized:

- URL: https://odoo.odoointegrator.id
- Username: `demo`
- Password: `demo`

The descriptions describe it as a disposable read/write demo and do not
publish Magento API credentials, database credentials, or administrator
accounts.

## Support

Published email: <alfatihridhont@gmail.com> via `mailto:` link.
No response-time, 24/7, customization, or lifetime-support promise is made.

## Feature claims

Only implemented and verified behavior is claimed:

- Simple, configurable, virtual/service, category, attributes, prices,
  status/visibility, primary/gallery media, and variant media.
- Guest and registered customers, deduplication, addresses, and store scope.
- Order import with variant identity, totals, tax, shipping, duplicate
  prevention, and increment-ID preservation.
- Phantom kit fulfillment, partial shipment, backorder, and quantity-aware
  shipment export.
- Invoice, paid-invoice payment, reconciliation, credit notes, full/partial/
  late refunds, and optional auto refund.
- OCA queue_job processing, retries, restart recovery, multi-company, multiple
  Store Views, Dashboard, and issues.

## Explicit limitations

The listing states that RMA, physical return-to-stock, bundle/grouped/
downloadable products, arbitrary custom attributes, special-price rules,
multi-source MSI routing, webhooks, and post-import Magento order edits are
outside the released contract. It also states that not every resource is
bidirectional.

## Manifests

- Correct display name, summary, version, category, author, website, license,
  price/currency, application/installable flags, dependencies, and image lists.
- Core image list contains thirteen package screenshots.
- Magento image list contains seventeen package screenshots.
- All referenced image paths were verified on each branch.

## HTML validation

Rendered from `file://` in Chromium at 1280 px desktop and 390 px mobile:

| Check | Core | Magento |
|---|---|---|
| Parsed HTML | PASS | PASS |
| Missing local assets | 0 | 0 |
| Broken images | 0 | 0 |
| Horizontal overflow desktop | None | None |
| Horizontal overflow mobile | None | None |
| Unsupported JavaScript | None | None |
| Demo URL/credentials | PASS | PASS |
| Support mailto | PASS | PASS |
