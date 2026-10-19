# Odoo eCommerce Integration Core

Shared, provider-neutral integration framework for native Odoo 19 eCommerce
connectors.

## Features

- Backend and store-scope identity
- Store-scoped product, variant, attribute, customer, order, invoice, payment,
  shipment, refund, carrier, payment-method, and inventory-source mappings
- Persistent synchronization state
- Operational events and actionable issues
- Multi-company record rules and role-based access
- OCA `queue_job` integration
- Native Odoo views and menus

## Dependencies

Odoo 19 modules: `base`, `mail`, `sale_management`, `stock`, `account`,
`delivery`, and OCA `queue_job`.

Install OCA `queue_job` as an independent addon from the OCA/queue `19.0`
branch. Odoo does not download Git dependencies automatically.

## License

LGPL-3. See the repository license metadata.
