from odoo import api, fields, models


class EcommerceSyncState(models.Model):
    _name = "ecommerce.sync.state"
    _description = "eCommerce Synchronization State"
    _order = "store_id, resource, direction"

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
    resource = fields.Selection(
        [
            ("product", "Product"),
            ("category", "Category"),
            ("customer", "Customer"),
            ("order", "Order"),
            ("invoice", "Invoice"),
            ("payment", "Payment"),
            ("inventory", "Inventory"),
            ("shipment", "Shipment"),
            ("refund", "Refund"),
            ("health", "Health"),
        ],
        required=True,
    )
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        required=True,
    )
    cursor_value = fields.Char()
    watermark = fields.Datetime()
    overlap_seconds = fields.Integer(default=300)
    last_started_at = fields.Datetime()
    last_success_at = fields.Datetime()
    last_completed_at = fields.Datetime()
    status = fields.Selection(
        [
            ("never", "Never"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="never",
        required=True,
        index=True,
    )
    last_error = fields.Char()
    metadata = fields.Json(default=dict)


    _sql_constraints = [
        ('state_uniq', 'UNIQUE (store_id, resource, direction)', 'Sync state must be unique per store, resource, and direction.'),
        ('overlap_check', 'CHECK (overlap_seconds >= 0)', 'Overlap cannot be negative.'),
    ]


class EcommerceSyncEvent(models.Model):
    _name = "ecommerce.sync.event"
    _description = "eCommerce Synchronization Event"
    _order = "occurred_at desc, id desc"

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
    event_type = fields.Char(required=True, index=True)
    severity = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        default="info",
        required=True,
        index=True,
    )
    source = fields.Char()
    entity_model = fields.Char()
    entity_id = fields.Char(index=True)
    external_reference = fields.Char()
    title = fields.Char(required=True)
    message = fields.Text()
    dedupe_key = fields.Char(index=True)
    details = fields.Json(default=dict)
    occurred_at = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )


    _sql_constraints = [
        ('dedupe_uniq', 'UNIQUE (dedupe_key)', 'Event dedupe key must be unique.'),
    ]


class EcommerceSyncIssue(models.Model):
    _name = "ecommerce.sync.issue"
    _description = "eCommerce Synchronization Issue"
    _order = "last_seen_at desc, id desc"

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
    issue_type = fields.Char(required=True, index=True)
    severity = fields.Selection(
        [
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ],
        default="error",
        required=True,
        index=True,
    )
    status = fields.Selection(
        [
            ("open", "Open"),
            ("resolved", "Resolved"),
            ("ignored", "Ignored"),
        ],
        default="open",
        required=True,
        index=True,
    )
    entity_model = fields.Char()
    entity_id = fields.Char(index=True)
    external_reference = fields.Char()
    title = fields.Char(required=True)
    summary = fields.Text(required=True)
    reason_code = fields.Char(required=True, index=True)
    fingerprint = fields.Char(required=True)
    occurrence_count = fields.Integer(default=1, required=True)
    first_seen_at = fields.Datetime(default=fields.Datetime.now, required=True)
    last_seen_at = fields.Datetime(default=fields.Datetime.now, required=True)
    resolved_at = fields.Datetime()
    resolution_note = fields.Text()
    last_event_id = fields.Many2one("ecommerce.sync.event", ondelete="set null")
    details = fields.Json(default=dict)


    @api.model
    def _record(
        self,
        *,
        store,
        issue_type,
        reason_code,
        title,
        summary,
        fingerprint,
        severity="error",
        entity_model=None,
        entity_id=None,
        external_reference=None,
        details=None,
    ):
        issue = self.search([("fingerprint", "=", fingerprint)], limit=1)
        values = {
            "store_id": store.id,
            "backend_id": store.backend_id.id,
            "issue_type": issue_type,
            "reason_code": reason_code,
            "title": title,
            "summary": summary,
            "severity": severity,
            "entity_model": entity_model,
            "entity_id": entity_id,
            "external_reference": external_reference,
            "details": details or {},
        }
        if issue:
            issue.write(
                {
                    **values,
                    "status": "open",
                    "occurrence_count": issue.occurrence_count + 1,
                    "last_seen_at": fields.Datetime.now(),
                    "resolved_at": False,
                }
            )
        else:
            issue = self.create(
                {
                    **values,
                    "fingerprint": fingerprint,
                    "first_seen_at": fields.Datetime.now(),
                    "last_seen_at": fields.Datetime.now(),
                }
            )
        return issue

    def action_resolve(self):
        self.write(
            {
                "status": "resolved",
                "resolved_at": fields.Datetime.now(),
            }
        )

    _sql_constraints = [
        ('fingerprint_uniq', 'UNIQUE (fingerprint)', 'Issue fingerprint must be unique.'),
    ]
