# Final Release Acceptance

Superseded on 2026-10-22 by `54_FINAL_RELEASE_ACCEPTANCE_DECISION.md`.

## Final decision

**GO for release of the 1.3.0 line on Odoo 19, 18, and 17.**

The previously listed gaps for live partial shipment and partial/full refund
were closed with real Magento orders 35-40 and are recorded in documents 49-53.

Remaining non-blocking items:

- The 100k finance fixture measured cursor selection and query cost; a live
  100k financial-event stream was not replayed in this final pass.
- Native Odoo permits one active company per browser session; Dashboard A/B
  isolation was verified with separate sessions.
- Magento RMA and physical return-to-stock remain outside the 1.3.0 contract.

See `54_FINAL_RELEASE_ACCEPTANCE_DECISION.md` for the accepted criteria,
defects closed, boundaries, and artifact identifiers.
