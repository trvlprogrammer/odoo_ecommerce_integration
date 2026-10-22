# Final Real Magento E2E Test Plan

## Executed on Odoo 19 with real local Magento and real queue_job

- Guest repeat orders (5), same normalized email, varying names/postal codes.
- Registered customer repeat orders (5), same Magento customer ID.
- Guest-to-registered transition with the same email.
- Product import, update, reimport.
- Primary and gallery image import with binary verification.
- Primary and gallery image export with binary round-trip and idempotent repeat.
- Virtual Magento product → Odoo service product.
- Odoo service product → Magento virtual product.
- Simple order import; existing configurable kit/order regression suite.
- Company B genuine Store View 2 order, invoice, inventory and Dashboard.
- Worker restart on 19 (10k), 18 and 17 (500-page runs).
- Finance 100k cursor selection.
- Scheduler two-process duplicate race.
- Uninstall isolation on 19/18/17.

## Not executed in this pass

- New partial-shipment and partial-refund orders on the current fixture.
- 5+ real Magento registered orders on 18/17 (equivalent suite tests only).
- Live 100k financial-event stream.
- Simultaneous browser multi-company selection (native switcher is single-active).
