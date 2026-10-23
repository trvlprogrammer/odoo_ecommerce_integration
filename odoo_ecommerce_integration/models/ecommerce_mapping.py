import logging

from psycopg2 import IntegrityError
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .ecommerce_provider import SYNC_CAPABILITY_MAP

_logger = logging.getLogger(__name__)


class EcommerceStore(models.Model):
    _name = "ecommerce.store"
    _description = "eCommerce Store Scope"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        help="Internal Odoo store code. It is not the Magento website or store-view code.",
    )
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
    external_website_id = fields.Char(
        string="Magento Website ID",
        help="Numeric Magento website identifier used to scope catalog and customer data.",
    )
    external_website_code = fields.Char(
        string="Magento Website Code",
        help="Magento website code shown in Stores > All Stores.",
    )
    external_store_view_id = fields.Char(
        string="Magento Store View ID",
        help="Numeric Magento store-view identifier used for order discovery and payload validation.",
    )
    external_store_view_code = fields.Char(
        string="Magento Store View Code",
        required=True,
        help="Magento store-view code used in API calls and order synchronization.",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, ondelete="restrict", check_company=True
    )
    stock_location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict", check_company=True
    )
    pricelist_id = fields.Many2one("product.pricelist", ondelete="restrict")
    currency_id = fields.Many2one("res.currency", ondelete="restrict")
    website_id = fields.Many2one("website", ondelete="set null", index=True)
    shipping_product_id = fields.Many2one(
        "product.product",
        string="Shipping Product",
        ondelete="restrict",
        domain="[('type', '=', 'service')]",
        check_company=True,
        help="Service product used for the Magento shipping order line.",
    )
    default_delivery_carrier_id = fields.Many2one(
        "delivery.carrier",
        string="Default Delivery Carrier",
        ondelete="restrict",
        check_company=True,
        help="Carrier used when a Magento shipping method has no explicit carrier mapping.",
    )
    default_payment_journal_id = fields.Many2one(
        "account.journal",
        string="Default Payment Journal",
        ondelete="restrict",
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="Journal used when a Magento payment method has no explicit journal mapping.",
    )
    order_import_cutoff_date = fields.Date(
        string="Order Import Cutoff",
        help="Never import Magento orders created before this date. Leave empty to import all available orders.",
    )
    auto_confirm_orders = fields.Boolean(default=False)
    auto_post_invoice = fields.Boolean(default=True)
    auto_register_payment = fields.Boolean(default=False)
    auto_register_refund = fields.Boolean(default=False)
    rounding_tolerance = fields.Float(default=0.01)
    stock_batch_size = fields.Integer(default=50)
    shipment_batch_size = fields.Integer(default=100)
    product_batch_size = fields.Integer(default=50)
    category_batch_size = fields.Integer(default=50)
    customer_batch_size = fields.Integer(default=50)
    order_batch_size = fields.Integer(default=25)
    finance_batch_size = fields.Integer(default=25)
    inventory_use_on_hand = fields.Boolean(default=True)
    inventory_subtract_reserved = fields.Boolean(default=True)
    inventory_safety_stock = fields.Integer(default=0)
    order_sync_interval_minutes = fields.Integer(default=5)
    customer_sync_interval_minutes = fields.Integer(default=30)
    catalog_sync_interval_minutes = fields.Integer(default=60)
    category_sync_interval_minutes = fields.Integer(default=60)
    inventory_sync_interval_minutes = fields.Integer(default=15)
    shipment_sync_interval_minutes = fields.Integer(default=15)
    finance_sync_interval_minutes = fields.Integer(default=30)
    last_preflight_at = fields.Datetime()
    last_preflight_error = fields.Char()
    can_preflight = fields.Boolean(compute="_compute_capability_flags")
    can_sync = fields.Boolean(compute="_compute_capability_flags")
    can_product_sync = fields.Boolean(compute="_compute_capability_flags")

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
        "AND shipment_batch_size > 0 AND shipment_batch_size <= 1000 "
        "AND product_batch_size > 0 AND product_batch_size <= 500 "
        "AND category_batch_size > 0 AND category_batch_size <= 500 "
        "AND customer_batch_size > 0 AND customer_batch_size <= 500 "
        "AND order_batch_size > 0 AND order_batch_size <= 500 "
        "AND finance_batch_size > 0 AND finance_batch_size <= 500)",
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
            if (
                store.default_delivery_carrier_id
                and store.default_delivery_carrier_id.company_id
                and store.default_delivery_carrier_id.company_id != store.company_id
            ):
                raise ValidationError("Default delivery carrier must belong to the store company.")
            if store.default_payment_journal_id:
                if store.default_payment_journal_id.company_id != store.company_id:
                    raise ValidationError("Default payment journal must belong to the store company.")
                if store.default_payment_journal_id.type not in ("bank", "cash"):
                    raise ValidationError("Default payment journal must be a bank or cash journal.")


    def _ecommerce_schedule_operations(self):
        """Return (resource, operation, interval_minutes) for this provider."""
        return []

    @api.model
    def _cron_ecommerce_scheduler(self):
        """Provider-neutral per-store scheduler.

        Cron discovery never performs provider API calls. It only enqueues the
        provider's bounded coordinator through the capability contract.
        """
        now = fields.Datetime.now()
        stores = self.sudo().search([("active", "=", True)])
        for store in stores:
            for resource, operation, interval in store._ecommerce_schedule_operations():
                try:
                    interval = int(interval or 0)
                except (TypeError, ValueError):
                    continue
                if interval <= 0 or not store._ecommerce_supports(resource, operation):
                    continue
                state_resource = {
                    "products": "product",
                    "categories": "category",
                    "customers": "customer",
                    "orders": "order",
                    "shipments": "shipment",
                    "finance": "payment",
                    "inventory": "inventory",
                }.get(resource, resource)
                state = self.env["ecommerce.sync.state"].sudo().search(
                    [("store_id", "=", store.id), ("resource", "=", state_resource)],
                    limit=1,
                )
                last = state.last_started_at or state.last_success_at
                if last and last + timedelta(minutes=interval) > now:
                    continue
                try:
                    store.sudo()._ecommerce_enqueue_sync(resource, operation)
                except Exception:
                    _logger.exception(
                        "Could not enqueue scheduled %s %s for store %s",
                        operation,
                        resource,
                        store.id,
                    )
        return True

    @api.depends("active", "backend_id.provider")
    def _compute_capability_flags(self):
        for store in self:
            capabilities = (
                store.backend_id._ecommerce_capabilities()
                if store.backend_id and store.active
                else frozenset()
            )
            store.can_preflight = "health.preflight" in capabilities
            store.can_product_sync = "product.export" in capabilities
            store.can_sync = bool(
                capabilities - {"health.preflight"}
            )

    def _ecommerce_supports(self, resource, operation):
        """Whether this store can run a generic resource operation."""
        self.ensure_one()
        capability = SYNC_CAPABILITY_MAP.get((operation, resource))
        return bool(
            capability
            and self.active
            and capability in self.backend_id._ecommerce_capabilities()
        )

    def _ecommerce_supports_product_sync(self):
        """Whether this store can enqueue product export/update jobs."""
        return self._ecommerce_supports("products", "export")

    def _ecommerce_has_dependencies(self):
        self.ensure_one()
        models = (
            "ecommerce.product.mapping",
            "ecommerce.variant.mapping",
            "ecommerce.category.mapping",
            "ecommerce.customer.mapping",
            "ecommerce.order.mapping",
            "ecommerce.invoice.mapping",
            "ecommerce.payment.mapping",
            "ecommerce.refund.mapping",
            "ecommerce.shipment.mapping",
            "ecommerce.inventory.source.mapping",
            "ecommerce.carrier.mapping",
            "ecommerce.payment.method.mapping",
            "ecommerce.sync.state",
            "ecommerce.sync.event",
            "ecommerce.sync.issue",
            "ecommerce.sync.run",
        )
        return any(
            self.env[model].sudo().search_count([("store_id", "=", self.id)])
            for model in models
        )

    def write(self, vals):
        if "company_id" in vals or "backend_id" in vals:
            for store in self:
                new_company = vals.get("company_id", store.company_id.id)
                new_backend = vals.get("backend_id", store.backend_id.id)
                if (
                    new_company != store.company_id.id
                    or new_backend != store.backend_id.id
                ) and store._ecommerce_has_dependencies():
                    raise UserError(
                        "The store company/backend cannot be changed after "
                        "mappings, synchronization history, or transactions exist."
                    )
        return super().write(vals)

    def _ecommerce_start_run(
        self,
        resource,
        operation,
        *,
        total=0,
        queued=0,
        cursor_value=None,
        advance_cursor_on_partial=False,
    ):
        self.ensure_one()
        self._ecommerce_require_operator()
        state = self.env["ecommerce.sync.state"].search(
            [("store_id", "=", self.id), ("resource", "=", resource)],
            order="direction",
            limit=1,
        )
        if not state:
            state = self.env["ecommerce.sync.state"].create(
                {
                    "backend_id": self.backend_id.id,
                    "store_id": self.id,
                    "resource": resource,
                    "direction": "outbound"
                    if resource in ("inventory", "shipment")
                    else "inbound",
                }
            )
        return self.env["ecommerce.sync.run"].create_for_store(
            self,
            resource,
            operation,
            total=total,
            queued=queued,
            sync_state=state,
            cursor_value=cursor_value,
            advance_cursor_on_partial=advance_cursor_on_partial,
        )

    def _ecommerce_enqueue_run_child(
        self, run, method_name, args, *, channel, key
    ):
        self.ensure_one()
        return self._ecommerce_enqueue_job(
            method_name,
            *args,
            channel=channel,
            identity_key=f"ecom:run:{run.id}:{key}",
        )

    def _ecommerce_require_operator(self):
        if not self.env.is_superuser() and not self.env.user.has_group(
            "odoo_ecommerce_integration.group_ecommerce_operator"
        ):
            raise AccessError(
                "eCommerce Operator access is required for synchronization."
            )

    def _ecommerce_job_user(self):
        self.ensure_one()
        return self.backend_id.job_user_id or self.env.ref("base.user_root")

    def _ecommerce_enqueue_job(self, method_name, *args, channel, identity_key):
        """Generic queue_job enqueue helper owned by the free core.

        The job is explicitly scoped to the store company, never to the
        caller's currently selected company.
        """
        self.ensure_one()
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))", (identity_key,)
        )
        company = self.company_id
        delayable = (
            self.with_company(company)
            .with_user(self._ecommerce_job_user())
            .with_context(
                company_id=company.id,
                allowed_company_ids=[company.id],
                ecommerce_store_id=self.id,
                ecommerce_backend_id=self.backend_id.id,
                ecommerce_provider=self.backend_id.provider,
            )
            .with_delay(channel=channel, identity_key=identity_key)
        )
        try:
            with self.env.cr.savepoint():
                return getattr(delayable, method_name)(*args)
        except IntegrityError:
            existing = self.env["queue.job"].sudo().search(
                [
                    ("identity_key", "=", identity_key),
                    ("state", "in", ("pending", "enqueued", "wait_dependencies")),
                ],
                limit=1,
            )
            if existing:
                return existing
            raise

    def _ecommerce_enqueue_sync(self, resource, operation):
        """Connector hook: enqueue one provider synchronization operation."""
        self.ensure_one()
        if not self._ecommerce_supports(resource, operation):
            raise UserError(
                "This store does not support %s %s." % (operation, resource)
            )
        raise UserError(
            "The installed connector does not implement this synchronization operation."
        )

    def _ecommerce_enqueue_product_sync(self, product_ids, operation, sync_images=True):
        """Connector hook: enqueue bounded product synchronization jobs."""
        self.ensure_one()
        raise UserError("This store's provider does not support product synchronization.")

    def action_preflight(self):
        self.ensure_one()
        self._ecommerce_require_operator()
        raise UserError("This store's provider does not implement preflight.")

    def action_open_ecommerce_sync_wizard(self):
        self.ensure_one()
        self._ecommerce_require_operator()
        if not self.can_sync:
            raise UserError(
                "The installed eCommerce connector does not support synchronization."
            )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "odoo_ecommerce_integration.action_ecommerce_store_sync_wizard"
        )
        action["context"] = {"default_store_ids": [(6, 0, self.ids)]}
        return action

    def action_view_jobs(self):
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "queue_job.action_queue_job"
        )
        action["domain"] = [("channel", "=like", "ecommerce%")]
        action["context"] = {}
        return action


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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ecommerce_check_target_companies()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._ecommerce_check_target_companies()
        return result

    def _ecommerce_check_target_companies(self):
        target_fields = (
            "odoo_template_id",
            "odoo_product_id",
            "odoo_partner_id",
            "odoo_invoice_partner_id",
            "odoo_shipping_partner_id",
            "odoo_sale_order_id",
            "odoo_sale_order_line_id",
            "odoo_move_id",
            "odoo_payment_id",
            "odoo_picking_id",
            "odoo_credit_note_id",
            "journal_id",
            "delivery_carrier_id",
            "warehouse_id",
            "stock_location_id",
            "product_mapping_id",
        )
        for record in self:
            for field_name in target_fields:
                if field_name not in record._fields:
                    continue
                target = record[field_name]
                if not target or "company_id" not in target._fields:
                    continue
                target_company = target.company_id
                if target_company and target_company != record.company_id:
                    raise ValidationError(
                        "The mapped target %s belongs to another company."
                        % field_name
                    )


class EcommerceProductMapping(models.Model):
    _name = "ecommerce.product.mapping"
    _description = "eCommerce Product Mapping"
    _inherit = ["ecommerce.mapping.mixin"]
    _order = "store_id, external_id"

    odoo_template_id = fields.Many2one(
        "product.template",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
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
        "product.product",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    product_mapping_id = fields.Many2one(
        "ecommerce.product.mapping",
        ondelete="restrict",
        index=True,
        check_company=True,
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
    inventory_dirty = fields.Boolean(default=True, index=True)
    inventory_dirty_at = fields.Datetime()
    inventory_generation = fields.Integer(default=0, readonly=True)

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
        "res.partner",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
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
        "stock.warehouse", required=True, ondelete="restrict", check_company=True
    )
    stock_location_id = fields.Many2one(
        "stock.location", required=True, ondelete="restrict", check_company=True
    )
    external_id = fields.Char(
        string="Magento Source Code",
        required=True,
        help="MSI inventory source code in Magento, normally 'default'.",
    )
    external_source_name = fields.Char(
        string="Source Name",
        help="Human-readable Magento inventory source name.",
    )

    @api.onchange("store_id")
    def _onchange_store_scope(self):
        for record in self:
            if record.store_id:
                record.backend_id = record.store_id.backend_id
                record.warehouse_id = record.store_id.warehouse_id
                record.stock_location_id = record.store_id.stock_location_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            store_id = vals.get("store_id")
            if store_id and not vals.get("backend_id"):
                store = self.env["ecommerce.store"].browse(store_id)
                vals["backend_id"] = store.backend_id.id
        return super().create(vals_list)

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
        "delivery.carrier", required=True, ondelete="restrict", check_company=True
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
        "account.journal", required=True, ondelete="restrict", check_company=True
    )
    external_label = fields.Char()

    _external_uniq = models.UniqueIndex(
        "(store_id, external_id) WHERE active IS TRUE",
        "Payment method must be unique per store.",
    )
