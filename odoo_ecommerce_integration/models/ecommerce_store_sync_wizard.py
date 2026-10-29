from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .ecommerce_provider import (
    SYNC_CAPABILITY_MAP,
    SYNC_DATA_TYPES,
    SYNC_OPERATIONS,
)


class EcommerceStoreSyncWizard(models.TransientModel):
    _name = "ecommerce.store.sync.wizard"
    _description = "Run eCommerce Synchronization"

    operation = fields.Selection(
        SYNC_OPERATIONS,
        required=True,
        default="import",
    )
    data_type = fields.Selection(
        SYNC_DATA_TYPES,
        string="Data Type",
        required=True,
        default="products",
    )
    provider = fields.Selection(selection="_selection_provider", required=True)
    backend_id = fields.Many2one(
        "ecommerce.backend",
        string="Instance",
        required=True,
        domain="[('provider', '=', provider), ('active', '=', True)]",
    )
    store_ids = fields.Many2many(
        "ecommerce.store",
        string="Target Stores",
        required=True,
        domain="[('backend_id', '=', backend_id), ('active', '=', True)]",
    )
    capability_summary = fields.Text(
        readonly=True, compute="_compute_capability_summary"
    )
    can_queue = fields.Boolean(compute="_compute_capability_summary")

    @api.model
    def _selection_provider(self):
        return self.env["ecommerce.backend"]._ecommerce_provider_selection()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        providers = self._selection_provider()
        if not providers:
            raise UserError("No installed eCommerce connector is available.")
        if len(providers) == 1:
            values.setdefault("provider", providers[0][0])

        active_ids = self.env.context.get("active_ids") or []
        if (
            self.env.context.get("active_model") == "ecommerce.store"
            and active_ids
            and not values.get("store_ids")
        ):
            values["store_ids"] = [(6, 0, active_ids)]
        commands = values.get("store_ids") or []
        store_ids = commands[0][2] if commands and commands[0][0] == 6 else []
        stores = self.env["ecommerce.store"].browse(store_ids)
        if stores:
            values.setdefault("provider", stores[0].backend_id.provider)
            values.setdefault("backend_id", stores[0].backend_id.id)
        if values.get("provider") and not values.get("backend_id"):
            backends = self.env["ecommerce.backend"].search(
                [("provider", "=", values["provider"]), ("active", "=", True)],
                limit=2,
            )
            if len(backends) == 1:
                values["backend_id"] = backends.id
        return values

    @api.onchange("provider")
    def _onchange_provider(self):
        if (
            self.backend_id
            and self.backend_id.provider == self.provider
            and self.store_ids
        ):
            self._compute_capability_summary()
            return
        self.backend_id = False
        self.store_ids = [(5, 0, 0)]
        self._compute_capability_summary()
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
        current = self.store_ids
        if (
            self.backend_id
            and current
            and all(store.backend_id == self.backend_id for store in current)
        ):
            self.store_ids = [(6, 0, current.ids)]
        else:
            self.store_ids = [(5, 0, 0)]
            if self.backend_id:
                self.store_ids = [
                    (6, 0, self.env["ecommerce.store"].search([
                        ("backend_id", "=", self.backend_id.id),
                        ("active", "=", True),
                    ]).ids)
                ]
        self._compute_capability_summary()

    @api.onchange("operation")
    def _onchange_operation(self):
        capability = SYNC_CAPABILITY_MAP.get((self.operation, self.data_type))
        if self.operation and self.data_type and not capability:
            self.data_type = False
        self._compute_capability_summary()

    @api.onchange("data_type")
    def _onchange_data_type(self):
        capability = SYNC_CAPABILITY_MAP.get((self.operation, self.data_type))
        if self.operation and self.data_type and not capability:
            self.operation = False
        self._compute_capability_summary()

    @api.depends("operation", "data_type", "store_ids")
    def _compute_capability_summary(self):
        for wizard in self:
            lines = []
            capability = SYNC_CAPABILITY_MAP.get(
                (wizard.operation, wizard.data_type)
            )
            if not capability:
                wizard.can_queue = False
                wizard.capability_summary = (
                    "This operation is not available for the selected data type."
                )
                continue
            for store in wizard.store_ids:
                supported = store._ecommerce_supports(
                    wizard.data_type, wizard.operation
                )
                lines.append(
                    "%s: %s"
                    % (
                        store.display_name,
                        "supported" if supported else "not supported",
                    )
                )
            supported_count = sum(1 for line in lines if line.endswith("supported"))
            wizard.can_queue = bool(
                capability
                and lines
                and supported_count == len(lines)
            )
            wizard.capability_summary = (
                "\n".join(lines) if lines else "Select one or more stores."
            )

    def action_sync(self):
        self.ensure_one()
        if not self.env.is_superuser() and not self.env.user.has_group(
            "odoo_ecommerce_integration.group_ecommerce_operator"
        ):
            raise AccessError(
                "eCommerce Operator access is required for synchronization."
            )
        if not self.store_ids:
            raise UserError("Select at least one target store.")
        capability = SYNC_CAPABILITY_MAP.get((self.operation, self.data_type))
        if not capability:
            raise UserError(
                "The selected operation is not available for this data type."
            )
        if self.backend_id.provider != self.provider:
            raise UserError("The selected Instance does not match the provider.")
        stores = self.store_ids.filtered(
            lambda store: store.active
            and store.backend_id == self.backend_id
            and store.company_id in self.env.companies
        )
        if not stores:
            raise UserError(
                "No selected store is available for this Instance and user company."
            )
        unsupported = stores.filtered(
            lambda store: not store._ecommerce_supports(
                self.data_type, self.operation
            )
        )
        if unsupported:
            raise UserError(
                "The selected provider does not support this operation for: %s"
                % ", ".join(unsupported.mapped("display_name"))
            )
        jobs = 0
        for store in stores:
            jobs += store._ecommerce_enqueue_sync(
                self.data_type, self.operation
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "eCommerce synchronization queued",
                "message": "%s job(s) queued for %s across %s store(s)."
                % (jobs, self.data_type, len(stores)),
                "type": "success",
                "sticky": False,
            },
        }
