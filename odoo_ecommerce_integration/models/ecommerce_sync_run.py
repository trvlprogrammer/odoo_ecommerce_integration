import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EcommerceSyncRun(models.Model):
    _name = "ecommerce.sync.run"
    _description = "eCommerce Synchronization Run"
    _order = "started_at desc, id desc"

    store_id = fields.Many2one(
        "ecommerce.store", required=True, ondelete="restrict", index=True
    )
    backend_id = fields.Many2one(
        "ecommerce.backend", required=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(
        "res.company",
        related="store_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    provider = fields.Char(related="backend_id.provider", store=True, readonly=True)
    operation = fields.Char(required=True, index=True)
    resource = fields.Char(required=True, index=True)
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("running", "Running"),
            ("done", "Done"),
            ("partial", "Partially Failed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="queued",
        required=True,
        index=True,
    )
    total = fields.Integer(default=0)
    queued = fields.Integer(default=0)
    processed = fields.Integer(default=0)
    succeeded = fields.Integer(default=0)
    failed = fields.Integer(default=0)
    skipped = fields.Integer(default=0)
    started_at = fields.Datetime(default=fields.Datetime.now, required=True)
    finished_at = fields.Datetime()
    last_error = fields.Char()
    cursor_value = fields.Char()
    advance_cursor_on_partial = fields.Boolean(default=False)
    sync_state_id = fields.Many2one(
        "ecommerce.sync.state", ondelete="set null", index=True
    )
    details = fields.Json(default=dict)

    _run_idx = models.Index("(store_id, state, started_at)")
    _company_idx = models.Index("(company_id, started_at)")

    @api.model
    def create_for_store(
        self,
        store,
        resource,
        operation,
        *,
        total=0,
        queued=0,
        sync_state=None,
        cursor_value=None,
        advance_cursor_on_partial=False,
    ):
        return self.create(
            {
                "store_id": store.id,
                "backend_id": store.backend_id.id,
                "resource": resource,
                "operation": operation,
                "total": total,
                "queued": queued,
                "sync_state_id": sync_state.id if sync_state else False,
                "cursor_value": cursor_value,
                "advance_cursor_on_partial": advance_cursor_on_partial,
            }
        )

    def _record_batch(
        self,
        key,
        *,
        succeeded=0,
        failed=0,
        skipped=0,
        error=None,
    ):
        """Record one bounded child batch exactly once.

        Child jobs may be retried by queue_job. The (run, key) unique batch
        identity makes progress accounting idempotent.
        """
        self.ensure_one()
        Batch = self.env["ecommerce.sync.batch"]
        batch = Batch.search(
            [("run_id", "=", self.id), ("key", "=", str(key))], limit=1
        )
        if batch:
            return batch
        batch = Batch.create(
            {
                "run_id": self.id,
                "key": str(key),
                "succeeded": succeeded,
                "failed": failed,
                "skipped": skipped,
                "error": (error or "")[:500] or False,
                "state": "partial" if failed else "done",
                "processed_at": fields.Datetime.now(),
            }
        )
        processed = succeeded + failed + skipped
        self.env.cr.execute(
            """
            UPDATE ecommerce_sync_run
               SET processed = processed + %s,
                   succeeded = succeeded + %s,
                   failed = failed + %s,
                   skipped = skipped + %s,
                   state = CASE WHEN state = 'queued' THEN 'running' ELSE state END,
                   last_error = COALESCE(%s, last_error)
             WHERE id = %s
            """,
            (processed, succeeded, failed, skipped, error, self.id),
        )
        self.invalidate_recordset()
        self.env["ecommerce.sync.run"].invalidate_model()
        run = self.browse(self.id)
        if run.total and run.processed >= run.total:
            run._finish()
        return batch

    def _finish(self, *, state=None):
        self.ensure_one()
        run = self.browse(self.id)
        if run.state in ("done", "partial", "failed", "cancelled"):
            return
        if state is None:
            state = "partial" if run.failed else "done"
        values = {
            "state": state,
            "finished_at": fields.Datetime.now(),
        }
        run.write(values)
        if run.sync_state_id:
            sync_values = {
                "last_completed_at": fields.Datetime.now(),
                "status": "failed" if state == "failed" else "success",
            }
            if state == "done":
                sync_values["last_success_at"] = fields.Datetime.now()
            if run.cursor_value and (
                state == "done"
                or (state == "partial" and run.advance_cursor_on_partial)
            ):
                sync_values["cursor_value"] = run.cursor_value
            run.sync_state_id.write(sync_values)

    def action_cancel(self):
        for run in self:
            if run.state in ("queued", "running"):
                run.write({"state": "cancelled", "finished_at": fields.Datetime.now()})
        return True


class EcommerceSyncBatch(models.Model):
    _name = "ecommerce.sync.batch"
    _description = "eCommerce Synchronization Batch"
    _order = "run_id, id"

    run_id = fields.Many2one(
        "ecommerce.sync.run", required=True, ondelete="cascade", index=True
    )
    key = fields.Char(required=True, index=True)
    state = fields.Selection(
        [("done", "Done"), ("partial", "Partial"), ("failed", "Failed")],
        default="done",
        required=True,
        index=True,
    )
    succeeded = fields.Integer(default=0)
    failed = fields.Integer(default=0)
    skipped = fields.Integer(default=0)
    error = fields.Text()
    processed_at = fields.Datetime(default=fields.Datetime.now)

    _run_key_uniq = models.UniqueIndex(
        "(run_id, key)", "A batch key must be unique within a synchronization run."
    )
