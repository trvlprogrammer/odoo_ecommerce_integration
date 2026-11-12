# 58 — Core extensions for the Shopify provider (19.0)

Backward-compatible additions made on branch `19.0` while implementing the Shopify
connector (`odoo_ecommerce_shopify`, phases S2–S11). Manifest version `19.0.1.13.0`.
Odoo 18.0 and 17.0 are unchanged.

| Change | Why |
| --- | --- |
| Capability `return.import`, sync data type `returns`, map `("import", "returns")` | Providers can schedule the import of physical returns |
| Sync state resource `return`; scheduler maps `returns` → `return` | Watermarks and last-run times for returns |
| `ecommerce.store.provider` (related to `backend_id.provider`) | Views can hide provider-specific buttons and fields |
| `services.records.record_issue_durably(env, store, ...)` | Writes an issue through a separate cursor (`lock_timeout` 2 s) so it survives the rollback of a failed queue job; falls back to the normal write when the store is not committed yet |

## Sale Order Prefix (2026-11-10, 19.0.1.14.0)

`ecommerce.store.sale_order_prefix` is shown for every provider on Orders & Finance,
before Auto Confirm Orders. `_ecommerce_sale_order_name(number)` returns the prefix
followed by the platform order number, or the number unchanged when the prefix is
empty. Magento uses it for sale order names and collision checks (unchanged names
without a prefix); Shopify uses it instead of its former own prefix field.
Verified: Core + Magento + Shopify tests 0 failed of 254; field order checked in the
`odoo19_dev` UI for a Magento and a Shopify Store.

## Instance creation from the form (fixed 2026-11-09)

Creating any Instance from the form failed with "Missing required value for the field
'Provider' (provider)". The form edits the non-stored `provider_ui`; its inverse only
runs after the INSERT, so the required `provider` column was NULL (PostgreSQL NOT NULL
violation, for every provider). Picking a provider also did not update `provider` in
the form, so provider-specific sections stayed hidden until saving. `create` and
`write` now copy `provider_ui` into `provider` before saving, and an onchange sets it
immediately. Records created from code with `provider` are unaffected.

Verified on `odoo19_dev` (web_save reproduction before/after, real browser: Shopify
create, save, edit, Test Shopify Connection; Magento create and edit) and by
`test_instance_form_creates_and_edits_with_the_provider_selection` (Core) and the
form tests of the Shopify and Magento connectors.

No existing behaviour changed: providers that do not declare `return.import` see no new
scheduled operation, and `record_issue` is unchanged.

Verification on Odoo 19 (2026-11-09):

- Fresh database with Core + Magento + Shopify, all module tests: 0 failed of 233 after
  the Magento test-data fix described in the Magento repository.
- After uninstalling Shopify: Core 35 and Magento 86 test methods, 0 failed of 109.
- Upgrade of `odoo19_dev` to this version: no errors.

Known pre-existing issue, not changed here: `migrations/19.0.1.9.0/post-migrate.py`
has an indentation error at line 24 (it only runs when upgrading from before 19.0.1.9.0).

## Migration fix (2026-11-12)

`migrations/19.0.1.9.0/post-migrate.py` (from commit 02dda23) had an indentation error and
did not compile, so upgrades from versions before 19.0.1.9.0 would fail. The branch that drops
the legacy table when carrier mappings have no shipping product column now drops the old Store
column and returns as intended.
