# Cross-Version Real E2E

## Versions tested

| Repository | 19.0 | 18.0 | 17.0 |
|---|---|---|---|
| Magento connector | `16a3948` | `9c619f3` | `daee05d` |
| Core integration | `bbd14d5` | `2de08a6` | `0a4129f` |

All tests ran against the same real Magento 2 instance. Each version used its
own Odoo database and its own real queue worker.

## Regression suites

Fresh databases were installed with the release candidate:

| Version | Database | Core | Magento | Result |
|---|---|---|---|---|
| 19.0 | `accept_final_19` | 20 | 60 | 80/80 PASS |
| 18.0 | `accept_final_18` | 20 | 60 | 80/80 PASS |
| 17.0 | `accept_final_17` | 20 | 60 | 80/80 PASS |

The earlier 77-suite count grew to 80 with the three new regression tests:

- `test_shipments_coordinator_revisits_backorder`
- `test_auto_refund_registers_payment_without_double_reconcile`
- `test_variant_image_is_owned_by_the_variant`

## Real transaction matrix

| Area | 19.0 | 18.0 | 17.0 |
|---|---|---|---|
| Configurable order | PASS, order 35 | PASS, order 39 | PASS, order 40 |
| Virtual/service order | PASS, order 36 | PASS, order 39 | PASS, order 40 |
| Phantom kit | PASS, order 37 | PASS, order 39 | PASS, order 40 |
| Partial shipment / backorder | PASS, order 38 | PASS, order 39 | PASS, order 40 |
| Invoice and payment | PASS | PASS | PASS |
| Partial/full refund | PASS | PASS | PASS |
| Variant image ownership | PASS real | PASS test contract | PASS test contract |
| Customer deduplication | PASS real | PASS suite | PASS suite |
| Dashboard A/B isolation | PASS separate | PASS separate | PASS separate |
| Worker restart | PASS | PASS | PASS |
| Scheduler identity race | PASS | PASS | PASS |
| Uninstall isolation | PASS | PASS | PASS |

## Version-specific notes

- Odoo 19 uses `account.payment.move_id` for reconciliation; Odoo 18 and 17
  expose the same move relation and are covered by the cross-version test.
- Odoo 18 and 17 retain their native stock SMS confirmation wizard. The test
  runner completed that wizard; product behavior was unchanged.
- Odoo 17 has no `account.payment.memo`; the refund test asserts the payment
  move reference instead, which works on all three versions.
- Odoo 17 product templates use `type = product` and have no `is_storable`
  field. The cross-version fixtures use the native field shape.

## Reproducibility

Commands used the repository branch matching the Odoo server, the version's
own OCA queue checkout, and a fresh database:

```text
odoo-bin -d <fresh-db> --without-demo=all -i odoo_ecommerce_magento \
  --test-enable --test-tags=/odoo_ecommerce_integration,/odoo_ecommerce_magento \
  --stop-after-init --no-http
```

No test used a fake Magento server for the real transaction matrix.
