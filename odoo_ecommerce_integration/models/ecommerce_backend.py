from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .ecommerce_provider import CAPABILITY_DEFINITIONS


class EcommerceBackend(models.Model):
    _name = "ecommerce.backend"
    _description = "eCommerce Backend"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    provider = fields.Char(required=True)
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


    @api.constrains("company_id", "job_user_id")
    def _check_job_user_company(self):
        for backend in self:
            if backend.job_user_id and backend.company_id not in backend.job_user_id.company_ids:
                raise ValidationError("The job user must have access to the backend company.")

    @api.model
    def _ecommerce_provider_registry(self):
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

    def action_set_draft(self):
        self.write({"state": "draft", "last_test_error": False})

    _sql_constraints = [
        ('code_uniq', 'UNIQUE (company_id, code)', 'Backend code must be unique per company.'),
        ('timeout_check', 'CHECK (timeout_seconds >= 5 AND timeout_seconds <= 120)', 'Backend timeout must be between 5 and 120 seconds.'),
    ]
