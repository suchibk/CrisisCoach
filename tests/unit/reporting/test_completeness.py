from crisis_coach.domains.collision.pack import CollisionPack
from crisis_coach.models.evidence import EvidenceRecord, EvidenceStatus
from crisis_coach.reporting.completeness import calculate_completeness
from crisis_coach.tools.contracts import AttachmentReference


def test_reports_and_status_only_claims_do_not_count_as_stored():
    items = CollisionPack().catalogue.items[:3]
    records = {item.item_id: EvidenceRecord(item_id=item.item_id) for item in items}
    records[items[0].item_id].status = EvidenceStatus.REPORTED
    records[items[1].item_id].status = EvidenceStatus.COLLECTED
    result = calculate_completeness(items, records)
    assert result.stored_count == 0
    assert result.missing_count == 3
    assert result.reported_only_count == 1


def test_valid_reference_counts_once_and_integrity_problem_removes_credit():
    items = CollisionPack().catalogue.items[:1]
    ref = AttachmentReference(relative_path="x", sha256="a"*64, size_bytes=3, media_type="image/png")
    records = {items[0].item_id: EvidenceRecord(item_id=items[0].item_id, status=EvidenceStatus.COLLECTED, attachments=(ref, ref))}
    assert calculate_completeness(items, records).stored_count == 1
    assert calculate_completeness(items, records, {items[0].item_id: "missing file"}).stored_count == 0
    assert calculate_completeness((), {}).stored_percent == 0
