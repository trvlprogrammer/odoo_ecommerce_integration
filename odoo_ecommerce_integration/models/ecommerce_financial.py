from odoo import fields, models


class EcommerceInvoiceMapping(models.Model):
    _name = "ecommerce.invoice.mapping"
    _description = "eCommerce Invoice Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "order_mapping_id, id"

    order_mapping_id = fields.Many2one(
        "ecommerce.order.mapping", required=True, ondelete="cascade", index=True
    )
    odoo_move_id = fields.Many2one("account.move", ondelete="restrict", index=True)
    external_increment_id = fields.Char()
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("created", "Created"),
            ("posted", "Posted"),
            ("failed", "Failed"),
            ("no_invoiceable_lines", "No Invoiceable Lines"),
            ("manual_review", "Manual Review"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    content_fingerprint = fields.Char()
    posted_at = fields.Datetime()


    _sql_constraints = [
        ('external_uniq', 'UNIQUE (store_id, external_id)', 'Invoice external identity must be unique per store.'),
        ('order_uniq', 'UNIQUE (order_mapping_id)', 'Only one invoice mapping is allowed per order in V1.'),
    ]


class EcommercePaymentMapping(models.Model):
    _name = "ecommerce.payment.mapping"
    _description = "eCommerce Payment Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "order_mapping_id, id"

    order_mapping_id = fields.Many2one(
        "ecommerce.order.mapping", required=True, ondelete="cascade", index=True
    )
    invoice_mapping_id = fields.Many2one(
        "ecommerce.invoice.mapping", ondelete="restrict", index=True
    )
    odoo_payment_id = fields.Many2one("account.payment", ondelete="restrict", index=True)
    external_invoice_id = fields.Char()
    external_method_code = fields.Char()
    amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    journal_id = fields.Many2one("account.journal", ondelete="restrict")
    payment_reference = fields.Char()
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("registered", "Registered"),
            ("manual_review", "Manual Review"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        default="pending",
        required=True,
        index=True,
    )


    _sql_constraints = [
        ('external_uniq', 'UNIQUE (store_id, external_id)', 'Payment evidence must be unique per store.'),
        ('payment_uniq', 'UNIQUE (store_id, odoo_payment_id)', 'An Odoo payment can be mapped only once per store.'),
    ]


class EcommerceShipmentMapping(models.Model):
    _name = "ecommerce.shipment.mapping"
    _description = "eCommerce Shipment Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "order_mapping_id, id"

    order_mapping_id = fields.Many2one(
        "ecommerce.order.mapping", required=True, ondelete="cascade", index=True
    )
    odoo_picking_id = fields.Many2one(
        "stock.picking", required=True, ondelete="restrict", index=True
    )
    tracking_number = fields.Char()
    tracking_carrier = fields.Char()
    content_fingerprint = fields.Char()
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("shipped", "Shipped"),
            ("adopted", "Adopted"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        default="pending",
        required=True,
        index=True,
    )


    _sql_constraints = [
        ('picking_uniq', 'UNIQUE (store_id, odoo_picking_id)', 'A picking can be mapped only once per store.'),
        ('external_uniq', 'UNIQUE (store_id, external_id)', 'Shipment external identity must be unique per store.'),
    ]


class EcommerceRefundMapping(models.Model):
    _name = "ecommerce.refund.mapping"
    _description = "eCommerce Refund Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "order_mapping_id, id"

    order_mapping_id = fields.Many2one(
        "ecommerce.order.mapping", required=True, ondelete="cascade", index=True
    )
    invoice_mapping_id = fields.Many2one(
        "ecommerce.invoice.mapping", ondelete="restrict", index=True
    )
    odoo_credit_note_id = fields.Many2one("account.move", ondelete="restrict", index=True)
    external_increment_id = fields.Char()
    amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    content_fingerprint = fields.Char()
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("imported", "Imported"),
            ("posted", "Posted"),
            ("failed", "Failed"),
            ("manual_review", "Manual Review"),
            ("skipped", "Skipped"),
        ],
        default="pending",
        required=True,
        index=True,
    )


    _sql_constraints = [
        ('external_uniq', 'UNIQUE (store_id, external_id)', 'Credit memo external identity must be unique per store.'),
        ('credit_note_uniq', 'UNIQUE (store_id, odoo_credit_note_id)', 'An Odoo credit note can be mapped only once per store.'),
    ]
