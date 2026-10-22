# Order, Fulfillment and Kit E2E

## Executed

- Guest simple orders 11–15 imported with increment IDs and one sale order each.
- Registered simple orders 26–30 imported and reused one partner/mapping.
- Mixed existing configurable/kit regression suite passes (77 tests).
- Company B order 10 (Store View 2) imported as sale order 22, company 5.
- Shipment export tests and quantity caps pass in the automated suite.
- Historical 10k/fixture smoke covered simple/configurable orders.

## Partial shipment and kit

Existing automated coverage verifies shipment quantity capping, backorders,
tracking, configurable parent/child item identity, and phantom-kit component
quantity. A new real Magento partial-shipment + partial-refund order was not
created in this pass.

## Status

Simple/configurable/virtual order paths and shipment logic are verified. New live
partial shipment and kit order E2E remain **NOT RUN** for this fixture.
