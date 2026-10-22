# Release Evidence Matrix

| Evidence | Odoo 19 | Odoo 18 | Odoo 17 |
| --- | --- | --- | --- |
| Full tests | 77 pass | 77 pass | 77 pass |
| Finance 100k cursor selection | Pass (19 fixture) | Shared logic | Shared logic |
| Core-only install | Pass | Pass | Pass |
| Magento upgrade | Pass | Pass | Pass |
| Uninstall isolation | Pass | Pass | Pass |
| Worker restart | Pass (10k) | Pass (500-page run) | Pass (500-page run) |
| Dashboard Company B populated | Pass | Pass | Pass |
| Dashboard KPI exact | Pass | Pass | Pass |
| Dashboard provider/backend/Store + drill-down | Pass | Pass | Pass |
| Dashboard date/reset/filter/drill-down | Pass | Pass | Pass |
| Finance cursor logic/test | Pass | Pass | Pass |
| Inventory generation race test | Pass | Pass | Pass |
| Scheduler two-process race | Pass | Not repeated | Not repeated |
| Peak RSS | 157,612 KB | – | – |
| 10k real Magento E2E | Pass | N/A | N/A |
| Capability-aware wizard dynamic option removal | Partial | Partial | Partial |

No push, deployment, tags, or publication.
