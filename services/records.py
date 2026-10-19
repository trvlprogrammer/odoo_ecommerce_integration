from odoo import fields


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
