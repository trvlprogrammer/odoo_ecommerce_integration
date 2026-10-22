# Invoice, Payment and Refund E2E

## Executed

- Company B order 10 imported into company 5.
- Posted invoice 15, company 5, total 42.95.
- Existing payment adoption/residual tests pass.
- Existing credit-note tests pass for partial/full behavior in the automated
  suite.
- Finance cursor 100k selection and idempotent mapping tests pass.

## Not executed in this pass

- New real Magento full/partial/multiple refunds on the current order fixture.
- Live late refund discovery after order synchronization.
- New real partial payment scenario.

Status: invoice posting and financial mapping are verified; new real refund and
partial-payment E2E remain **NOT RUN**.
