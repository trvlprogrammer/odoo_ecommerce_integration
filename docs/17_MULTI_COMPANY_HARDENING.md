# Multi-Company Hardening

## Invariants

- Every Store has a required, indexed `company_id` defaulting to the active company.
- Store company must equal Backend company.
- Store warehouse, stock location, pricelist, and website are company-validated.
- All mappings derive stored `company_id` from `store_id.company_id`.
- Every mapping/sync model has a company record rule.
- Mapping target records are checked against the mapping company:
  - Odoo 19/18 use `check_company=True` for company-bearing targets.
  - Odoo 17 uses the same Python target-company constraint because the native
    check-company domain conflicts with group-restricted company fields.
  - Shared records with no company are allowed.
- Store company/backend changes are blocked once mappings or synchronization
  history exist. Backend company changes are blocked while stores exist.
- Product SKU matching is scoped to shared products plus the Store company.

## Execution context

`_ecommerce_enqueue_job()` creates every job with:

- `with_company(store.company_id)`
- `company_id` and `allowed_company_ids` context
- the Backend integration user

The default integration job user must have eCommerce Operator access and access
to the Backend company.

Stock move and stock quant hooks filter Stores by the move/quant company before
enqueueing inventory jobs. Shared products remain usable in multiple companies,
but stock quantities and jobs stay company-specific.

## Authorization

Read-only eCommerce Users can view authorized records but cannot test
connections, run preflight, open synchronization wizards, or execute connector
actions. Wizards are Operator/Manager only, and public methods enforce the same
group check server-side.

## Remaining policy

Dashboard queue-job provider filtering uses Store identity markers in job keys.
Queue jobs do not carry a provider field; company and Store filters are
authoritative, while provider filtering for queue counts may include jobs for
another provider serving the same Store.
