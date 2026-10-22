# Customer and Partner Deduplication

## Guest identity policy

Guests are scoped by normalized email + company + Store website. Reuse requires
email plus matching last name, phone, or postcode. Different names/addresses
create separate partners. Child contacts are excluded from candidate matching.

## Real E2E — Odoo 19

Magento guest orders 11–15, same email `guest.repeat@example.test`:
- Orders 11/12/13, identical name/address → one partner (id 90).
- Order 14, different name/postcode → partner 93.
- Order 15, another name/postcode → partner 96.
- No uncontrolled duplicate; exactly three partners for five orders.

## Registered customer

Magento customer 3, orders 21–25 failed reuse before the fix because address
children shared the email and made candidate lookup ambiguous. Fix: registered
customer mapping is created on first order and customer candidate lookup excludes
child contacts. Retest with customer 4, orders 26–30:
- one partner (129)
- one active customer mapping for Magento customer 4.

## Guest → registered transition

Orders 33 (guest) and 34 (registered), same email:
- both map to partner 138
- one guest customer mapping and one registered customer mapping
- no duplicate partner.

## Cross-scope

Company B order and inventory remain scoped to company 5 / Store 7. A guest email
cannot reuse a partner from another company because candidate matching includes
`company_id`.
