from __future__ import annotations

from uuid import uuid4

from ..models import Instruction, SceneState, SessionStatus
from ..models.events import Control, ControlEvent, TextEvent, TimerEvent, CaptureEvent, ReportEvent, QuestionEvent, ContextEvent, IncidentContextEvent, AIConsentEvent, InputEvent, INPUT_EVENT_ADAPTER
from ..tools.executor import ToolExecutor
from ..tools.contracts import ToolContext, ToolError
from ..models.evidence import EvidenceStatus
from .clock import Clock, MonotonicClock
from ..domains.contracts import DomainPack
from .graph import TurnGraph
from ..persistence.contracts import IncidentRepository, PersistenceError


class WorkflowEngine:
    """Shared lifecycle and transactional graph execution for a registered domain."""

    def __init__(self, pack: DomainPack, clock: Clock | None = None, repository: IncidentRepository | None = None, backend: str = "local", executor: ToolExecutor | None = None, photo_reviewer=None, attachment_store=None) -> None:
        self.pack = pack
        self.executor = executor
        self.photo_reviewer = photo_reviewer
        self.attachment_store = attachment_store
        self._clock = clock or MonotonicClock()
        self._repository = repository
        self._graph = TurnGraph(self, backend=backend)
        self.last_route: tuple[str, ...] = ()

    def start(self, person_name: str = "Dana Okoye", profile=None, practice: bool = False) -> tuple[SceneState, Instruction]:
        state = SceneState(incident_id=str(uuid4()), person_name=person_name, profile=profile, practice_mode=practice, domain_id=self.pack.metadata.domain_id, pack_version=self.pack.metadata.version)
        state.events.append("SCENE_OPENED")
        reply = self._publish(state, self.pack.opening(state))
        if self._repository is not None:
            self._repository.save(state, response=reply)
        return state, reply

    def reopen(self, incident_id: str) -> tuple[SceneState, Instruction]:
        if self._repository is None:
            raise PersistenceError("Reopening requires an incident repository")
        state = self._repository.load(incident_id)
        state.ai_text_allowed = False
        state.ai_images_allowed = False
        state.pending_scene_changes = ()
        state.timer_id = None
        state.timer_deadline = None
        state.events.append("INCIDENT_REOPENED")
        self._check_domain(state)
        reply = self.pack.recovery(state)
        if state.status is not SessionStatus.STOPPED:
            self._publish(state, reply)
        self._repository.save(state, response=reply)
        return state, reply

    def turn(self, state: SceneState, user_text: str) -> Instruction:
        parts = user_text.split(maxsplit=2)
        if len(parts) == 3 and parts[0] in ("/attach", "/statement"):
            event = CaptureEvent(item_id=parts[1], tool="capture_photo" if parts[0] == "/attach" else "record_statement",
                                 arguments={"source_path" if parts[0] == "/attach" else "text": parts[2]})
        elif user_text.strip().lower() in ("/ai-text on", "/ai-text off", "/ai-images on", "/ai-images off"):
            command, value = user_text.strip().lower().split()
            event = AIConsentEvent(capability="text" if command == "/ai-text" else "images", allowed=value == "on")
        elif user_text.strip().startswith("/context "):
            from ..models.incident_context import IncidentContext
            from pydantic import ValidationError
            try:
                event = IncidentContextEvent(context=IncidentContext.model_validate_json(user_text.strip()[9:]))
            except ValidationError:
                # Invalid commands still pass through the safety guard.
                event = TextEvent(text=user_text)
        elif user_text.strip().lower() == "/knowledge-demo":
            from datetime import date
            from ..models.knowledge import KnowledgeContext
            event = ContextEvent(context=KnowledgeContext(policy_id="demo-meridian", jurisdiction="DEMO", reference_date=date(2026, 9, 8), allow_synthetic=True))
        elif user_text.strip().lower().startswith("/ask "):
            event = QuestionEvent(question=user_text.strip()[5:])
        elif user_text.strip().endswith("?") and any(word in user_text.lower() for word in ("policy", "police", "excess", "report", "insurance", "insurer", "notify", "notification", "deductible", "exchange", "legal", "fault", "liability", "claim")):
            event = QuestionEvent(question=user_text)
        elif user_text.strip().lower() == "/export":
            event = ReportEvent()
        else:
            event = TextEvent(text=user_text)
        response = self.handle_event(state, event)
        assert response is not None
        return response

    def _publish(self, state: SceneState, reply: Instruction) -> Instruction:
        state.last_instruction = reply
        state.timer_id = None
        state.timer_deadline = None
        if state.status is SessionStatus.ACTIVE and not reply.terminate:
            state.timer_id = str(uuid4())
            delay = 30 if self.pack.is_cleared(state) else 8
            state.timer_deadline = self._clock.now() + delay
        return reply

    def seconds_until_timer(self, state: SceneState) -> float | None:
        if state.timer_deadline is None:
            return None
        return max(0.0, state.timer_deadline - self._clock.now())

    def poll(self, state: SceneState) -> Instruction | None:
        if state.timer_id is None or self.seconds_until_timer(state) != 0:
            return None
        return self.handle_event(state, TimerEvent(timer_id=state.timer_id))

    def handle_event(self, state: SceneState, event: InputEvent) -> Instruction | None:
        event = INPUT_EVENT_ADAPTER.validate_python(event)
        self._check_domain(state)
        if (isinstance(event, ReportEvent) or (isinstance(event, CaptureEvent) and event.tool == "capture_photo")) and self._repository is not None:
            if self._repository.has_event(state.incident_id, event.event_id):
                return None
            if self._repository.load(state.incident_id).revision != state.revision:
                raise PersistenceError("Incident changed; reopen before capturing evidence")
        working = state.model_copy(deep=True)
        # Process safety first, even if storage is unavailable.
        result = self._graph.invoke(working, event)
        working = result.scene
        response = result.response
        self.last_route = result.route
        if working.model_dump() == state.model_dump():
            return response
        working.events.append("GRAPH_ROUTE: " + " -> ".join(self.last_route))
        from ..models.trace import TurnTrace
        entry = TurnTrace(event_id=event.event_id, event_kind=event.kind, route=self.last_route,
            status=working.status.value, gate=str(working.safety_gate),
            selected_id=working.current_evidence_id if working.status is SessionStatus.ACTIVE and self.pack.is_cleared(working) else None,
            response=response.text if response else None)
        working.trace = (*working.trace[-99:], entry)
        if self._repository is not None:
            try:
                if self._repository.has_event(state.incident_id, event.event_id):
                    return None
                self._repository.save(working, event=event, response=response)
            except PersistenceError:
                if working.status is not SessionStatus.STOOD_DOWN or response is None or not response.terminate:
                    raise
                response = Instruction(text=response.text + " This update could not be saved.", terminate=True, reason=response.reason)
                working.last_instruction = response
        # Commit in-memory state only after the durable transaction succeeds.
        for name in type(state).model_fields:
            setattr(state, name, getattr(working, name))
        return response

    def _controls(self, state: SceneState, event: InputEvent) -> Instruction | None:
        event = INPUT_EVENT_ADAPTER.validate_python(event)
        if event.event_id == state.last_event_id:
            return None
        if isinstance(event, TimerEvent):
            if event.timer_id != state.timer_id or self.seconds_until_timer(state) != 0:
                return None
            state.last_event_id = event.event_id
            if state.status is not SessionStatus.ACTIVE:
                return None
            state.events.append("TIMER_EXPIRED")
            if self.pack.is_cleared(state):
                current = state.last_instruction
                reminder = Instruction(text="Still with me? Take your time. " + (current.text if current else ""), expects="photo")
                self._publish(state, reminder)
                state.last_instruction = current
                return reminder
            current = state.last_instruction
            reply = self._publish(state, self.pack.silence(state))
            if state.status is SessionStatus.STOPPED:
                state.last_instruction = current
            return reply

        state.last_event_id = event.event_id
        control = event.control if isinstance(event, ControlEvent) else None
        if isinstance(event, TextEvent):
            # Exact control phrases only: mixed text still passes through safety.
            commands = {"stop": Control.PAUSE, "pause": Control.PAUSE,
                        "hold on. stop.": Control.PAUSE, "leave me alone": Control.PAUSE,
                        "go on": Control.RESUME, "resume": Control.RESUME,
                        "repeat": Control.REPEAT, "say that again": Control.REPEAT,
                        "slow down": Control.SLOW_DOWN}
            control = commands.get(event.text.lower().strip())

        if control is not None and state.status is not SessionStatus.STOOD_DOWN:
            state.events.append(f"CONTROL: {control.value}")
            if control is Control.PAUSE:
                state.status = SessionStatus.STOPPED
                state.timer_id = None
                state.timer_deadline = None
                return Instruction(text="Stopped. Say go on whenever you're ready.")
            if control is Control.RESUME and state.status is SessionStatus.STOPPED:
                state.status = SessionStatus.ACTIVE
                return self._publish(state, state.last_instruction or self.pack.opening(state))
            if state.status is SessionStatus.STOPPED:
                return Instruction(text="Paused. Say go on whenever you're ready.")
            if state.last_instruction is not None:
                reply = state.last_instruction
                if control is Control.SLOW_DOWN:
                    reply = Instruction(**{**reply.model_dump(), "speech_rate": 0.75})
                    state.last_instruction = reply
                # Repeats do not extend the safety deadline or advance the gate.
                return reply

        if state.status is SessionStatus.STOPPED:
            reply = self.pack.paused(state, event.text if isinstance(event, TextEvent) else (event.question if isinstance(event, QuestionEvent) else (event.arguments.get("text", "") if isinstance(event, CaptureEvent) else "")))
            return self._publish(state, reply) if reply.terminate else reply
        return None

    def _check_domain(self, state: SceneState) -> None:
        if state.domain_id != self.pack.metadata.domain_id or state.pack_version != self.pack.metadata.version:
            raise ValueError("Incident domain or pack version does not match this workflow")

    def capture(self, state: SceneState, event: CaptureEvent) -> Instruction | None:
        if state.status is not SessionStatus.ACTIVE or not self.pack.is_cleared(state):
            return Instruction(text="Finish the safety check before recording evidence.")
        authorize = getattr(self.pack, "capture_tool", None)
        if authorize is None or authorize(state, event.item_id) != event.tool:
            return Instruction(text="That capture does not match an applicable evidence item.")
        if self.executor is None:
            return Instruction(text="Local capture is not configured for this workflow.")
        try:
            result = self.executor.execute(event.tool, event.arguments,
                ToolContext(incident_id=state.incident_id, event_id=event.event_id))
        except ToolError as exc:
            state.events.append(f"TOOL_FAILED: {event.tool}")
            return Instruction(text=str(exc))
        record = state.evidence[event.item_id]
        if result.attachment not in record.attachments:
            record.attachments = record.attachments + (result.attachment,)
        record.status = EvidenceStatus.COLLECTED
        record.original_text = result.original_text
        record.note = "Stored locally; image quality has not been verified" if event.tool == "capture_photo" else "Original text stored verbatim"
        state.events.append(f"TOOL_COMPLETED: {event.tool}: {event.item_id}")
        if event.tool == "capture_photo":
            return self.review_photo(state, event.item_id, result.attachment)
        return None

    def export_pack(self, state: SceneState, event: ReportEvent) -> Instruction:
        if state.status is not SessionStatus.ACTIVE or not self.pack.is_cleared(state):
            return Instruction(text="Finish the safety check before building the evidence pack.")
        items = getattr(self.pack, "report_items", None)
        if self.executor is None or items is None:
            return Instruction(text="Evidence pack export is not configured.")
        from ..models.reports import EvidencePackReference
        try:
            result = EvidencePackReference.model_validate(self.executor.execute("build_evidence_pack",
                {"scene": state.model_dump(), "items": items(state)},
                ToolContext(incident_id=state.incident_id, event_id=event.event_id)))
        except ToolError as exc:
            return Instruction(text=str(exc))
        state.exports = state.exports + (result,)
        state.events.append("TOOL_COMPLETED: build_evidence_pack")
        return Instruction(text=f"Evidence pack saved locally. Stored items: {result.stored_items}/{result.required_items}. Review the gaps before sharing.", reason=result.relative_path)

    def answer_question(self, state: SceneState, event: QuestionEvent | ContextEvent | IncidentContextEvent) -> Instruction:
        from ..models.knowledge import KnowledgeAnswer, KnowledgeQuery
        if isinstance(event, IncidentContextEvent):
            state.incident_context = event.context
            return Instruction(text="Incident details saved as user-provided observations. Blank fields remain unknown.")
        if isinstance(event, ContextEvent):
            state.knowledge_context = event.context
            label = "SYNTHETIC DEMO sources enabled; these are not real policy or legal requirements." if event.context.allow_synthetic else "Source context updated. Only matching reviewed local passages will be used."
            return Instruction(text=label)
        question = event.question
        normalized = question.lower()
        if any(term in normalized for term in ("whose fault", "at fault", "liability", "should i claim", "should i make a claim", "medical advice")):
            answer = KnowledgeAnswer(question=question, status="refused", message="I cannot determine fault, liability, or whether you should claim. I can show matching policy or duty passages.")
        else:
            topic = None
            corpus = "policy"
            if any(term in normalized for term in ("excess", "deductible")): topic = "excess"
            elif any(term in normalized for term in ("notify", "notification", "report", "deadline")): topic = "notification"
            if "police" in normalized: corpus, topic = "duties", "police"
            elif any(term in normalized for term in ("exchange", "swap details")): corpus, topic = "duties", "exchange"
            if topic is None or self.executor is None:
                answer = KnowledgeAnswer(question=question, status="not_found", message="No supported local lookup is available for that question. I cannot establish the requirement.")
            else:
                query = KnowledgeQuery(question=question, corpus=corpus, topic=topic, context=state.knowledge_context)
                try:
                    answer = KnowledgeAnswer.model_validate(self.executor.execute("check_policy" if corpus == "policy" else "assess_duties", query.model_dump(), ToolContext(incident_id=state.incident_id, event_id=event.event_id)))
                except ToolError:
                    answer = KnowledgeAnswer(question=question, status="not_found", message="The local source lookup failed. No requirement has been established.")
        state.knowledge_answers = state.knowledge_answers + (answer,)
        text = answer.message
        for citation in answer.citations:
            label = "SYNTHETIC DEMO — " if citation.synthetic else ""
            text += f"\n\n{label}{citation.title}, section {citation.section} [{citation.source_id}]\n{citation.text}\nSource: {citation.source_uri} (effective {citation.effective_from} to {citation.effective_until or 'unspecified'})"
        return Instruction(text=text, citations=answer.citations)

    def review_photo(self, state, item_id, attachment):
        from ..models.ai import PhotoAssessment
        if not state.ai_images_allowed or self.photo_reviewer is None or self.attachment_store is None:
            return None
        record = state.evidence[item_id]
        assessment = record.photo_reviews.get(attachment.sha256)
        if assessment is None:
            if record.failed_photo_reviews >= 2:
                record.note = "Stored without another AI review after two unsuccessful captures"
                return None
            try:
                goal = getattr(self.pack, "photo_goal", lambda s, i: i)(state, item_id)
                data = self.attachment_store.read(state.incident_id, attachment)
                assessment = PhotoAssessment.model_validate(self.photo_reviewer.review(data, attachment.media_type, goal))
                record.photo_reviews[attachment.sha256] = assessment
                if assessment.verdict == "retake":
                    record.failed_photo_reviews += 1
            except Exception as exc:
                state.events.append(f"AI_PHOTO_FAILED: {type(exc).__name__}")
                record.note = "Stored locally; AI quality review unavailable"
                return None
        state.events.append(f"AI_PHOTO_ASSESSMENT: {item_id}: {assessment.verdict}")
        if any(review.verdict == "usable" for review in record.photo_reviews.values()):
            record.status = EvidenceStatus.VERIFIED
            record.note = "AI assessed image usability only; no human, identity, fault, or claim verification"
        elif assessment.verdict == "retake":
            record.note = "AI quality issues: " + ", ".join(assessment.issues)
            if record.failed_photo_reviews >= 2:
                record.status = EvidenceStatus.FAILED
                record.note += "; originals retained after two unsuccessful captures"
                return None
            record.status = EvidenceStatus.PENDING
            state.current_evidence_id = item_id
            descriptions = {"blur":"The image is blurred.", "dark":"The image is too dark.", "occluded":"The subject is obscured.", "wrong_subject":"The requested subject is missing.", "unreadable":"The requested detail is unreadable."}
            return Instruction(text=descriptions[assessment.issues[0]] + " Retake it only from a safe position.", expects="photo")
        else:
            record.note = "Stored locally; AI could not establish image usability"
        return None

    def set_ai_consent(self, state, event):
        specialist = getattr(self.pack, "interpreter", None) if event.capability == "text" else self.photo_reviewer
        if event.allowed and specialist is None:
            return Instruction(text=f"AI {event.capability} support is not configured. Local operation remains available.")
        if event.capability == "text":
            state.ai_text_allowed = event.allowed
            if not event.allowed: state.pending_scene_changes = ()
        else:
            state.ai_images_allowed = event.allowed
        state.events.append(f"AI_CONSENT: {event.capability}: {event.allowed}")
        return Instruction(text=(f"Permission recorded to send {event.capability} to {getattr(specialist, 'provider_label', 'the configured AI provider')} for this session. Provider charges may apply." if event.allowed else f"AI {event.capability} sharing is disabled."))
