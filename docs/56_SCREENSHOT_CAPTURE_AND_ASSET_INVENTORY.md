# Screenshot Capture and Asset Inventory

Date: 2026-10-22

## Capture method

Real Odoo UI captures were produced with Playwright Chromium against local Odoo
17, 18, and 19 instances. No mock interface, generated dashboard, stock image,
or browser developer tool is present. Populated disposable demo records were
used. Standard browser chrome is not included.

Capture viewport was 1600 px wide. The Dashboard was captured at 1600 x 1300;
other views at 1600 x 1000. PNG assets were not resized after capture.

## Magento connector assets

Common destination folder:
`odoo_ecommerce_magento/static/description/screenshots/`

| Asset | Odoo 19 source | Odoo 18 source | Odoo 17 source |
|---|---|---|---|
| dashboard.png | 19 | 18 | 17 |
| backend.png | 19 | 18 | 17 |
| store.png | 19 | 18 | 17 |
| product-mappings.png | 19 | 18 | 17 |
| configurable-product.png | 19 | 18 | 17 |
| variants.png | 19 | 18 | 17 |
| product-media.png | 19 | 19 verification capture | 19 verification capture |
| variant-image.png | 19 | 18 | 17 |
| categories.png | 19 | 18 | 17 |
| customers.png | 19 | 18 | 17 |
| order.png | 19 | 18 | 17 |
| delivery.png | 19 | 18 | 17 |
| kit-delivery.png | 19 | 18 partial-delivery capture | 17 partial-delivery capture |
| kit-bom.png | 19 | 18 | 17 |
| invoice.png | 19 | 18 | 17 |
| payment.png | 19 | 18 | 17 |
| credit-note.png | 19 | 18 | 17 |
| queue-job.png | 19 | 18 | 17 |
| issues.png | 19 | 18 | 17 |
| stock.png | 19 | 19 verification capture | 19 verification capture |
| multi-store.png | 19 | 18 | 17 |
| product-sync-wizard.png | 19 | 19 verification capture | 19 verification capture |
| store-sync-wizard.png | 19 | 18 | 17 |

The two Odoo 19 verification captures reused on 18/17 are identified in the
figcaptions as "Verification capture: Odoo 19". The 18/17 kit-delivery asset is
their own real partial-delivery capture, which contains the kit components.

## Core assets

Common destination folder:
`odoo_ecommerce_integration/static/description/screenshots/`

| Asset | Odoo 19 source | Odoo 18 source | Odoo 17 source |
|---|---|---|---|
| dashboard.png | 19 | 18 | 17 |
| backend.png | 19 | 18 | 17 |
| store.png | 19 | 18 | 17 |
| mappings.png | 19 | 18 | 17 |
| customers.png | 19 | 18 | 17 |
| orders.png | 19 | 18 | 17 |
| sync-state.png | 19 | 18 | 17 |
| queue.png | 19 | 18 | 17 |
| product-sync-wizard.png | 19 | 19 verification capture | 19 verification capture |
| store-sync-wizard.png | 19 | 18 | 17 |
| issues.png | 19 | 18 | 17 |
| security.png | 19 | 18 | 17 |

## Verification

- Every referenced image path exists on all six branches.
- Chromium reported zero broken images at 1280 px desktop and 390 px mobile.
- No horizontal overflow was detected.
- No screenshot contains a login page, browser error, developer tools, API
  token, password, database credential, or real customer personal data.
- Screenshots show the actual configured demo company, store, mappings,
  orders, pickings, accounting records, queue jobs, and resolved issues.

## Removed assets

The four legacy animated GIFs were removed from the Magento package because
the refreshed listing now uses current static screenshots and HTML workflow
sections. This also reduced package size and removed stale UI captures.
