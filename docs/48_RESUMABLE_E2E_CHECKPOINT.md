# Resumable E2E Checkpoint

## State

- Core/ Magento branches: 19.0 current.
- Latest local tests: 77/77 on 19, 18, 17.
- 10k run 7: done 10,043/10,043, 0 failed.
- Company B order mapping 32 / sale order 22 / invoice mapping 15.
- Image fixtures: Magento E2E-IMAGE-1, Odoo E2E-IMAGE-ODOO-1.
- Virtual fixture: Magento E2E-VIRTUAL-1, Odoo E2E-SERVICE-EXPORT-1.
- Guest orders 11–15; registered 26–30; transition 33–34.

## Resumable next actions

1. Create a real Magento partial-shipment fixture and export it through the queue.
2. Create real Magento partial/full credit memos and verify Odoo refund mappings.
3. Run the same customer/order/image smoke on 18/17 with isolated external IDs.
4. Optionally execute a live 100k financial-event stream.
5. Do not push/deploy/publish.
