# 11 — Security and Commercial Distribution

## 1. Security scope

Native Odoo changes the trust boundary compared with the SaaS:

- Odoo is both the UI and the runtime.
- Odoo users have ORM access to connector models unless record rules/ACLs stop
  them.
- Jobs run inside Odoo workers with Odoo credentials.
- Magento credentials are stored in the customer's Odoo database.
- Financial documents and customer PII live in Odoo.

The design therefore treats company isolation, secret handling, and
adopt-before-retry as product requirements, not hardening extras.

## 2. Threats and controls

| Threat | Control |
| --- | --- |
| Token theft from DB/backup | Manager-only field, masked UI, no logs; DB/disk encryption or secret-managed deployment |
| Token in logs/events/jobs | Central redaction; never pass token to job args; sanitize Magento errors |
| Cross-company data leak | `company_id` on every row; record rules; company context on every ORM lookup |
| Malicious Magento URL (SSRF) | URL normalization, metadata-endpoint block, no redirects, manager-only config |
| Malicious API response | Schema/type validation, bounded response size, no `eval`, no raw SQL |
| Duplicate money/stock documents | Unique store-scoped mappings + adopt-before-retry + concurrency locks |
| Unauthorized financial action | Manager/accounting rights; explicit action; auditable mapping state |
| PII over-collection | Import only operational fields; no marketing/password/token data |
| Job replay/duplicate | OCA identity_key + mapping constraints + state checks |
| Unsupported product type corrupts data | Explicit type detection; fail closed |
| Partial write after crash | Persist intent/fingerprint; adopt exact match; ambiguity → manual review |

## 3. Credential handling decision

Odoo `Char(password=True)` masks the value in the UI but **does not provide
field-level encryption at rest**. This project does not invent a home-grown
cryptography scheme.

V1 decision:

- Store the Magento integration token in a manager-only `access_token` field
  with `password=True`.
- Never expose it in list/tree views, search, exports, events, issues, job
  arguments, or exception text.
- Require a dedicated Odoo integration user for jobs; do not run jobs as
  superuser.
- Document that production deployments must protect the database at rest
  (encrypted volume/backup, restricted DB access) or inject the token through
  an approved secret-management deployment.
- If a customer requires application-level field encryption, treat it as a
  separately approved security milestone with a documented key-management
  design. Do not silently substitute a DB-stored key for real encryption.

This is a deliberate tradeoff: simpler and auditable, but weaker than a dedicated
secret manager. It must be disclosed in the customer security notes.

## 4. Access control

Groups:

- `group_ecommerce_user` — read-only operational visibility.
- `group_ecommerce_operator` — mappings, manual sync, safe retry, issue resolve.
- `group_ecommerce_manager` — backend/store configuration and credentials.
- `base.group_system` — emergency administration only.

Rules:

- All `ecommerce.*` records have a company record rule.
- Backend/store access also requires the user's company to match.
- Credentials are not readable by operators.
- Job user must be a dedicated internal user with operator rights and the
  required sale/stock/account company access.
- Scheduled crons enqueue jobs; they do not use the superuser.
- Archiving is preferred to deletion. Hard deletion is manager-only and
  restricted by foreign keys once financial/shipment history exists.

Test both positive and negative access. UI hiding is not a security control.

## 5. Data minimization

- Do not store raw Magento request/response bodies in events/issues.
- Do not store customer passwords, tokens, or payment card data.
- Customer email/phone/address are stored only in Odoo partners/orders as
  required for fulfillment and accounting.
- Job descriptions contain entity references, not customer payloads.
- Queue job `result`/error fields are sanitized and bounded.
- Live test fixtures use fake data and are never committed with real PII.

## 6. Logging and redaction

- Log store/backend references, entity IDs, operation, status, retry count, and
  sanitized reason codes.
- Never log `Authorization`, cookies, tokens, full URLs with query secrets, or
  raw Magento exception bodies.
- Error messages stored in mappings/issues are short codes plus safe context.
- Configure Odoo log retention and access controls; logs are not a second
  database of customer data.

## 7. Financial safety rules

1. Never create a second invoice/payment/credit note for one evidence key.
2. Never auto-post if totals/currency/residual checks fail.
3. Never auto-confirm an order with a financial mismatch.
4. Never infer a payment from amount/time alone.
5. Adopt only an exact fingerprint; zero or multiple matches is manual review.
6. Do not mutate posted accounting documents during retry.
7. Refund payment automation is out of V1.
8. RMA is unsupported on Magento Open Source.

## 8. Distribution model

| Component | Technical name | License | Distribution |
| --- | --- | --- | --- |
| Free core | `odoo_ecommerce_integration` | LGPL-3 | Public repository + Odoo Apps free listing |
| Paid Magento connector | `odoo_ecommerce_magento` | OPL-1 | Commercial Odoo Apps listing / licensed delivery |
| OCA queue_job | `queue_job` | LGPL-3 (upstream) | Independently installed; not bundled |
| Shopify connector | `odoo_ecommerce_shopify` | To be decided | Out of Phase 1 |

Odoo 19 lists `LGPL-3` and `OPL-1` as valid manifest licenses. OPL-1 is the Odoo
Proprietary License v1.0 commonly used for paid Odoo Apps. This document is not
legal advice. Before commercial release:

- Review the OPL-1 text and Odoo Apps terms.
- Confirm the paid connector's dependency on the LGPL-3 core and queue_job is
  acceptable for the intended distribution.
- Preserve all upstream copyright/license notices.
- Do not relicense OCA code.
- Have counsel review the final commercial terms if required.

## 9. Installation instructions (customer-facing)

The connector is **not** auto-installed by declaring a dependency. Odoo does not
download external Git repositories. The customer must:

1. Install the free core `odoo_ecommerce_integration`.
2. Install OCA `queue_job` from the matching OCA branch.
3. Add the connector to `addons_path`.
4. Install `odoo_ecommerce_magento`.
5. Configure the backend URL/token and store scope.
6. Run preflight and test connection.
7. Enable scheduled jobs only after preflight passes.

Suggested README order:

```text
1. Prerequisites: Odoo 19, PostgreSQL, Python requests/openupgradelib,
   OCA queue_job 19.0.
2. Add all three addon paths.
3. Install queue_job, then odoo_ecommerce_integration, then
   odoo_ecommerce_magento.
4. Configure Magento integration/token.
5. Configure website/store view, company, warehouse, source, mappings.
6. Test connection/preflight.
7. Start jobrunner with workers > 1.
8. Enable schedules.
```

Do not tell customers to copy OCA code into the paid module. Do not imply that
the free core downloads the paid connector.

## 10. Odoo Apps packaging checklist

- `__manifest__.py` at repo root, valid version/license/depends.
- `README.md` and `static/description/index.html` with accurate features and
  limitations.
- Icon and screenshots without customer data/secrets.
- No bundled queue_job or third-party source without license compliance.
- No secrets, tokens, database dumps, or local paths.
- Clear supported Odoo versions.
- Clear external dependency installation steps.
- Accurate price/license listing metadata managed in the Odoo Apps backend.
- A support/security contact and vulnerability reporting process.
- A changelog per release.

## 11. Version and support policy

- Do not advertise Odoo 18/17 until the corresponding gate is recorded.
- Do not advertise unsupported Magento editions/versions.
- State the tested Magento version (`2.4.7-p3`) and the compatibility policy.
- State V1 limitations explicitly (images, bundle/grouped, MSI multi-source,
  RMA, post-import edits, later tracking changes, refund payment automation).
- Security fixes are released for supported version branches; old branches are
  not silently claimed as supported.

## 12. Repository hygiene

- `.env*`, tokens, and customer data are gitignored.
- No secrets in test fixtures or docs.
- No broad cleanup scripts that touch the workspace or protected repositories.
- Each release is tagged in its own version branch.
- `git diff --check` and a secret scan run before release.
- Protected repositories are never installed/upgraded as part of this product.

## 13. Incident response (minimum)

1. Revoke the Magento integration token.
2. Disable the backend/store and queue schedules.
3. Preserve sanitized logs; do not copy PII into tickets.
4. Identify affected mappings/documents by entity IDs.
5. Patch, test, and release on all supported branches.
6. Notify customers according to contractual/legal obligations.
