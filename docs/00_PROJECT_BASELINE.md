# 00 — Project Baseline

**Phase:** documentation only

**Date:** 2026-10-19

**Target:** native Odoo eCommerce integration, Odoo 19 first

**Workspace:** `/home/ridho/Data/odooapps`

## 1. Status

This document records the baseline observed before implementation. It is not an
acceptance claim. No application code, manifest, view, security rule, database,
branch, commit, or external service was changed during this phase.

Documentation is stored only in:

`/home/ridho/Data/odooapps/odoo_ecommerce_integration/docs/`

## 2. Evidence classes

| Class | Meaning |
| --- | --- |
| **VERIFIED-LOCAL** | Directly inspected on this machine during this phase |
| **VERIFIED-UPSTREAM** | Read from an official upstream source (e.g. OCA manifest/README) |
| **SAAS-EVIDENCE** | Present in the read-only SaaS reference repository |
| **HISTORICAL-CLAIM** | Recorded by the SaaS documentation but not re-executed in this phase |
| **DESIGN** | Proposed native Odoo design, not yet implemented or tested |

Where evidence is absent, this document says so. Historical acceptance markers
are not treated as proof of the current local state.

## 3. Repository baseline

All target and read-only repositories were inspected read-only.

| Repository | Branch | HEAD | Tracked changes | Write authority |
| --- | --- | --- | --- | --- |
| `odoo_ecommerce_integration` | `main` | `fc49b66f11a04ff011182bffdd168a86aa884ca7` | clean | **Allowed** (docs only this phase) |
| `odoo_ecommerce_magento` | `main` | `ecea4746619e2fa37f5492c5b9494ff944b07bc0` | clean | **Allowed** (docs only this phase) |
| `odoo_ecommerce_shopify` | `main` | `6515fbe9db2676fc785f8703e27d9b8d6fb2271e` | clean | Read-only; out of Phase 1 |
| `move_line_in_picking_list` | `19.0` | `894691104e74e4ca862bf1502286cf85f602f295` | clean | **Protected** |
| `odoo_advance_chatter` | `main` | `c6da242a2e4208fbd0e0b78a871d1cbf55c2326e` | clean | **Protected** |
| `odoo_sticky_view` | `19.0` | `111afd8d6ad643616d0bfc355c913a522d9cd814` | clean | **Protected** |
| `order_line_in_order_list` | `19.0` | `fba4274075ae40b41f3db32d262b9500363c42bc` | clean | **Protected** |
| `po_line_in_po_list` | `19.0` | `5f10e48128b55e8c2a4eb5e13be388752dbe2ebc` | clean | **Protected** |

At audit start, target repositories contained only `.gitignore`, `README.md`,
and Git metadata. They were valid empty scaffolds, not partially implemented
modules. This phase added the `docs/` directory only.

Remotes for both target repositories:

- `git@github.com:trvlprogrammer/odoo_ecommerce_integration.git`
- `git@github.com:trvlprogrammer/odoo_ecommerce_magento.git`

No `19.0`, `18.0`, or `17.0` branch was created or switched.

## 4. SaaS reference baseline

Location:

`/home/ridho/Data/odoo-integrator/odoo-saas-integrator`

| Field | Value |
| --- | --- |
| Branch | `main` |
| HEAD | `d88326de2431311cc80720b23122111ed4dc5dda` |
| Last commit | `feat(magento): use Magento order number as Odoo sale order name` |
| Working tree | One untracked `.codebase-memory/` index directory created by tooling; no tracked changes |
| Stack | FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, background worker, Next.js |
| Magento reference | Open Source `2.4.7-p3` |
| Historical state marker | `MAGENTO_V1_DEEP_HARDENING_AND_REFREEZE_COMPLETE` |

The SaaS repository is **read-only** for this project. It contains 17 Magento
test modules (`tests/test_magento*.py`, about 4,007 lines). The historical
Magento documentation records a full-suite result of 1,676 passed and 12/12 live
Magento scenarios passed on 2026-10-17. Those are **HISTORICAL-CLAIM** records;
this documentation phase did not run the SaaS test suite or live Magento tests.

The SaaS source and tests are used as behavioral evidence only. The native Odoo
modules must not copy the SaaS service architecture, require the SaaS runtime,
or depend on SaaS database tables.

## 5. Local environment baseline

| Item | Finding | Evidence |
| --- | --- | --- |
| OS | CachyOS Linux, kernel `7.2.11-1-cachyos`, x86_64 | VERIFIED-LOCAL |
| CPU / RAM | 12 CPUs, 31 GiB RAM (about 20 GiB available) | VERIFIED-LOCAL |
| Disk | ~227 GiB free on `/home` | VERIFIED-LOCAL |
| Host Python | 3.14.8; host `pip` absent | VERIFIED-LOCAL |
| Odoo 19 | `/home/ridho/Data/odoo-dev/19`, `odoo-bin --version` reports `Odoo Server 19.0`; source branch `19.0`, commit `20f5882e...` | VERIFIED-LOCAL |
| Odoo 19 Python | Venv `3.12.15`; `cryptography 42.0.8`, `requests 2.31.0`, `psycopg2 2.9.10` present | VERIFIED-LOCAL |
| Odoo 19 DB config | `odoo19_dev`, HTTP `8079`, one cron thread, workers `0` | VERIFIED-LOCAL |
| Odoo 18 | `/home/ridho/Data/odoo-dev/18`, branch `18.0`, commit `8e50ecb1...`, DB `odoo18_dev`, HTTP `8078` | VERIFIED-LOCAL |
| Odoo 17 | `/home/ridho/Data/odoo-dev/17`, branch `17.0`, commit `02d3a1d8...`, DB `odoo17_dev`, HTTP `8077` | VERIFIED-LOCAL |
| PostgreSQL | Docker container `odoo-dev-postgres` (`postgres:16`) exists but is **exited**; port `5432`; data under `/home/ridho/Data/odoo-dev/postgres/data` | VERIFIED-LOCAL |
| Docker / Compose | Docker `29.9.1`, Compose `5.6.0`; daemon available; no containers running | VERIFIED-LOCAL |
| OCA `queue_job` | Not present in any active Odoo addons path. A local checkout exists at `/home/ridho/Data/odoo-integrator/odoo-project/custom-odoo-modules/src/queue_job`, version `19.0.2.0.3`, not wired into the Odoo 19 config | VERIFIED-LOCAL |
| Magento | No running stack, no local Magento images, no Compose project, no `.env.magento.local`; not provisioned | VERIFIED-LOCAL |
| Odoo processes | No Odoo process running | VERIFIED-LOCAL |
| Odoo dev addons | Symlinks only to the four protected Odoo repos; no eCommerce modules installed | VERIFIED-LOCAL |

No database was started, created, reset, migrated, or queried for business data.
No secret file was printed. Only configuration key names and non-secret metadata
were inspected.

## 6. Upstream dependency baseline

| Dependency | Version / branch | License | Evidence |
| --- | --- | --- | --- |
| OCA `queue_job` | `19.0` branch, manifest `19.0.2.1.6` at audit time | LGPL-3 | VERIFIED-UPSTREAM |
| OCA `queue_job` Python deps | `requests`, `openupgradelib` | Upstream | VERIFIED-UPSTREAM |
| OCA `queue_job` 18.0 | manifest `18.0.4.1.1` | LGPL-3 | VERIFIED-UPSTREAM |
| OCA `queue_job` 17.0 | manifest `17.0.1.5.4` | LGPL-3 | VERIFIED-UPSTREAM |
| Magento Open Source | `2.4.7-p3` reference baseline | OSI/Adobe terms | SAAS-EVIDENCE |
| PHP for Magento | `8.3` container image in the SaaS reference compose | n/a | SAAS-EVIDENCE |
| MariaDB | `10.6` | n/a | SAAS-EVIDENCE |
| OpenSearch | `2.12.0` | n/a | SAAS-EVIDENCE |
| Redis | `7.2-alpine` | n/a | SAAS-EVIDENCE |

The local `queue_job` copy is older than the current OCA 19.0 branch. It must
not be silently copied into either target repository. M1 must install a pinned
OCA revision as an independent external addon.

## 7. Non-negotiable guardrails

1. Only `odoo_ecommerce_integration` and `odoo_ecommerce_magento` may be written.
2. This phase is documentation only.
3. Protected repositories must remain byte-for-byte and Git-state unchanged.
4. No branch switch, commit, push, tag, release, or deployment in this phase.
5. No secrets, tokens, passwords, customer PII, or production data in docs.
6. No custom queue engine and no vendored OCA source.
7. No FastAPI service in the native connector.
8. No claim of Odoo 18/17 support until the respective gates pass.
9. No claim that Magento is installed or that SaaS tests passed locally.
10. Financial and shipment writes must adopt-before-retry and fail to manual
    review when identity is ambiguous.

## 8. Baseline limitations

- The existing Odoo development databases are stopped and were not inspected
  for module state or data.
- Magento is not installed; the proposed environment is a design, not a verified
  local installation.
- The SaaS test suite and live Magento harness were not executed.
- The SaaS working tree contains an untracked codebase index; it is not part of
  this project and was not modified.
- No licensed Odoo Apps listing, price, support policy, or legal review exists
  yet.

## 9. Safe refresh procedure

Before implementation, re-verify:

```bash
git -C /home/ridho/Data/odooapps/odoo_ecommerce_integration status --short --branch
git -C /home/ridho/Data/odooapps/odoo_ecommerce_magento status --short --branch
/home/ridho/Data/odoo-dev/19/venv/bin/python \
  /home/ridho/Data/odoo-dev/19/odoo-src/odoo-bin --version
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
```

Then read `13_EXECUTION_CHECKPOINTS.md` for the next safe action.
