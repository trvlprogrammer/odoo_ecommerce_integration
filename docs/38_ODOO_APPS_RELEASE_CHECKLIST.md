# Odoo Apps Release Checklist

## Core

- Name/summary present, application false.
- Version `19.0.1.3.0` / branch equivalents.
- License LGPL-3.
- Dependencies: base, mail, sale_management, stock, account, delivery,
  website_sale, queue_job.
- 6 declared images; all paths exist.
- Dashboard assets bundle present.
- No credentials/logs/test fixtures in the addon folder.

## Magento

- Name/summary present, application true.
- Version `19.0.1.2.0` / branch equivalents.
- License OPL-1.
- Price USD 280.0.
- Depends on `odoo_ecommerce_integration` and `mrp`.
- 7 declared images; all paths exist.
- No credentials/logs/test fixtures in the addon folder.
- Local compose tools remain outside the addon package.

## Listing

Verified Dashboard, Store Sync, product Sync, provider/backend/Store settings,
and queue/reliability wording against implemented behavior. No unsupported
feature claims introduced. No publication performed.
