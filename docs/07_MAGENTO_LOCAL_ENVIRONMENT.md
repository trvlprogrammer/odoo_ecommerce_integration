# 07 — Magento Local Environment

## 1. Current findings

Verified on 2026-10-19:

- Docker `29.9.1` and Compose `5.6.0` are available.
- No containers are running.
- The shared PostgreSQL container `odoo-dev-postgres` (`postgres:16`) exists but
  is stopped.
- No Magento image, volume, Compose project, or `.env.magento.local` exists.
- Magento is **not installed** on this machine.
- Odoo 17, 18, and 19 are already installed under `/home/ridho/Data/odoo-dev`.
- OCA `queue_job` is not installed in the active Odoo 19 environment.

Therefore this document defines a **new isolated test environment** for M1. It
does not claim that Magento is ready now.

## 2. Reuse decision

Reuse the existing Odoo 19 installation. Do not provision a second Odoo.

Create a new, isolated Magento stack for the connector. Do not reuse the SaaS
database or SaaS credentials. The SaaS reference compose at
`/home/ridho/Data/odoo-integrator/odoo-saas-integrator/docker/magento/compose.yaml`
is design evidence only and must not be copied with secrets or runtime volumes.

## 3. Version pin

| Component | Version |
| --- | --- |
| Edition | Magento Open Source |
| Magento | `2.4.7-p3` |
| PHP | 8.3 FPM image (`markoshust/magento-php:8.3-fpm-4` reference) |
| Web server | nginx (`markoshust/magento-nginx:1.24-0` reference) |
| Database | MariaDB 10.6 |
| Search | OpenSearch 2.12.0 |
| Cache/session | Redis 7.2 |
| Composer | Requires Adobe Marketplace credentials in the operator's `~/.composer/auth.json` |

Verify the exact image digests when provisioning. Do not use floating `latest`.
Record the final digests in the connector repository (not secrets).

## 4. Resource requirements

Minimum for a usable local stack:

- 4–6 CPU cores during install/indexing
- 6–8 GiB RAM available (OpenSearch alone 512 MiB heap in the reference)
- 15–25 GiB free disk for images, Magento application, database, and search
- Host has 12 CPUs, ~31 GiB RAM, ~227 GiB free — sufficient

Do not run a full reindex while Odoo integration tests are running.

## 5. Network layout

Bind only to loopback:

| Service | Host bind | Notes |
| --- | --- | --- |
| Magento HTTP | `127.0.0.1:8083` | pick next free port if occupied |
| MariaDB | none (Docker network) | optional `127.0.0.1:3307` for debugging |
| OpenSearch | none | internal only |
| Redis | none | internal only |

Before provisioning, check `ss -ltn` and `docker ps`; do not stop unrelated
services to free a port. Magento must not be exposed on `0.0.0.0`.

## 6. Compose design

Place the stack in the connector repository (during implementation, not this
documentation phase):

```
odoo_ecommerce_magento/tools/magento-compose/
  compose.yaml
  nginx/default.conf
  .env.example
  README.md
```

Services:

- `db`: MariaDB 10.6, internal volume, healthcheck.
- `redis`: Redis 7.2, internal.
- `opensearch`: OpenSearch 2.12.0 single node, security plugin disabled **only
  for isolated local use**, internal.
- `phpfpm`: PHP 8.3 FPM with Magento source volume and composer cache.
- `app`: nginx, loopback port, depends on phpfpm.

Volumes: `magento_app`, `magento_db`, `magento_search`, `magento_sock`.
No host bind of the Magento app source unless needed for debugging.

`.env.example` contains names only, no real values. `.env` is gitignored.

## 7. Provisioning steps

1. Verify Docker and free ports.
2. Require `~/.composer/auth.json` with `repo.magento.com` credentials. Do not
   copy this file into the repository.
3. Generate local-only database/admin passwords into `.env` with mode `0600`.
4. Start `db`, `redis`, `opensearch`; wait for health.
5. Create the Magento project:

   ```text
   composer create-project \
     --repository-url=https://repo.magento.com/ \
     magento/project-community-edition=2.4.7-p3 \
     /tmp/magento-project
   ```

6. Install with `bin/magento setup:install`:
   - base URL `http://127.0.0.1:8083/` (local HTTP only)
   - database host `db`
   - OpenSearch host `opensearch`
   - Redis for cache/session/page cache
   - `--cleanup-database`
7. Set developer mode for local development.
8. Disable Magento 2FA **only in this isolated stack** if the chosen Magento
   version requires it for admin token creation. This is a local convenience,
   never a production instruction.
9. Disable secure frontend/admin URLs for the local HTTP base URL.
10. Flush cache, verify frontend/health, run indexers in realtime/update-on-save.
11. Create a dedicated Integration with least-privilege ACL:
    - Sales/Orders: read; Shipments: read/write (V1)
    - Customers: read
    - Catalog: read/write only if catalog export is enabled
    - Inventory: sources read, source items write
    - Stores: read
12. Obtain the integration access token and write it to a gitignored
    `.env.magento.local` with mode `0600`.
13. Run the connector preflight and record capability flags.

Do not store the token in Git, chat, docs, test fixtures, or logs.

## 8. Test credential handling

- Local credentials live only in `.env.magento.local` (gitignored) or the
  operator's secret store.
- Odoo backend test records may reference the environment by name, but the token
  field must be populated from a secret injection step, not committed XML.
- Test fixtures use fake customer names/emails and no real payment data.
- A test database dump must be scrubbed before sharing.

## 9. Fixtures

Create deterministic fixtures in an isolated environment:

| Fixture | Example |
| --- | --- |
| Simple product | `E2E-SIMPLE-1`, SKU, price, tax class, stock |
| Configurable product | `E2E-TSHIRT`, children S/M/L with distinct prices/SKUs |
| Attribute | `e2e_size` select attribute with S/M/L options |
| Registered customer | one website-scoped customer with billing/shipping addresses |
| Guest order | same email twice to test deterministic partner reuse |
| Order economics | discount, shipping, tax, currency totals |
| Invoice/payment | paid invoice with a stable payment method code |
| Shipment | partial and full shipments, optional tracking |
| Credit memo | full/partial credit memo against an invoice |
| Inventory source | `default` source and a mapped Odoo warehouse |
| Second store view | second view on the same website for isolation tests |

Use unique prefixes such as `E2E-` and a dedicated test store view. Do not mix
fixtures with unrelated merchant data.

## 10. Health checks

```bash
curl -fsS http://127.0.0.1:8083/health_check.php
docker compose -f tools/magento-compose/compose.yaml ps
docker compose -f tools/magento-compose/compose.yaml exec -T phpfpm \
  php bin/magento --version
```

Magento health is not sufficient. The connector preflight must also verify:

- token auth
- website/store-view discovery
- MSI source read
- selected source/website binding
- Odoo connection to the intended company/database

## 11. Start, stop, reset

```bash
# start
docker compose -f tools/magento-compose/compose.yaml up -d

# status
docker compose -f tools/magento-compose/compose.yaml ps

# stop
docker compose -f tools/magento-compose/compose.yaml down

# destructive local reset (isolated stack only)
docker compose -f tools/magento-compose/compose.yaml down -v
rm -f .env.magento.local
```

Never run `down -v` against a shared or production project. Confirm the Compose
project name and volumes before destruction.

## 12. Odoo test database

Use a **new** dedicated database for native connector tests, e.g.
`ecommerce_magento_test_19`, created by M1 after explicit implementation
authorization. Do not use `odoo19_dev`, `odoo18_dev`, `odoo17_dev`, or any SaaS
database as a test target unless it is backed up and the operator explicitly
approves.

The existing PostgreSQL container can be started without modifying its data.
Implementation must use a separate database and test company. Never reset the
shared container's volume.

## 13. Magento version risks

- `2.4.7-p3` is pinned for parity with the SaaS baseline. Verify Adobe support
  status before commercial release.
- PHP 8.3 and OpenSearch 2.12 must match the chosen Magento patch's supported
  matrix. Confirm during M1.
- Composer repository credentials are required; this is a setup prerequisite,
  not something the module can automate.
- Open Source does not provide Adobe Commerce RMA. Do not simulate it.
- Local 2FA disabling is test-only and must not appear in customer install docs
  as a production recommendation.

## 14. Acceptance for M1

M1 is complete only when:

- Magento `2.4.7-p3` is reachable only on loopback.
- A least-privilege integration token works.
- Websites/store views/sources are discovered.
- A deterministic simple/configurable/customer/order fixture exists.
- Odoo 19 is running with a dedicated test database, `queue_job`, core, and
  connector installed.
- A jobrunner with workers > 1 is running.
- Credentials are absent from Git and logs.
- A clean reset and re-provision procedure is documented and tested.
