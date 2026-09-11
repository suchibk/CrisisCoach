"""Conservative text adapters for explicit scene facts and collection reports."""
import re
from datetime import datetime, timedelta
from typing import Literal
from pydantic import BaseModel, ConfigDict
from ...models.evidence import EvidenceCatalogue, EvidenceRecord, EvidenceStatus

class CollisionFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    scenario: Literal["full", "unattended", "scuff"] = "full"
    driver_present: bool = True
    witness_present: bool = False


def apply_scene_changes(state, catalogue: EvidenceCatalogue, text: str, now: datetime) -> None:
    if state.evidence_catalogue_version not in (None, catalogue.version):
        raise ValueError("Incident evidence catalogue version is unsupported")
    state.evidence_catalogue_version = catalogue.version
    facts = CollisionFacts.model_validate(state.domain_data)
    normalized = text.lower().replace("’", "'")
    if normalized.strip().startswith(("/collected ", "/unavailable ", "/failed ")):
        normalized = ""  # Evidence content is not a scene-control command.
    if any(phrase in normalized for phrase in ("came back to", "returned to my parked", "nobody there", "/scenario unattended")):
        facts.scenario = "unattended"
        facts.driver_present = False
    elif any(phrase in normalized for phrase in ("bollard", "just a scuff", "/scenario scuff")):
        facts.scenario = "scuff"
        facts.driver_present = False
    elif normalized.strip() == "/scenario full":
        facts.scenario = "full"
        facts.driver_present = True
    witness_leaving = bool(re.search(r"(?:witness|woman|man).*(?:leaving|walking (?:off|away)|about to leave)", normalized))
    if witness_leaving or "there's a witness" in normalized or "there is a witness" in normalized:
        facts.witness_present = True
    for item in catalogue.items:
        state.evidence.setdefault(item.item_id, EvidenceRecord(item_id=item.item_id))
    if witness_leaving:
        record = state.evidence["witness_details"]
        if record.estimated_deadline is None:
            record.estimated_deadline = now + timedelta(seconds=60)
    if any(phrase in normalized for phrase in ("getting back in", "getting back into", "driver is leaving", "what if he drives off")):
        for item_id in ("other_plate", "other_insurance", "other_vehicle"):
            record = state.evidence[item_id]
            if record.estimated_deadline is None:
                record.estimated_deadline = now + timedelta(seconds=60)
    if any(phrase in normalized for phrase in ("he drove off", "driver has left", "driver drove away")):
        facts.driver_present = False
        for item in catalogue.items:
            if item.requires_driver and state.evidence[item.item_id].status is EvidenceStatus.PENDING:
                state.evidence[item.item_id].status = EvidenceStatus.UNAVAILABLE
                state.evidence[item.item_id].note = "User reported that the driver left"
    if any(phrase in normalized for phrase in ("witness has left", "witness walked away")):
        facts.witness_present = True
        record = state.evidence["witness_details"]
        if record.status is EvidenceStatus.PENDING:
            record.status = EvidenceStatus.UNAVAILABLE
            record.note = "User reported that the witness left"
    if facts.scenario == "unattended":
        record = state.evidence["footage_reference"]
        if record.estimated_deadline is None:
            record.estimated_deadline = now + timedelta(seconds=120)
    state.domain_data = facts.model_dump(mode="json")


def applicable_items(state, catalogue: EvidenceCatalogue):
    facts = CollisionFacts.model_validate(state.domain_data)
    # Keep unavailable driver items in the full-scene gap report after departure.
    return tuple(item for item in catalogue.items if facts.scenario in item.scenarios
                 and (not item.requires_witness or facts.witness_present))


def record_report(state, catalogue: EvidenceCatalogue, text: str) -> str | None:
    normalized = text.strip().lower()
    target = state.current_evidence_id
    note = text.strip()
    status = EvidenceStatus.REPORTED
    if normalized.startswith(("/unavailable ", "/failed ")):
        parts = text.split(maxsplit=2)
        if len(parts) < 3: return "Use /unavailable followed by the item ID and a reason."
        target, note = parts[1], parts[2]
        status = EvidenceStatus.FAILED if normalized.startswith("/failed ") else EvidenceStatus.UNAVAILABLE
    elif normalized.startswith("/collected "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3: return "Use /collected followed by the item ID and what you recorded."
        target, note = parts[1], parts[2]
    elif normalized not in ("done", "photo taken", "got it"):
        return None
    if target not in {item.item_id for item in applicable_items(state, catalogue)}:
        return "That evidence item is not applicable to this incident."
    item = next(item for item in catalogue.items if item.item_id == target)
    if item.expects == "text" and normalized in ("done", "photo taken", "got it"):
        return f"Record the details using /collected {target} followed by your text."
    state.evidence[target].status = status
    state.evidence[target].note = note
    return None
