# 02 — Repository Structure

## 1. Verified current structure

Both write-allowed repositories are empty scaffolds on `main`:

```
odoo_ecommerce_integration/
  .git/
  .gitignore
  README.md
  docs/                  # created by this documentation phase

odoo_ecommerce_magento/
  .git/
  .gitignore
  README.md
```

There is no `__manifest__.py`, module package, test suite, license file, or
implementation branch yet. Do not treat these repositories as partially built
modules.

The module roots will therefore be the repository roots:

```
odoo_ecommerce_integration/__manifest__.py
odoo_ecommerce_magento/__manifest__.py
```

## 2. Planned free-core structure

```
odoo_ecommerce_integration/
  __init__.py
  __manifest__.py
  README.md
  LICENSE                         # LGPL-3
  models/
    __init__.py
    ecommerce_backend.py
    ecommerce_store.py
    ecommerce_mapping_mixin.py
    ecommerce_product_mapping.py
    ecommerce_variant_mapping.py
    ecommerce_attribute_mapping.py
    ecommerce_customer_mapping.py
    ecommerce_order_mapping.py
    ecommerce_order_line_mapping.py
    ecommerce_invoice_mapping.py
    ecommerce_payment_mapping.py
    ecommerce_shipment_mapping.py
    ecommerce_refund_mapping.py
    ecommerce_inventory_source_mapping.py
    ecommerce_carrier_mapping.py
    ecommerce_payment_method_mapping.py
    ecommerce_sync_state.py
    ecommerce_sync_event.py
    ecommerce_sync_issue.py
  services/
    __init__.py
    mapping_service.py
    sync_state_service.py
    event_service.py
    issue_service.py
    queue_service.py
    retry_policy.py
  security/
    ecommerce_security.xml
    ir.model.access.csv
  views/
    ecommerce_backend_views.xml
    ecommerce_store_views.xml
    ecommerce_mapping_views.xml
    ecommerce_sync_state_views.xml
    ecommerce_event_views.xml
    ecommerce_issue_views.xml
    ecommerce_menus.xml
  data/
    ecommerce_cron.xml
    ecommerce_sequence.xml       # only if a human-readable reference is needed
  tests/
    __init__.py
    test_backend.py
    test_store_scope.py
    test_mapping_constraints.py
    test_sync_state.py
    test_events_issues.py
    test_security.py
    test_queue_integration.py
  docs/
    00_PROJECT_BASELINE.md
    ...
  static/description/
    icon.png
    index.html
```

Do not create every file in M2. The milestone plan defines the minimum slice.
The structure reserves ownership; unused placeholders are not evidence of work.

## 3. Planned Magento connector structure

```
odoo_ecommerce_magento/
  __init__.py
  __manifest__.py
  README.md
  LICENSE                         # OPL-1
  models/
    __init__.py
    ecommerce_backend.py          # _inherit: Magento fields/methods
    ecommerce_store.py            # _inherit: Magento scope/workflow fields
    magento_product_sync.py
    magento_customer_sync.py
    magento_order_sync.py
    magento_financial.py
    magento_inventory_sync.py
    magento_shipment_sync.py
    magento_refund_sync.py
    magento_mapping.py            # connector helpers only, no duplicate core mappings
  services/
    __init__.py
    magento_client.py             # HTTP, auth, retry, URL safety
    magento_adapter.py            # payload -> normalized DTOs/ORM vals
    magento_errors.py
    magento_catalog.py
    magento_customers.py
    magento_orders.py
    magento_finance.py
    magento_inventory.py
    magento_shipments.py
    magento_refunds.py
    magento_monitoring.py
  jobs/
    __init__.py
    catalog_jobs.py
    customer_jobs.py
    order_jobs.py
    finance_jobs.py
    inventory_jobs.py
    shipment_jobs.py
    refund_jobs.py
  security/
    magento_security.xml
    ir.model.access.csv
  views/
    magento_backend_views.xml
    magento_store_views.xml
    magento_mapping_views.xml
    magento_sync_views.xml
    magento_menus.xml
  data/
    queue_job_data.xml
    magento_cron.xml
  tests/
    __init__.py
    test_client.py
    test_auth.py
    test_scope.py
    test_catalog.py
    test_customers.py
    test_orders.py
    test_finance.py
    test_inventory.py
    test_shipments.py
    test_refunds.py
    test_queue_resilience.py
    test_multi_company.py
  tools/
    magento-compose/
      compose.yaml
      nginx/default.conf
      README.md
      .env.example
    scripts/
      magento_up.sh
      magento_fixture.sh
  static/description/
    icon.png
    index.html
```

The connector must not define parallel copies of `ecommerce.*` mapping tables or
a second sync-state/logging system. It extends core models and uses core services.

## 4. External addons layout

OCA `queue_job` is not part of either repository. A recommended local layout:

```
/home/ridho/Data/odoo-dev/19/addons/          # symlinks/custom addons
/home/ridho/Data/odoo-dev/19/addons/
  odoo_ecommerce_integration -> /home/ridho/Data/odooapps/odoo_ecommerce_integration
  odoo_ecommerce_magento     -> /home/ridho/Data/odooapps/odoo_ecommerce_magento
  queue_job                  -> /home/ridho/Data/odoo-dev/oca/queue/queue_job
```

The exact queue_job checkout must be a pinned OCA revision, not the older local
copy at `/home/ridho/Data/odoo-integrator/odoo-project/.../queue_job`.

Addons path (illustrative, adjust to the chosen checkout):

```ini
addons_path = /home/ridho/Data/odoo-dev/19/odoo-src/addons,
              /home/ridho/Data/odoo-dev/19/odoo-src/odoo/addons,
              /home/ridho/Data/odoo-dev/19/addons,
              /home/ridho/Data/odoo-dev/oca/queue
```

## 5. File ownership

| Concern | Core | Magento connector |
| --- | --- | --- |
| Backend identity | defines | extends |
| Store scope | defines | extends/validates |
| Queue dependency | declares | inherits through core |
| Mapping tables | defines | uses |
| Event/issue tables | defines | writes through services |
| Retry policies | defaults | overrides per Magento job |
| REST client | none | owns |
| Magento payloads | none | owns |
| Catalog rules | shared mapping only | owns |
| Order/finance/shipment rules | shared state only | owns |
| Views | generic | Magento-specific additions |
| ACL groups | defines | adds Magento manager rights only if needed |

## 6. Branch and tag strategy

Current state: both repositories are on `main`. Do not create branches during
this documentation phase.

Recommended implementation sequence:

1. Keep `main` as the integration branch for documentation and initial scaffolding.
2. At M1, create `19.0` from `main` for Odoo 19 implementation.
3. Develop only against `19.0`. Protect `main` from unreviewed feature work.
4. At M9, tag the verified Odoo 19 release, e.g. `19.0.1.0.0`.
5. Create `18.0` only after the Odoo 19 acceptance gate passes. Port forward,
   do not merge unverified changes backward.
6. Create `17.0` only after Odoo 18 acceptance passes.
7. Every version branch is independently installable and tagged.

Do not use one branch to claim multiple Odoo versions. Do not symlink target
repositories into version branches.

## 7. Packaging rules

- `__manifest__.py` at repository root.
- `version` begins with the Odoo major: `19.0.x.y.z`, `18.0.x.y.z`, `17.0.x.y.z`.
- `license` exactly `LGPL-3` for core and `OPL-1` for the connector.
- `depends` lists only actual dependencies.
- `application: True` on the connector if it should appear as an app; core may
  be an app or a library depending on final UX.
- `installable: True`.
- `external_dependencies` only for genuinely required Python packages.
- No `queue_job` source, no OCA code, no generated secrets.
- Include `static/description/icon.png` and a concise `index.html` for Odoo Apps.
- README installation instructions must state that Odoo does not download Git
  dependencies automatically.

## 8. Generated and forbidden files

Never commit:

- `.env`, `.env.*` with real values, tokens, Composer auth files
- Magento database dumps, customer data, production order exports
- Odoo filestore data, database backups, logs
- `__pycache__`, coverage output, local virtualenvs
- OCA `queue_job` source copied into either module
- `.codebase-memory/` indexes or agent caches
- IDE state and machine-specific paths containing credentials

The existing `.gitignore` files already exclude common Python/local artifacts.
Add explicit Magento test-environment ignores when the compose files are created.

## 9. Documentation location

Architecture and acceptance documentation belongs to the free core repository:

`odoo_ecommerce_integration/docs/`

The paid connector may contain customer-facing install notes, but the
authoritative architecture, parity matrix, and gates live in the core docs to
avoid divergence between repositories.
