# Product Import, Export and Media

## Fields verified on Odoo 19

Import: Magento entity ID, SKU, name, type, price, status, visibility, weight,
website/store scope, category links, configurable parent/child, simple/virtual
type, primary and gallery image bytes.

Export: SKU, name, price, status, visibility, type (`simple`/`virtual`),
attribute set, weight, category links, primary image, gallery images, configurable
parent/children and options.

Not implemented: bundle, grouped, downloadable, all Magento custom attributes,
Magento special-price rules, product-video media.

## Image E2E

Magento `E2E-IMAGE-1` with primary + gallery images:
- import produced Odoo template image and product.image gallery records
- no duplicate images on reimport
- image bytes verified by SHA-256.

Odoo `E2E-IMAGE-ODOO-1` with primary + gallery:
- Magento media entries 4 and 5 created
- repeated export kept media count at 2
- Magento media content decoded to the same SHA-256 as the Odoo image.

## Virtual/service

Magento virtual product 10873 → Odoo product template type `service`.
Odoo service product `E2E-SERVICE-EXPORT-1` → Magento `type_id=virtual`.

## Regression tests

Image import/export contract test added; suite now 77 tests.
