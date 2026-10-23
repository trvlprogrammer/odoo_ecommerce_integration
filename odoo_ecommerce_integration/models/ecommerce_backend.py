from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError

from .ecommerce_provider import CAPABILITY_DEFINITIONS


class EcommerceBackend(models.Model):
    _name = "ecommerce.backend"
    _description = "eCommerce Backend"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    provider = fields.Char(
        required=True,
        help="Internal provider code. Select the friendly provider in the form.",
    )
    provider_ui = fields.Selection(
        selection="_ecommerce_provider_selection",
        string="Provider",
        compute="_compute_provider_ui",
        inverse="_inverse_provider_ui",
        store=False,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True)
    base_url = fields.Char(required=True)
    allow_insecure_http = fields.Boolean(default=False)
    allow_private_network = fields.Boolean(
        default=False,
        help="Development only: allow HTTPS endpoints that resolve to a private address. "
        "Never enable this for a production backend.",
    )
    verify_ssl = fields.Boolean(default=True)
    timeout_seconds = fields.Integer(default=30)
    job_user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    access_token = fields.Char(
        groups="odoo_ecommerce_integration.group_ecommerce_manager",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("error", "Error"),
            ("disabled", "Disabled"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    last_test_at = fields.Datetime(readonly=True)
    last_test_error = fields.Char(readonly=True)
    capabilities = fields.Json(default=dict)
    notes = fields.Text()

    _code_uniq = models.UniqueIndex(
        "(company_id, code)",
        "Backend code must be unique per company.",
    )
    _timeout_check = models.Constraint(
        "CHECK (timeout_seconds >= 5 AND timeout_seconds <= 120)",
        "Backend timeout must be between 5 and 120 seconds.",
    )

    @api.constrains("company_id", "job_user_id")
    def _check_job_user_company(self):
        for backend in self:
            if backend.job_user_id and backend.company_id not in backend.job_user_id.company_ids:
                raise ValidationError("The job user must have access to the backend company.")
            if (
                backend.job_user_id
                and backend.job_user_id.id != 1
                and not backend.job_user_id.has_group(
                    "odoo_ecommerce_integration.group_ecommerce_operator"
                )
            ):
                raise ValidationError(
                    "The job user must have eCommerce Operator access."
                )

    @api.depends("provider")
    def _compute_provider_ui(self):
        for backend in self:
            backend.provider_ui = backend.provider or False

    def _inverse_provider_ui(self):
        for backend in self:
            if backend.provider_ui:
                backend.provider = backend.provider_ui

    @api.model
    def _ecommerce_provider_registry(self):
        """Return provider capabilities registered by installed connectors.

        Each entry is a dict with at least ``code`` and ``label``.
        Connector addons extend this method with ``super()``.
        """
        return []

    @api.model
    def _ecommerce_provider_selection(self):
        return [
            (item["code"], item["label"])
            for item in self._ecommerce_provider_registry()
            if item.get("code") and item.get("label")
        ]

    def _ecommerce_provider_definition(self):
        self.ensure_one()
        for item in self._ecommerce_provider_registry():
            if item.get("code") == self.provider:
                return item
        return {}

    def _ecommerce_capabilities(self):
        """Return the installed provider's supported capability codes."""
        self.ensure_one()
        definition = self._ecommerce_provider_definition()
        known = set(CAPABILITY_DEFINITIONS)
        return frozenset(
            code for code in definition.get("capabilities", []) if code in known
        )

    def _ecommerce_require_operator(self):
        if not self.env.is_superuser() and not self.env.user.has_group(
            "odoo_ecommerce_integration.group_ecommerce_operator"
        ):
            raise AccessError(
                "eCommerce Operator access is required for synchronization."
            )

    def write(self, vals):
        if "company_id" in vals:
            for backend in self:
                if (
                    vals["company_id"] != backend.company_id.id
                    and self.env["ecommerce.store"]
                    .sudo()
                    .search_count([("backend_id", "=", backend.id)])
                ):
                    raise UserError(
                        "The backend company cannot be changed while stores exist."
                    )
        return super().write(vals)

    def action_set_draft(self):
        self.write({"state": "draft", "last_test_error": False})
