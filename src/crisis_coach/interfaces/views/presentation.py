"""Backend-derived UI data; no independent workflow rules."""
from ...models import SessionStatus


def ledger_rows(coach, scene):
    labels = {item.item_id:item.label for item in coach.pack.catalogue.items}
    applicable = {item.item_id for item in coach.pack.report_items(scene)}
    return [{"Item":labels.get(key,key), "Status":record.status.value,
        "Stored files":len(record.attachments), "Scope":"Current" if key in applicable else "Additional",
        "Note":record.note or "", "Estimated deadline":record.estimated_deadline.isoformat() if record.estimated_deadline else "Unknown"}
        for key,record in scene.evidence.items()]


def progress(coach, scene):
    records = [scene.evidence[item.item_id] for item in coach.pack.report_items(scene) if item.item_id in scene.evidence]
    return {"Stored":sum(bool(r.attachments) for r in records),
        "Reported only":sum(r.status.value == "reported" and not r.attachments for r in records),
        "Pending":sum(r.status.value == "pending" for r in records),
        "Unavailable / failed":sum(r.status.value in ("unavailable","failed") for r in records)}


def actionable(coach, scene):
    return scene.status is SessionStatus.ACTIVE and coach.pack.is_cleared(scene)
