from odoo import fields, models


class EcommerceOrderMapping(models.Model):
    _name = "ecommerce.order.mapping"
    _description = "eCommerce Order Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, imported_at desc, id desc"

    odoo_sale_order_id = fields.Many2one(
        "sale.order", ondelete="restrict", index=True
    )
    external_order_reference = fields.Char(index=True)
    external_state = fields.Char()
    external_status = fields.Char()
    external_customer_id = fields.Char(index=True)
    is_guest = fields.Boolean(default=False)
    odoo_partner_id = fields.Many2one("res.partner", ondelete="restrict")
    odoo_invoice_partner_id = fields.Many2one("res.partner", ondelete="restrict")
    odoo_shipping_partner_id = fields.Many2one("res.partner", ondelete="restrict")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    external_grand_total = fields.Monetary(currency_field="currency_id")
    odoo_amount_total = fields.Monetary(currency_field="currency_id")
    financial_check = fields.Selection(
        [
            ("unverified", "Unverified"),
            ("matched", "Matched"),
            ("rounding", "Rounding Difference"),
            ("mismatch", "Mismatch"),
        ],
        default="unverified",
        required=True,
    )
    import_status = fields.Selection(
        [
            ("importing", "Importing"),
            ("imported", "Imported"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        default="importing",
        required=True,
        index=True,
    )
    confirmation_status = fields.Selection(
        [
            ("not_requested", "Not Requested"),
            ("pending", "Pending"),
            ("confirmed", "Confirmed"),
            ("failed", "Failed"),
        ],
        default="not_requested",
        required=True,
    )
    create_attempted_at = fields.Datetime()
    imported_at = fields.Datetime()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id)",
        "Order external identity must be unique per store.",
    )
    _sale_uniq = models.UniqueIndex(
        "(store_id, odoo_sale_order_id) WHERE odoo_sale_order_id IS NOT NULL",
        "A sale order can be mapped only once per store.",
    )
    _import_status_idx = models.Index("(store_id, import_status)")
    _imported_idx = models.Index("(company_id, imported_at)")


class EcommerceOrderLineMapping(models.Model):
    _name = "ecommerce.order.line.mapping"
    _description = "eCommerce Order Line Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "order_mapping_id, id"

    order_mapping_id = fields.Many2one(
        "ecommerce.order.mapping", required=True, ondelete="cascade", index=True
    )
    odoo_sale_order_line_id = fields.Many2one(
        "sale.order.line", required=True, ondelete="restrict", index=True
    )
    external_line_id = fields.Char(required=True)
    external_child_line_id = fields.Char()
    external_product_id = fields.Char()
    external_sku = fields.Char()
    quantity = fields.Float(digits="Product Unit")
    price_unit = fields.Monetary(currency_field="currency_id")
    discount_amount = fields.Monetary(currency_field="currency_id")
    tax_amount = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", related="order_mapping_id.currency_id", store=True, readonly=True
    )

    _line_uniq = models.UniqueIndex(
        "(order_mapping_id, external_line_id)",
        "Order item must be unique within an order.",
    )
    _child_idx = models.Index("(order_mapping_id, external_child_line_id)")
