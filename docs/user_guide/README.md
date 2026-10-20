# eCommerce Integration Core — User Guide

This guide is for Odoo administrators installing the free core that supports
compatible eCommerce connectors such as Magento Connector for Odoo.

## 1. Requirements

- Odoo 17.0, 18.0, or 19.0 on the matching branch.
- OCA `queue_job` from the matching OCA/queue branch.
- A compatible connector for actual external synchronization.
- Odoo applications installed automatically as dependencies: Sales, Inventory,
  Accounting/Invoicing, Delivery, Website/eCommerce, and Manufacturing.

The core alone does not connect to Magento, Shopify, or another platform.

## 2. Repository layout and addons_path

This repository is a container; the addon is the nested directory:

```text
odoo_ecommerce_integration/          # repository root
└── odoo_ecommerce_integration/      # Odoo addon
```

Add the **repository root** to `addons_path`, not the nested addon directory.

```bash
--addons-path=/opt/odoo/addons,/opt/odoo/oca/queue,/opt/odoo/odoo_ecommerce_integration
```

## 3. Installation

1. Install OCA `queue_job`.
2. Restart Odoo and update the Apps list.
3. Install **eCommerce Integration Core**.
4. Install a compatible connector, following its own guide.

## 4. Configuration

- **eCommerce → Configuration → Backends**: create the external system,
  base URL, masked access token, company, and job user.
- **eCommerce → Configuration → Stores**: scope each store to a website/store
  view, company, warehouse, stock location, currency, and automation options.
- **eCommerce → Mappings**: product, variant, category, customer, order,
  inventory source, payment method, and carrier mappings.
- **eCommerce → Monitoring**: sync states, events, and issues.

Connector-specific fields and actions appear when a connector is installed.

## 5. Background jobs

Most work runs through OCA `queue_job`. Start Odoo with `queue_job` loaded and
run workers or a jobrunner. Verify execution in **Job Queue → Queue**. Jobs
that remain pending usually mean the runner is stopped or channel capacity is
exhausted.

## 6. Security notes

- Credentials are manager-only and masked in the form.
- Queue jobs run as the configured integration user, not superuser.
- Company record rules isolate stores and mappings.
- Never share access tokens, passwords, or customer data in support requests.

## 7. Troubleshooting

- **Missing queue_job**: install the matching OCA branch and restart Odoo.
- **Jobs pending**: start the runner and check channel capacity.
- **Access denied**: verify the user belongs to the record's company and has an
  eCommerce role.
- **Connector actions unavailable**: install the paid connector; the free core
  is a framework only.
