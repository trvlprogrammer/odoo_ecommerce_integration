# Final Cross-Version Test Matrix

Superseded by `53_CROSS_VERSION_REAL_E2E.md` for the final 1.3.0 execution.

| Area | 19 | 18 | 17 |
|---|---|---|---|
| Full regression, fresh DB | 80/80 PASS | 80/80 PASS | 80/80 PASS |
| Core-only install | PASS | PASS | PASS |
| Magento install/upgrade | PASS | PASS | PASS |
| Guest repeat orders | PASS real | PASS suite | PASS suite |
| Registered repeat orders | PASS real | PASS suite | PASS suite |
| Guest to registered | PASS real | PASS suite | PASS suite |
| Product import/update | PASS real | PASS real | PASS real |
| Product image import/export | PASS real | PASS contract | PASS contract |
| Variant image ownership | PASS real | PASS contract | PASS contract |
| Virtual/service products | PASS real | PASS real | PASS real |
| Configurable order | PASS real | PASS real | PASS real |
| Phantom kit order | PASS real | PASS real | PASS real |
| Partial shipment and backorder | PASS real | PASS real | PASS real |
| Invoice and payment | PASS real | PASS real | PASS real |
| Partial/late/full refund | PASS real | PASS real | PASS real |
| Dashboard A/B | PASS separate | PASS separate | PASS separate |
| Multi-company Store View | PASS | PASS suite | PASS suite |
| Worker restart | PASS | PASS | PASS |
| Scheduler race | PASS | PASS | PASS |
| Uninstall isolation | PASS | PASS | PASS |

RMA and physical return-to-stock are outside the released contract.
