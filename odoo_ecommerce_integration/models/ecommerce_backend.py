from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    def action_set_draft(self):
        self.write({"state": "draft", "last_test_error": False})
