# Odoo eCommerce Integration Core

Shared, provider-neutral integration framework for native Odoo eCommerce
connectors. Supported target branches: Odoo 19, 18, and 17.

## Repository layout

This repository is a container for one Odoo addon:

```text
odoo_ecommerce_integration/          # repository root (add to addons_path)
├── docs/
├── LICENSE
├── README.md
├── .gitignore
└── odoo_ecommerce_integration/      # Odoo addon (technical module name)
    ├── __init__.py
    ├── __manifest__.py
    ├── models/
    ├── services/
    ├── security/
    ├── tests/
    └── views/
```

Add the repository root to `addons_path`, for example:

```bash
--addons-path=/path/to/odoo/addons,/path/to/oca/queue_job,/path/to/odoo_ecommerce_integration
```

The nested directory keeps the technical module name unchanged. Do not add the
repository root itself as a module.

## Features

- Backend and store-scope identity
- Store-scoped product, variant, attribute, category, customer, order, invoice,
  payment, shipment, refund, carrier, payment-method, and inventory-source
  mappings
- Persistent synchronization state
- Operational events and actionable issues
- Multi-company record rules and role-based access
- OCA `queue_job` integration
- Native Odoo views and menus

## Dependencies

- `base`, `mail`, `sale_management`, `stock`, `account`, `delivery`,
  `website_sale`, `mrp`
- OCA `queue_job` from the matching OCA/queue branch (`19.0`, `18.0`, `17.0`)

Odoo does not download Git dependencies automatically. Install `queue_job` as
an independent addon from the matching branch.

Install order: `queue_job`, then `odoo_ecommerce_integration`.

## License

LGPL-3. See `LICENSE`.
