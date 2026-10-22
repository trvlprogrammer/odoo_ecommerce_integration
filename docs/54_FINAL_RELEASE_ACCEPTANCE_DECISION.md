# Final Release Acceptance Decision

Date: 2026-10-22

## Decision

**GO for release of the 1.3.0 line on Odoo 19, 18, and 17.**

The decision is based on fresh-database regression runs plus real Magento
transactions. It is not based on unit tests alone.

## Blocking criteria

| Criterion | Evidence | Result |
|---|---|---|
| Full regression on 19 | `accept_final_19`, 80/80 | PASS |
| Full regression on 18 | `accept_final_18`, 80/80 | PASS |
| Full regression on 17 | `accept_final_17`, 80/80 | PASS |
| Real configurable order | Magento 35, 39, 40 | PASS |
| Real virtual order | Magento 36, 39, 40 | PASS |
| Real kit order | Magento 37, 39, 40 | PASS |
| Real partial shipment | Magento 38, 39, 40 | PASS |
| Real invoice and payment | All real orders | PASS |
| Real partial and late refund | Magento 38, 39, 40 | PASS |
| Variant image ownership | Magento child image | PASS |
| Customer deduplication | Guest, registered, transition | PASS |
| Worker restart | 19, 18, 17 | PASS |
| Scheduler race | 19, 18, 17 | PASS |
| Dashboard company isolation | Separate A/B evidence | PASS |
| Uninstall isolation | Versioned test databases | PASS |

## Defects closed during acceptance

1. Backorder shipments on previously scanned orders are now discovered and
   exported.
2. Auto refund registration no longer attempts to reconcile already-reconciled
   receivable lines and uses the correct Odoo payment move.
3. Configurable child media now belongs to the variant instead of overwriting
   parent product media.

Each defect has a regression test and a real-Magento retest.

## Release boundaries

- Magento RMA and physical return-to-stock are not part of 1.3.0.
- Bundle, grouped, and downloadable products remain unsupported.
- Auto Register Refund remains off by default; credit notes stay open for
  manual refund unless the merchant enables it.
- The shipment coordinator now scans completed outgoing pickings in addition to
  cursor-advancing orders. This is correct for backorders; shipment volume
  should still be monitored after go-live.
- No push, deploy, publish, or production data change was performed as part of
  this acceptance.

## Release artifacts

- Magento connector: `16a3948` on 19.0, `9c619f3` on 18.0, `daee05d` on 17.0.
- Core integration: `bbd14d5` on 19.0, `2de08a6` on 18.0, `0a4129f` on 17.0.
- Manifest version: `19.0.1.3.0`, `18.0.1.3.0`, `17.0.1.3.0`.
- Evidence documents: 49 through 53 in this directory.

The release is accepted for packaging and merchant-side staging. Production
promotion remains a separate operational decision.
