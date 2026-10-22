# Complete Field Mapping Contract

| Resource | Supported fields | Direction | Notes |
|---|---|---|---|
| Product | id, sku, name, type, price, status, visibility, weight, category links, media entries | Both | Bundle/grouped/downloadable excluded |
| Variant | child SKU, attributes, price, configurable parent, variant primary/gallery media | Both | Parent/child identity preserved; child media uses `image_variant_1920` and variant-owned `product.image` |
| Category | id, name, parent, level, path, external name | Both | Odoo `product.public.category` |
| Customer | Magento customer ID, email, website, name, partner mapping | Import | Registered and guest policies |
| Address | billing/shipping name, street, city, region, postcode, country, phone | Import | Child contacts |
| Order | entity ID, increment ID, store, customer, status, currency, totals, lines | Import | Order number preserved |
| Order line | item ID, child item ID, SKU, qty, price, discount, tax | Import | Configurable/kit identity |
| Invoice | increment ID, lines, totals, posted state | Import | Idempotent mapping |
| Payment | invoice evidence, method, amount, journal, reference | Import | Adoption/residual caps |
| Credit memo | increment ID, lines, tax, shipping, total | Import | Credit-note mapping |
| Shipment | order, items, quantities, tracking | Export | One Magento shipment per picking |
| Inventory | SKU, source, absolute quantity, salability | Export | MSI source |
| Image | primary/gallery bytes, label, MIME, template or variant owner | Both | Max 10 MB, SHA-256 idempotency; Magento may re-encode the container |

Unsupported custom attributes, bundle/grouped/downloadable, RMA, and Magento
special-price rules are explicitly outside the contract.
