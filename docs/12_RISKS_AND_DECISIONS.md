# 12 — Risks and Decisions

## 1. Decision log

| ID | Decision | Status | Rationale | Consequences |
| --- | --- | --- | --- | --- |
| D1 | Odoo 19 first, then 18, then 17 | Accepted | Directive; newest ORM first, sequential gates | 18/17 are not started until prior gate passes |
| D2 | Free core + paid Magento connector | Accepted | Product model | Core must be independently useful; connector owns Magento API |
| D3 | OCA queue_job mandatory | Accepted | Mature OCA job system; no custom queue | External dependency installation required |
| D4 | Backend = installation; Store = website + store view | Accepted | Avoid credential duplication; preserve Magento scope | One store view per store; duplicate binding rejected |
| D5 | Product mapping = template; variant mapping = `product.product` | Accepted | Supports simple/configurable and order lines | Simple products need both mappings |
| D6 | Store-scoped unique external identities | Accepted | Prevent cross-store/company collisions | No global external-ID constraints |
| D7 | Use increment ID as `sale.order.name`, `entity_id` as identity | Accepted | Merchant-facing name; durable idempotency | Name collision with unrelated order must fail safely |
| D8 | Odoo invoice is primary; Magento invoice is evidence | Accepted | Avoid duplicate accounting | Magento invoice creation is out of V1 |
| D9 | Payment registration only with exact evidence/method mapping | Accepted | Financial safety | Some payments require manual review |
| D10 | Refund payment automation out of V1 | Accepted | Weak gateway evidence | Credit notes only; payment refund remains manual |
| D11 | One active MSI source per store | Accepted | SaaS parity and safety | Multi-source MSI deferred |
| D12 | No RMA on Magento Open Source | Accepted | Edition capability | RMA deferred; never simulated |
| D13 | No product images/bundle/grouped/virtual/downloadable | Accepted | SaaS V1 scope | Unsupported types fail safely |
| D14 | No tax-rate mapping model in V1 | Accepted | Simplicity; use Odoo product taxes | Total mismatch blocks auto-confirm and opens issue |
| D15 | Credential field is masked, not field-encrypted | Accepted for V1 | Avoid home-grown crypto | Production must protect DB at rest; disclosed limitation |
| D16 | No custom FastAPI/Next.js in native product | Accepted | Odoo-native operation | Native views/cron/jobs only |
| D17 | Store scan jobs are bounded; per-entity jobs for work | Accepted | Avoid giant jobs | More queue rows, better isolation |
| D18 | Adopt-before-retry for all non-idempotent writes | Accepted | Prevent duplicates | Requires fingerprint queries and manual-review paths |
| D19 | Magento 2.4.7-p3 pinned for V1 | Accepted | SaaS parity baseline | Verify support/EOL before commercial release |
| D20 | No webhooks in V1 | Accepted | Polling-first parity; Open Source webhook uncertainty | Polling latency and API load |
| D21 | Native Odoo 19 `models.Constraint` | Accepted | 19 ORM requires it | 17/18 branches use `_sql_constraints` |

## 2. Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| R1 | Magento 2.4.7-p3 support/EOL changes during development | Medium | High | Verify support matrix at M1 and before release; document compatibility; plan a later patch line | Product/eng |
| R2 | Magento REST shipment/credit memo payloads differ from SaaS assumptions | Medium | High | Validate against isolated 2.4.7-p3 OpenAPI/live calls; contract tests; fail closed | Connector eng |
| R3 | Payment evidence is gateway-dependent | High | High | Manual review when evidence is weak; require explicit journal mapping; never infer | Finance eng |
| R4 | Odoo tax totals differ from Magento totals | High | Medium | Compare totals; block auto-confirm; issue; V1 does not auto-correct taxes | Connector eng |
| R5 | Credential at-rest exposure | Medium | High | Manager-only, DB/disk encryption, backups, secret-managed deployments; no logs | Security |
| R6 | Cross-company data leak | Low | Critical | Company field + record rules + negative tests; company-scoped ORM context | Security |
| R7 | Duplicate payment/invoice/shipment after crash | Medium | Critical | Unique mappings, adopt-before-retry, concurrency tests, manual review | Finance/eng |
| R8 | OCA queue_job version/API drift | Medium | High | Pin exact branches/commits; install per version; test jobrunner | Platform |
| R9 | Local queue_job checkout is stale/wrong | Medium | Medium | Do not use it implicitly; M1 installs pinned OCA 19.0 | Platform |
| R10 | Magento API rate limits/timeouts | Medium | Medium | Bounded pages, backoff, `Retry-After`, channel capacity | Connector eng |
| R11 | Product structure corruption on round trip | Medium | High | Conservative field ownership; unsupported types fail; idempotent tests | Catalog eng |
| R12 | Guest/customer identity ambiguity | Medium | High | Deterministic reuse; no fuzzy merge; manual review on ambiguity | Orders eng |
| R13 | Multi-store scope collision | Low | High | Unique store-view binding; store-scoped constraints; isolation tests | Platform |
| R14 | Financial posting cannot be undone by a retry | Low | Critical | Re-read posted state; never mutate posted docs; manual review | Finance eng |
| R15 | Odoo 18/17 API differences are underestimated | High | High | Sequential ports with source audit and full live acceptance | Porting eng |
| R16 | Odoo Apps/license compatibility | Medium | High | Legal review; preserve LGPL/OCA notices; OPL-1 listing compliance | Product/legal |
| R17 | Customer data in logs/issues | Medium | High | Central redaction; bounded metadata; tests | Security |
| R18 | Installation friction (queue_job, Composer, cron/worker) | High | Medium | Clear install docs; preflight; diagnostics | Support |
| R19 | Long-running jobs starve finance/orders | Medium | High | Separate channels; bounded batches; priorities; no giant jobs | Platform |
| R20 | Magento DB/OpenSearch resource exhaustion on dev machine | Medium | Medium | Resource limits, loopback, documented teardown | Dev env |

## 3. Open decisions

These require evidence or operator approval before the related milestone:

1. **Magento support window:** confirm `2.4.7-p3` is acceptable for commercial
   release, or select a supported patch line.
2. **Credential encryption:** decide whether field-level encryption/secret
   manager integration is required for the paid release (currently D15).
3. **Tax mapping:** decide whether V1 total-mismatch issues are sufficient or a
   tax mapping model is required for target merchants.
4. **Customer creation in Magento:** V1 does not push Odoo partners to Magento;
   confirm this remains the product boundary.
5. **Refund payment:** confirm manual-only for V1.
6. **Multi-source MSI:** confirm one source per store is acceptable for V1.
7. **Webhooks:** confirm polling-only for V1.
8. **Shopify interface:** do not design shared Shopify-specific fields until a
   Shopify milestone is approved; only generic core interfaces now.
9. **Odoo Apps pricing/support:** commercial terms not defined in this phase.
10. **SaaS decommissioning:** native modules must not require SaaS; no decision
    yet on migrating existing SaaS mappings/data.

## 4. Accepted limitations (V1)

- No product images, bundle, grouped, virtual, downloadable products.
- No multi-source MSI; one active source per store.
- No Adobe Commerce RMA on Open Source.
- No post-import order edits/cancellations.
- No tracking update after a Magento shipment exists.
- No refund payment automation based on weak evidence.
- No tax-rate mapping/auto-correction.
- No webhooks/event bus; polling-first.
- No Odoo 18/17 support until separately accepted.
- No Shopify functionality in Phase 1.

## 5. Rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| Keep FastAPI/SaaS as the native runtime | Violates native Odoo requirement; adds deployment dependency |
| Custom queue engine | Duplicates OCA; violates queue directive |
| One backend per Magento website | Duplicates credentials; ambiguous connection health |
| Global external-ID uniqueness | Collides across stores/companies |
| Use Magento invoice as accounting source | Duplicates Odoo accounting and bypasses Odoo tax/journal control |
| Auto-create missing products from orders | Hides mapping errors; unsafe commercial data |
| Auto-retry ambiguous shipment create | Duplicates shipments |
| Store OCA source in the paid module | License/maintenance violation |
| Claim 18/17 support from static analysis | Unverified compatibility claim |
| Field-level crypto with a DB-stored key | False sense of security; needs proper key management |

## 6. Decision review triggers

Re-open the relevant decision when:

- Magento version/edition changes.
- A merchant demonstrates a required tax, MSI, RMA, or refund-payment use case.
- A security review requires field-level encryption.
- queue_job upstream changes its API or support matrix.
- Odoo 18/17 acceptance exposes a material API difference.
- Odoo Apps/license review changes distribution terms.
- A live Magento contract test disproves an adapter assumption.
