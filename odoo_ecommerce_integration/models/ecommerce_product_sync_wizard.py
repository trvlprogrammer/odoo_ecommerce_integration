from odoo import api, fields, models
from odoo.exceptions import UserError


class EcommerceProductSyncWizard(models.TransientModel):
    _name = "ecommerce.product.sync.wizard"
    _description = "Sync Product to eCommerce"

    product_ids = fields.Many2many(
        "product.product",
        string="Products",
        required=True,
        domain=[("sale_ok", "=", True)],
    )
    operation = fields.Selection(
        [
            ("export", "Export — create new external product"),
            ("update", "Update — refresh existing external product"),
        ],
        required=True,
        default="export",
    )
    provider = fields.Selection(selection="_selection_provider", required=True)
    backend_id = fields.Many2one(
        "ecommerce.backend",
        required=True,
        domain="[('provider', '=', provider), ('active', '=', True)]",
    )
    store_ids = fields.Many2many(
        "ecommerce.store",
        string="Target stores",
        required=True,
        domain="[('backend_id', '=', backend_id), ('active', '=', True)]",
    )
    existing_status = fields.Text(readonly=True, compute="_compute_existing_status")

    @api.model
    def _selection_provider(self):
        return self.env["ecommerce.backend"]._ecommerce_provider_selection()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        providers = self._selection_provider()
        if not providers:
            raise UserError(
                "No installed eCommerce connector provides product synchronization."
            )
        if len(providers) == 1:
            values.setdefault("provider", providers[0][0])
        if values.get("provider"):
            backends = self.env["ecommerce.backend"].search(
                [("provider", "=", values["provider"]), ("active", "=", True)],
                limit=2,
            )
            if len(backends) == 1:
                values.setdefault("backend_id", backends.id)
                eligible = self.env["ecommerce.store"].search(
                    [("backend_id", "in", backends.ids), ("active", "=", True)]
                ).filtered(lambda store: store._ecommerce_supports_product_sync())
                if len(eligible) == 1:
                    values.setdefault("store_ids", [(6, 0, eligible.ids)])
        active_ids = self.env.context.get("active_ids") or []
        if active_ids and not values.get("product_ids"):
            if self.env.context.get("active_model") == "product.template":
                template = self.env["product.template"].browse(active_ids[0])
                values["product_ids"] = [(6, 0, template.product_variant_ids.ids[:1])]
            elif self.env.context.get("active_model") == "product.product":
                values["product_ids"] = [(6, 0, active_ids)]
        return values

    @api.onchange("provider")
    def _onchange_provider(self):
        self.backend_id = False
        self.store_ids = [(5, 0, 0)]
        if not self.provider:
            return
        backends = self.env["ecommerce.backend"].search(
            [("provider", "=", self.provider), ("active", "=", True)], limit=2
        )
        if len(backends) == 1:
            self.backend_id = backends
            self._onchange_backend_id()

    @api.onchange("backend_id")
    def _onchange_backend_id(self):
        self.store_ids = [(5, 0, 0)]
        if not self.backend_id:
            return
        stores = self.env["ecommerce.store"].search(
            [("backend_id", "=", self.backend_id.id), ("active", "=", True)]
        ).filtered(lambda store: store._ecommerce_supports_product_sync())
        if stores:
            self.store_ids = [(6, 0, stores.ids)]
        self._compute_existing_status()

    @api.depends("product_ids", "store_ids")
    def _compute_existing_status(self):
        for wizard in self:
            lines = []
            for store in wizard.store_ids:
                store_id = store._origin.id if store._origin else store.id
                for product in wizard.product_ids:
                    product_id = product._origin.id if product._origin else product.id
                    variant = self.env["ecommerce.variant.mapping"].search(
                        [
                            ("store_id", "=", store_id),
                            ("odoo_product_id", "=", product_id),
                            ("active", "=", True),
                        ],
                        limit=1,
                    )
                    template = self.env["ecommerce.product.mapping"].search(
                        [
                            ("store_id", "=", store_id),
                            ("odoo_template_id", "=", product.product_tmpl_id.id),
                            ("active", "=", True),
                        ],
                        limit=1,
                    )
                    mapped = (
                        (variant and not variant.external_id.startswith("local:"))
                        or (template and not template.external_id.startswith("local:"))
                    )
                    if mapped:
                        external_id = (
                            variant.external_id
                            if variant and not variant.external_id.startswith("local:")
                            else template.external_id
                        )
                        state = "Mapped (external ID %s)" % external_id
                    else:
                        state = "Not mapped"
                    lines.append(f"{store.display_name} · {product.display_name}: {state}")
            wizard.existing_status = "\n".join(lines) if lines else "Select a backend and target store(s)."

    def action_sync(self):
        self.ensure_one()
        if not self.product_ids:
            raise UserError("Select at least one product.")
        if not self.store_ids:
            raise UserError("Select at least one target store.")
        backend = self.backend_id
        if not backend.active:
            raise UserError("The selected backend is inactive.")
        if backend.provider != self.provider:
            raise UserError("The selected backend does not match the chosen provider.")

        # A configurable template is synchronized once, using a representative
        # variant; sending several variants would create the same parent twice.
        products = []
        seen_templates = set()
        for product in self.product_ids.sorted("id"):
            template_id = product.product_tmpl_id.id
            if template_id in seen_templates:
                continue
            seen_templates.add(template_id)
            products.append(product)

        stores = self.store_ids.filtered(
            lambda store: store.active
            and store.backend_id == backend
            and store.company_id in self.env.companies
        )
        if not stores:
            raise UserError(
                "No selected store is available for this backend and user company."
            )
        unsupported = stores.filtered(
            lambda store: not store._ecommerce_supports(
                "products", self.operation
            )
        )
        if unsupported:
            raise UserError(
                "Product %s is not supported by: %s"
                % (
                    self.operation,
                    ", ".join(unsupported.mapped("display_name")),
                )
            )

        errors = []
        for store in stores:
            for product in products:
                variant = self.env["ecommerce.variant.mapping"].search(
                    [
                        ("store_id", "=", store.id),
                        ("odoo_product_id", "=", product.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                template = self.env["ecommerce.product.mapping"].search(
                    [
                        ("store_id", "=", store.id),
                        ("odoo_template_id", "=", product.product_tmpl_id.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                mapped = (
                    (variant and not variant.external_id.startswith("local:"))
                    or (template and not template.external_id.startswith("local:"))
                )
                if self.operation == "update" and not mapped:
                    errors.append(
                        "%s is not mapped in %s. Use Export for the first synchronization."
                        % (product.display_name, store.display_name)
                    )
                if self.operation == "export" and mapped:
                    errors.append(
                        "%s is already mapped in %s. Use Update to refresh it."
                        % (product.display_name, store.display_name)
                    )
        if errors:
            raise UserError("\n".join(errors))

        jobs = 0
        for store in stores:
            jobs += store._ecommerce_enqueue_product_sync([product.id for product in products], self.operation)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "eCommerce synchronization queued",
                "message": "%s job(s) queued for %s product(s) across %s store(s)."
                % (jobs, len(products), len(stores)),
                "type": "success",
                "sticky": False,
            },
        }
