# Final Cross-Version Test Matrix

| Area | 19 | 18 | 17 |
|---|---|---|---|
| Full regression | 77 | 77 | 77 |
| Core-only install | PASS | PASS | PASS |
| Magento install/upgrade | PASS | PASS | PASS |
| Guest repeat orders | PASS | NOT RUN (unit equivalent) | NOT RUN |
| Registered repeat orders | PASS | NOT RUN | NOT RUN |
| Guest→registered | PASS | NOT RUN | NOT RUN |
| Product import/update | PASS | PASS unit | PASS unit |
| Product image import/export | PASS real | PASS unit | PASS unit |
| Virtual/service products | PASS real | PASS unit | PASS unit |
| Simple/registered orders | PASS real | PASS unit | PASS unit |
| Configurable/kit | PASS suite | PASS suite | PASS suite |
| Partial shipment | PARTIAL | PARTIAL | PARTIAL |
| Invoice/payment | PASS/PARTIAL | PASS suite | PASS suite |
| Refund | PARTIAL | PASS suite | PASS suite |
| Dashboard A/B | PASS separate | PASS separate | PASS separate |
| Multi-company Store View | PASS | PARTIAL | PARTIAL |
| Worker restart | PASS | PASS | PASS |
| Scheduler race | PASS | PASS | PASS |
| Uninstall isolation | PASS | PASS | PASS |
