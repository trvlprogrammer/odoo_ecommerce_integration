# 14 — Implementation Handoff

## 1. What this phase delivered

Implementation-ready documentation for a native Odoo eCommerce integration,
with Magento first. No application code, module manifest, database change, commit,
push, or deployment was performed.

Documents:

`00` baseline · `01` architecture · `02` repositories · `03` parity ·
`04` data models · `05` queue · `06` Magento adapter · `07` local Magento ·
`08` Odoo 19 plan · `09` porting · `10` testing · `11` security/distribution ·
`12` risks/decisions · `13` checkpoints · `14` this handoff.

## 2. Verified repository baseline

| Repository | Role | State |
| --- | --- | --- |
| `odoo_ecommerce_integration` | free core, LGPL-3 | empty scaffold on `main`, HEAD `fc49b66f...`; docs added only |
| `odoo_ecommerce_magento` | paid Magento connector, OPL-1 | empty scaffold on `main`, HEAD `ecea4746...` |
| `odoo_ecommerce_shopify` | paid Shopify, out of Phase 1 | read-only, clean |
| `move_line_in_picking_list` | protected | clean, untouched |
| `odoo_advance_chatter` | protected | clean, untouched |
| `odoo_sticky_view` | protected | clean, untouched |
| `order_line_in_order_list` | protected | clean, untouched |
| `po_line_in_po_list` | protected | clean, untouched |

SaaS reference: `/home/ridho/Data/odoo-integrator/odoo-saas-integrator`,
HEAD `d88326de...`, read-only, Magento V1 historically refrozen.

## 3. Environment findings

- CachyOS Linux, 12 CPUs, 31 GiB RAM, ~227 GiB free.
- Odoo 19 source/venv installed; `Odoo Server 19.0`; Python 3.12.15.
- Odoo 18 and 17 also installed.
- PostgreSQL 16 container exists but is stopped; do not reset its volume.
- Docker/Compose available.
- OCA queue_job is **not** on the active Odoo 19 addons path. A stale local
  `19.0.2.0.3` copy exists elsewhere; do not use it implicitly.
- Magento is **not** installed. A `2.4.7-p3` isolated Docker stack must be
  provisioned in M1.
- No dedicated connector test database exists yet.

## 4. Architecture in one page

```
Magento REST Admin API
        ^
        |  connector adapter (OPL-1)
        v
odoo_ecommerce_magento
  catalog / customer / order / finance / inventory / shipment / refund jobs
        |
        |  core services + native ORM
        v
odoo_ecommerce_integration (LGPL-3)
  backend/store, mappings, sync state, events, issues, security, views
        |
        v
Odoo 19 ORM (sale, stock, account, product, partner)
        |
        v
OCA queue_job (independent LGPL-3 addon)
```

Key decisions:

- One `ecommerce.backend` per installation; one `ecommerce.store` per Magento
  website + store view.
- Product mapping = template; variant mapping = `product.product`; order lines
  and inventory use variant mappings.
- Durable Magento order identity = `entity_id`; sale order name = `increment_id`.
- Store-scoped uniqueness; company record rules on every core row.
- OCA queue_job only; all API-bound work is asynchronous and bounded.
- Adopt-before-retry for shipments and financial documents; ambiguity is a
  manual-review issue.
- Magento invoice is evidence; Odoo invoice/payment/credit note are primary.
- Native Odoo views, cron, ORM; no FastAPI, Next.js, SQLAlchemy, or Alembic.

## 5. Feature parity status

The SaaS reference demonstrates V1 outcomes for connection, catalog, customers,
orders, financial workflows, inventory, shipments, credit memos, monitoring, and
retry/ambiguity handling. The full matrix is in `03_FEATURE_PARITY_MATRIX.md`.

Status:

- **Behavior understood and mapped:** connection/scope, simple/configurable
  catalog, customers/guests, order economics, invoice/payment/credit memo,
  inventory/kit, shipments/tracking, idempotency, monitoring.
- **Native mechanism differs:** ORM vs SQLAlchemy, queue_job vs SaaS worker,
  Odoo views vs Next.js, direct ORM vs JSON-2.
- **Explicitly deferred:** images, bundle/grouped/virtual/downloadable,
  multi-source MSI, RMA, post-import edits, later tracking updates, refund
  payment automation.
- **Not verified locally:** SaaS test suite and live Magento scenarios were not
  re-run in this phase.

## 6. Critical implementation rules

1. Do not implement until authorized. This phase ends with documentation.
2. Create `19.0` only in M1. Do not touch protected repos.
3. Install queue_job as an independent pinned OCA addon; no vendoring.
4. Do not claim field-level credential encryption; follow D15 or reopen it.
5. Use `models.Constraint` on 19; `_sql_constraints` on 18/17.
6. Every mapping is store/company scoped; never use a global external ID.
7. Every remote write must have a durable mapping/fingerprint and an adoption
   path.
8. Never auto-confirm an order on a financial mismatch.
9. Never auto-register a payment without method mapping and residual/currency
   checks.
10. Do not run business jobs as superuser.
11. No secrets/PII in queue args, events, issues, logs, tests, or docs.
12. Run full live acceptance on the isolated Magento before claiming success.

## 7. Odoo 19 acceptance gate

M9 passes only when:

- Both modules install on a clean Odoo 19 database with queue_job.
- A1–A22 in `10_TESTING_AND_ACCEPTANCE.md` have executed evidence.
- Catalog simple/configurable round trip is idempotent.
- Guest repeat orders reuse one commercial partner.
- Order economics and increment-ID naming are correct.
- Financial workflows create no duplicate invoice/payment/credit note after
  crash/retry.
- Inventory/shipment tests include partial, kit, tracking, and adoption.
- Multi-store and multi-company isolation pass.
- Queue crash/requeue and concurrency pass with a real jobrunner.
- Upgrade/uninstall tests pass.
- No critical/high security finding remains.
- Docs match behavior.
- Protected repos are unchanged.
- A human maintainer records the acceptance and tag.

## 8. Odoo 18 / 17 gates

- M10 (18) starts only after M9 acceptance. Use OCA queue 18.0. Replace
  constraint syntax, audit every sale/stock/account call, port all tests, run
  full live acceptance.
- M11 (17) starts only after M10 acceptance. Repeat the audit with OCA queue
  17.0 and 17-specific ORM/view/account behavior.
- No version may be advertised before its gate. No static-analysis-only claims.
- See `09_ODOO_18_17_PORTING_PLAN.md`.

## 9. Open risks requiring owner decisions

| Risk | Decision needed |
| --- | --- |
| Magento 2.4.7-p3 support/EOL | Confirm commercial support line |
| Credential encryption | Accept D15 or approve a key-management milestone |
| Tax fidelity | Accept total-mismatch blocking or approve tax mapping |
| Refund payments | Confirm manual-only V1 |
| Multi-source MSI | Confirm one source per store |
| Odoo Apps/license | Complete legal/commercial review |
| Live payment evidence | Validate against target gateways; manual review otherwise |

## 10. Exact starting point for the next agent

**Do not write application code yet.** The next safe step is:

1. Read `13_EXECUTION_CHECKPOINTS.md` and the four decision documents:
   `01`, `04`, `05`, `11`.
2. Re-run the baseline checks in `00_PROJECT_BASELINE.md` §9.
3. Ask the operator to authorize the implementation phase and M1.
4. On authorization, execute M1 exactly as specified in
   `08_ODOO_19_IMPLEMENTATION_PLAN.md`:
   - create `19.0` branches,
   - install pinned OCA queue_job 19.0,
   - provision isolated Magento 2.4.7-p3,
   - create the dedicated Odoo 19 test DB,
   - scaffold empty modules,
   - install both modules with no business logic,
   - record evidence in `13_EXECUTION_CHECKPOINTS.md`.

Do not start M2 in the same step. M1 must be verified first.

## 11. Context recovery instructions

If a future session has no conversation history:

1. Read `13_EXECUTION_CHECKPOINTS.md` first.
2. Read `00_PROJECT_BASELINE.md` and confirm the current Git/HEAD state.
3. Read `01_ARCHITECTURE.md` and `04_DATA_MODELS.md` before touching models.
4. Read `05_OCA_QUEUE_JOB_DESIGN.md` before adding any job.
5. Read `06_MAGENTO_API_ADAPTER.md` before adding any Magento call.
6. Read `10_TESTING_AND_ACCEPTANCE.md` before claiming a milestone done.
7. Do not trust an old acceptance marker over current branch/test evidence.
8. Do not modify protected repositories or the SaaS reference.
9. If documentation and code disagree, stop and reconcile them explicitly.

## 12. Documentation acceptance

- Repository structure verified.
- Protected repositories verified clean at baseline.
- SaaS behavior audited; unavailable local execution identified.
- Core/connector boundaries defined.
- Mapping models specified.
- OCA queue_job design verified against upstream.
- Magento local environment documented with current findings.
- Odoo 19 milestones actionable.
- Odoo 18/17 porting gates defined.
- Security and commercial distribution documented.
- Tests and acceptance gates measurable.
- Handoff complete.

**Phase status: implementation executed on Odoo 19, 18, and 17 branches.
Core and connector install and pass their mocked/ORM/queue tests on all three
versions. A real OCA jobrunner executed a queued job successfully. Live Magento
acceptance is blocked because no Magento installation or Adobe Composer
credentials exist. Odoo 19/18/17 are therefore not commercially accepted, and no
version support claim beyond the recorded tests is made.**
