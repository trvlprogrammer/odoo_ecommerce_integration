import logging

from odoo import SUPERUSER_ID, api, fields

_logger = logging.getLogger(__name__)


def record_event(
    env,
    store,
    event_type,
    *,
    severity="info",
    source=None,
    entity_model=None,
    entity_id=None,
    external_reference=None,
    title=None,
    message=None,
    dedupe_key=None,
    details=None,
):
    values = {
        "backend_id": store.backend_id.id,
        "store_id": store.id,
        "event_type": event_type,
        "severity": severity,
        "source": source,
        "entity_model": entity_model,
        "entity_id": entity_id,
        "external_reference": external_reference,
        "title": title or event_type,
        "message": message,
        "dedupe_key": dedupe_key,
        "details": details or {},
        "occurred_at": fields.Datetime.now(),
    }
    return env["ecommerce.sync.event"].create(values)


def record_issue(
    env,
    store,
    issue_type,
    reason_code,
    *,
    title=None,
    summary=None,
    fingerprint=None,
    severity="error",
    entity_model=None,
    entity_id=None,
    external_reference=None,
    details=None,
):
    fingerprint = fingerprint or (
        f"store:{store.id}|type:{issue_type}|entity:{entity_model}:{entity_id}|"
        f"reason:{reason_code}"
    )
    return env["ecommerce.sync.issue"]._record(
        store=store,
        issue_type=issue_type,
        reason_code=reason_code,
        title=title or issue_type,
        summary=summary or reason_code,
        fingerprint=fingerprint,
        severity=severity,
        entity_model=entity_model,
        entity_id=entity_id,
        external_reference=external_reference,
        details=details,
    )


def record_issue_durably(env, store, issue_type, reason_code, **kwargs):
    """Record an issue that must survive a rollback of the current transaction.

    queue_job rolls back the job transaction when a job fails permanently, so
    an issue written in the job cursor disappears with it. The issue is written
    and committed through a separate cursor. When the Store row is not visible
    from a new transaction (it was created in the still-open current one), the
    issue falls back to the current cursor, which is the previous behaviour.
    """
    try:
        with env.registry.cursor() as cr:
            # The current transaction may hold a lock on the same issue row.
            cr.execute("SET LOCAL lock_timeout = '2s'")
            durable_env = api.Environment(cr, SUPERUSER_ID, {})
            durable_store = durable_env["ecommerce.store"].browse(store.id).exists()
            if durable_store:
                record_issue(durable_env, durable_store, issue_type, reason_code, **kwargs)
                return True
    except Exception:  # pragma: no cover - logged, then the current cursor is used
        _logger.exception("Durable issue recording failed for store %s", store.id)
    record_issue(env, store.sudo(), issue_type, reason_code, **kwargs)
    return False


def resolve_issue(env, fingerprint, note=None):
    issue = env["ecommerce.sync.issue"].search([("fingerprint", "=", fingerprint)], limit=1)
    if issue:
        issue.write(
            {
                "status": "resolved",
                "resolved_at": fields.Datetime.now(),
                "resolution_note": note,
            }
        )
    return issue
