from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class EcommerceStore(models.Model):
    _name = "ecommerce.store"
    _description = "eCommerce Store Scope"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    backend_id = fields.Many2one(
        "ecommerce.backend", required=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True)
    external_website_id = fields.Char()
    external_website_code = fields.Char()
    external_store_view_id = fields.Char()
    external_store_view_code = fields.Char(required=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, ondelete="restrict"
    )
    stock_location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict"
    )
    pricelist_id = fields.Many2one("product.pricelist", ondelete="restrict")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    website_id = fields.Many2one("website", ondelete="set null", index=True)
    shipping_product_id = fields.Many2one(
        "product.product",
        ondelete="restrict",
        domain="[('type', '=', 'service')]",
    )
    auto_confirm_orders = fields.Boolean(default=False)
    auto_post_invoice = fields.Boolean(default=True)
    auto_register_payment = fields.Boolean(default=False)
    auto_register_refund = fields.Boolean(default=False)
    rounding_tolerance = fields.Float(default=0.01)
    stock_batch_size = fields.Integer(default=50)
    shipment_batch_size = fields.Integer(default=100)
    inventory_use_on_hand = fields.Boolean(default=True)
    inventory_subtract_reserved = fields.Boolean(default=True)
    inventory_safety_stock = fields.Integer(default=0)
    order_sync_interval_minutes = fields.Integer(default=5)
    customer_sync_interval_minutes = fields.Integer(default=30)
    catalog_sync_interval_minutes = fields.Integer(default=60)
    category_sync_interval_minutes = fields.Integer(default=60)
    inventory_sync_interval_minutes = fields.Integer(default=15)
    shipment_sync_interval_minutes = fields.Integer(default=15)
    last_preflight_at = fields.Datetime()
    last_preflight_error = fields.Char()

    _backend_code_uniq = models.UniqueIndex(
        "(backend_id, code)",
        "Store code must be unique per backend.",
    )
    _store_view_uniq = models.UniqueIndex(
        "(backend_id, external_store_view_id) WHERE external_store_view_id IS NOT NULL",
        "A Magento store view can be bound to only one store.",
    )
    _safety_check = models.Constraint(
        "CHECK (inventory_safety_stock >= 0)",
        "Safety stock cannot be negative.",
    )
    _batch_check = models.Constraint(
        "CHECK (stock_batch_size > 0 AND stock_batch_size <= 500 "
        "AND shipment_batch_size > 0 AND shipment_batch_size <= 1000)",
        "Synchronization batch sizes are out of range.",
    )
    _tolerance_check = models.Constraint(
        "CHECK (rounding_tolerance >= 0 AND rounding_tolerance <= 1)",
        "Rounding tolerance must be between 0 and 1.",
    )

    @api.constrains("backend_id", "company_id")
    def _check_backend_company(self):
        for store in self:
            if store.backend_id.company_id != store.company_id:
                raise ValidationError("Store and backend must belong to the same company.")

    @api.constrains("company_id", "warehouse_id", "stock_location_id", "currency_id", "pricelist_id")
    def _check_company_records(self):
        for store in self:
            if store.warehouse_id.company_id != store.company_id:
                raise ValidationError("Warehouse must belong to the store company.")
            if store.stock_location_id.company_id not in (False, store.company_id):
                raise ValidationError("Stock location must belong to the store company.")
            if store.pricelist_id and store.pricelist_id.company_id not in (False, store.company_id):
                raise ValidationError("Pricelist must belong to the store company.")
            if store.website_id and store.website_id.company_id != store.company_id:
                raise ValidationError("Website must belong to the store company.")


    def _ecommerce_supports_product_sync(self):
        """Whether this store can enqueue product export/update jobs."""
        return False

    def _ecommerce_enqueue_product_sync(self, product_ids, operation):
        """Connector hook: enqueue bounded product synchronization jobs.

        Connectors override this method. The free core never imports connector
        code and never calls an external API directly.
        """
        self.ensure_one()
        raise UserError("This store's provider does not support product synchronization.")


class EcommerceMappingMixin(models.AbstractModel):
    _name = "ecommerce.mapping.mixin"
    _description = "eCommerce Mapping Mixin"

    backend_id = fields.Many2one(
        "ecommerce.backend", required=True, ondelete="restrict", index=True
    )
    store_id = fields.Many2one(
        "ecommerce.store", required=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company",
        related="store_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    external_id = fields.Char(required=True, index=True)
    external_parent_id = fields.Char(index=True)
    external_code = fields.Char(index=True)
    active = fields.Boolean(default=True)
    sync_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("synced", "Synced"),
            ("failed", "Failed"),
            ("manual_review", "Manual Review"),
            ("disabled", "Disabled"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    last_synced_at = fields.Datetime()
    last_error = fields.Char()
    metadata = fields.Json(default=dict)

    @api.constrains("backend_id", "store_id")
    def _check_store_backend(self):
        for record in self:
            if record.store_id.backend_id != record.backend_id:
                raise ValidationError("Mapping backend does not match the store backend.")


class EcommerceProductMapping(models.Model):
    _name = "ecommerce.product.mapping"
    _description = "eCommerce Product Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_template_id = fields.Many2one(
        "product.template", required=True, ondelete="restrict", index=True
    )
    external_product_type = fields.Char(required=True, default="simple")
    mapping_method = fields.Selection(
        [("manual", "Manual"), ("sku_auto", "SKU Auto"), ("export", "Export")],
        default="manual",
        required=True,
    )
    external_sku = fields.Char()
    external_updated_at = fields.Datetime()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Product mapping external identity must be unique per store.",
    )
    _template_uniq = models.UniqueIndex(
        "(store_id, odoo_template_id) WHERE active IS TRUE",
        "An Odoo template can be mapped only once per store.",
    )


class EcommerceVariantMapping(models.Model):
    _name = "ecommerce.variant.mapping"
    _description = "eCommerce Variant Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_product_id = fields.Many2one(
        "product.product", required=True, ondelete="restrict", index=True
    )
    product_mapping_id = fields.Many2one(
        "ecommerce.product.mapping", ondelete="restrict", index=True
    )
    external_sku = fields.Char()
    external_barcode = fields.Char()
    mapping_method = fields.Selection(
        [
            ("manual", "Manual"),
            ("sku_auto", "SKU Auto"),
            ("import", "Import"),
            ("export", "Export"),
        ],
        default="manual",
        required=True,
    )
    last_pushed_quantity = fields.Integer(default=-1)
    last_pushed_at = fields.Datetime()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Variant mapping external identity must be unique per store.",
    )
    _product_uniq = models.UniqueIndex(
        "(store_id, odoo_product_id) WHERE active IS TRUE",
        "An Odoo variant can be mapped only once per store.",
    )


class EcommerceAttributeMapping(models.Model):
    _name = "ecommerce.attribute.mapping"
    _description = "eCommerce Attribute Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_attribute_id = fields.Many2one(
        "product.attribute", required=True, ondelete="restrict", index=True
    )
    external_attribute_type = fields.Char(default="select")
    mapping_method = fields.Selection(
        [("manual", "Manual"), ("import", "Import"), ("export", "Export")],
        default="manual",
        required=True,
    )

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Attribute mapping external identity must be unique per store.",
    )
    _attribute_uniq = models.UniqueIndex(
        "(store_id, odoo_attribute_id) WHERE active IS TRUE",
        "An Odoo attribute can be mapped only once per store.",
    )


class EcommerceAttributeValueMapping(models.Model):
    _name = "ecommerce.attribute.value.mapping"
    _description = "eCommerce Attribute Value Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "attribute_mapping_id, external_id"

    attribute_mapping_id = fields.Many2one(
        "ecommerce.attribute.mapping", required=True, ondelete="restrict", index=True
    )
    odoo_value_id = fields.Many2one(
        "product.attribute.value", required=True, ondelete="restrict", index=True
    )
    external_label = fields.Char()
    mapping_method = fields.Selection(
        [("manual", "Manual"), ("import", "Import"), ("export", "Export")],
        default="manual",
        required=True,
    )

    _external_uniq = models.UniqueIndex(
        "(attribute_mapping_id, external_id)",
        "Attribute option must be unique per attribute mapping.",
    )
    _value_uniq = models.UniqueIndex(
        "(attribute_mapping_id, odoo_value_id)",
        "An Odoo attribute value can be mapped only once per attribute.",
    )


class EcommerceCategoryMapping(models.Model):
    _name = "ecommerce.category.mapping"
    _description = "eCommerce Category Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_category_id = fields.Many2one(
        "product.public.category", required=True, ondelete="restrict", index=True
    )
    external_parent_id = fields.Char(index=True)
    external_name = fields.Char(index=True)
    external_level = fields.Integer()
    external_path = fields.Char()
    mapping_method = fields.Selection(
        [("manual", "Manual"), ("import", "Import"), ("export", "Export")],
        default="manual",
        required=True,
    )

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Category mapping external identity must be unique per store.",
    )
    _category_uniq = models.UniqueIndex(
        "(store_id, odoo_category_id) WHERE active IS TRUE",
        "An eCommerce category can be mapped only once per store.",
    )


class EcommerceCustomerMapping(models.Model):
    _name = "ecommerce.customer.mapping"
    _description = "eCommerce Customer Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_partner_id = fields.Many2one(
        "res.partner", required=True, ondelete="restrict", index=True
    )
    external_website_id = fields.Char(required=True)
    is_guest = fields.Boolean(default=False, index=True)
    mapping_method = fields.Selection(
        [
            ("manual", "Manual"),
            ("import", "Import"),
            ("email", "Email Match"),
            ("guest", "Guest Identity"),
        ],
        default="manual",
        required=True,
    )

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Customer mapping external identity must be unique per store.",
    )


class EcommerceInventorySourceMapping(models.Model):
    _name = "ecommerce.inventory.source.mapping"
    _description = "eCommerce Inventory Source Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, ondelete="restrict"
    )
    stock_location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict"
    )
    external_source_name = fields.Char()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Inventory source must be unique per store.",
    )

    @api.constrains("store_id", "active")
    def _check_one_active_source(self):
        for record in self.filtered("active"):
            count = self.search_count(
                [("store_id", "=", record.store_id.id), ("active", "=", True)]
            )
            if count > 1:
                raise ValidationError("Only one active inventory source is allowed per store.")

    @api.constrains("store_id", "warehouse_id", "stock_location_id")
    def _check_company_records(self):
        for record in self:
            if record.warehouse_id.company_id != record.store_id.company_id:
                raise ValidationError("Inventory source warehouse must belong to the store company.")
            if record.stock_location_id.company_id != record.store_id.company_id:
                raise ValidationError("Inventory source location must belong to the store company.")


class EcommerceCarrierMapping(models.Model):
    _name = "ecommerce.carrier.mapping"
    _description = "eCommerce Carrier Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    delivery_carrier_id = fields.Many2one(
        "delivery.carrier", required=True, ondelete="restrict"
    )
    external_label = fields.Char()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Carrier method must be unique per store.",
    )


class EcommercePaymentMethodMapping(models.Model):
    _name = "ecommerce.payment.method.mapping"
    _description = "eCommerce Payment Method Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    journal_id = fields.Many2one(
        "account.journal", required=True, ondelete="restrict"
    )
    external_label = fields.Char()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Payment method must be unique per store.",
    )
