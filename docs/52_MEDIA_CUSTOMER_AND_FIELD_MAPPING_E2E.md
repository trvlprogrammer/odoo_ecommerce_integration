# Media, Customer, and Field Mapping E2E

## Product media

Previously verified real-Magento evidence:

- Magento `E2E-IMAGE-1`: primary and gallery imported into Odoo.
- Odoo `E2E-IMAGE-ODOO-1`: primary and gallery exported to Magento media IDs
  4 and 5. Repeating the export did not create additional media.

### Configurable variant media

A real image and gallery image were uploaded to Magento child
`E2E-CONF-RED`. The configurable parent was then imported through the normal
product path.

Observed Odoo result:

| Item | Result |
|---|---|
| Variant `E2E-CONF-RED` primary image | Present in `image_variant_1920` |
| Parent template primary image | Empty; parent was not overwritten |
| Variant gallery count | 1 `product.image` with `product_variant_id` set |
| Magento media IDs | 6 primary, 7 gallery |
| Pixel comparison | 96 x 96 RGB pixel hash matched Magento primary |

Magento re-encodes uploaded files, so byte hashes differ by container. The
decoded pixel hash matched exactly. The unit suite now locks this ownership
rule with `test_variant_image_is_owned_by_the_variant`.

## Customer identity

Previously verified on the same account:

- Guest orders 11-15 resolved to partners 90, 93, and 96.
- Registered orders 26-30 resolved to one partner, 129.
- Transition orders 33 and 34 resolved to one partner, 138, with both guest
  and registered mappings.
- Registered child-parent duplicate mapping was fixed in `magento_sync.py`.
- Ambiguous guest identities are reported as an issue rather than merged
  silently.

## Field mapping contract

| Area | Fields proven |
|---|---|
| Product | SKU, name, type, price, category, status, media |
| Variant | child SKU, attributes, parent identity, variant media |
| Customer | Magento ID, email, name, guest/registered flag |
| Address | billing and shipping child contacts |
| Order | Magento ID, increment ID, store, currency, totals, state |
| Order line | item ID, SKU, qty, price, tax, configurable/kit identity |
| Shipment | order, item, qty, tracking, backorders |
| Invoice | increment ID, totals, posted state, residual |
| Payment | invoice evidence, method, amount, journal, reference |
| Credit memo | increment ID, item and shipping lines, total, outbound refund |
| Inventory | SKU, source, absolute quantity, salability |
| Image | primary/gallery, MIME, label, template vs variant ownership |

## Explicit boundaries

Bundle, grouped, and downloadable products, Magento RMA, custom attributes
outside the mapping tables, and Magento special-price rules are not part of the
released contract. They are documented as unsupported rather than silently
partially synchronized.
