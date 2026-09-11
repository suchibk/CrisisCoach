"""One explicit node/edge definition shared by local and LangGraph runners."""
from typing import TYPE_CHECKING
from pydantic import BaseModel, ConfigDict
from ..models import SceneState, Instruction, SessionStatus
from ..models.events import InputEvent, TextEvent, TimerEvent, CaptureEvent, ReportEvent, QuestionEvent, ContextEvent, IncidentContextEvent, AIConsentEvent

if TYPE_CHECKING:
    from .engine import WorkflowEngine

class TurnState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene: SceneState
    event: InputEvent
    response: Instruction | None = None
    handled: bool = False
    route: tuple[str, ...] = ()

class TurnGraph:
    def __init__(self, engine: "WorkflowEngine", backend: str = "local"):
        if backend not in ("local", "langgraph"):
            raise ValueError("Unknown graph backend")
        self.engine = engine
        self.nodes = {"safety": self.safety, "controls": self.controls,
                      "gate": self.gate, "capture": self.capture, "report": self.report, "answer": self.answer, "consent": self.consent, "plan": self.plan}
        self.compiled = None
        if backend == "langgraph":
            try:
                from langgraph.graph import StateGraph, START, END
            except ImportError as exc:
                raise RuntimeError('LangGraph support requires pip install -e ".[agent]"') from exc
            graph = StateGraph(TurnState)
            for name, node in self.nodes.items():
                graph.add_node(name, node)
            graph.add_edge(START, "safety")
            for name in self.nodes:
                graph.add_conditional_edges(name, self.next_node, {**{key:key for key in self.nodes}, "end": END})
            self.compiled = graph.compile()

    @staticmethod
    def next_node(state: TurnState) -> str:
        if state.handled:
            return "end"
        if state.route[-1] == "gate" and isinstance(state.event, AIConsentEvent):
            return "consent"
        if state.route[-1] == "gate" and isinstance(state.event, (QuestionEvent, ContextEvent, IncidentContextEvent)):
            return "answer"
        if state.route[-1] == "gate" and isinstance(state.event, ReportEvent):
            return "report"
        if state.route[-1] == "gate" and isinstance(state.event, CaptureEvent):
            return "capture"
        return {"capture": "plan", "safety": "controls", "controls": "gate", "gate": "plan", "plan": "end"}[state.route[-1]]

    def update(self, state: TurnState, name: str, response=None, handled=False):
        return {"scene": state.scene, "response": response, "handled": handled, "route": state.route + (name,)}

    def safety(self, state: TurnState):
        text = state.event.text if isinstance(state.event, TextEvent) else (state.event.question if isinstance(state.event, QuestionEvent) else (state.event.arguments.get("text", "") if isinstance(state.event, CaptureEvent) else ""))
        if isinstance(state.event, IncidentContextEvent):
            text = state.event.context.safety_text()
        reply = self.engine.pack.preempt(state.scene, text) if text else None
        if reply is not None:
            state.scene.last_event_id = state.event.event_id
            self.engine._publish(state.scene, reply)
        return self.update(state, "safety", reply, reply is not None)

    def controls(self, state: TurnState):
        if state.scene.status is SessionStatus.COMPLETE:
            return self.update(state, "controls", Instruction(text="This incident is complete.", terminate=True), True)
        reply = self.engine._controls(state.scene, state.event)
        handled = reply is not None or isinstance(state.event, TimerEvent) or state.event.event_id != state.scene.last_event_id
        return self.update(state, "controls", reply, handled)

    def gate(self, state: TurnState):
        if self.engine.pack.metadata.domain_id == "collision" and isinstance(state.event, TextEvent) and state.scene.status is SessionStatus.ACTIVE and self.engine.pack.is_cleared(state.scene):
            import re
            if re.search(r"\b(?:sorry|my fault|apologise|apologize)\b", state.event.text, re.I):
                check = getattr(self.engine.pack, "capture_safety", self.engine.pack.guard)
                reply = check(state.scene, state.event.text)
                if reply is not None:
                    self.engine._publish(state.scene, reply)
                    return self.update(state, "gate", reply, True)
                state.scene.events.append("USER: " + state.event.text)
                return self.update(state, "gate", Instruction(text="You can describe what you observed in your own words. I cannot determine fault or the legal effect of an apology. Your current collection task is unchanged."), True)
        if isinstance(state.event, (QuestionEvent, ContextEvent, IncidentContextEvent, AIConsentEvent)) and state.scene.status is SessionStatus.ACTIVE and self.engine.pack.is_cleared(state.scene):
            text = state.event.question if isinstance(state.event, QuestionEvent) else ""
            if isinstance(state.event, IncidentContextEvent):
                text = state.event.context.safety_text()
            check = getattr(self.engine.pack, "capture_safety", self.engine.pack.guard)
            reply = check(state.scene, text) if text else None
            if reply is not None: self.engine._publish(state.scene, reply)
            return self.update(state, "gate", reply, reply is not None)
        if isinstance(state.event, ReportEvent) and state.scene.status is SessionStatus.ACTIVE and self.engine.pack.is_cleared(state.scene):
            return self.update(state, "gate")
        if isinstance(state.event, CaptureEvent) and state.scene.status is SessionStatus.ACTIVE and self.engine.pack.is_cleared(state.scene):
            # Scan submitted statement text for additional injury signals before capture.
            text = state.event.arguments.get("text", "")
            check = getattr(self.engine.pack, "capture_safety", self.engine.pack.guard)
            reply = check(state.scene, text) if text else None
            if reply is not None:
                self.engine._publish(state.scene, reply)
            return self.update(state, "gate", reply, reply is not None)
        text = state.event.text if isinstance(state.event, TextEvent) else (state.event.question if isinstance(state.event, QuestionEvent) else "")
        state.scene.events.append(f"USER: {text}")
        reply = self.engine.pack.guard(state.scene, text)
        if reply is not None:
            self.engine._publish(state.scene, reply)
        return self.update(state, "gate", reply, reply is not None)

    def capture(self, state: TurnState):
        reply = self.engine.capture(state.scene, state.event)
        if reply is not None:
            self.engine._publish(state.scene, reply)
        return self.update(state, "capture", reply, reply is not None)

    def consent(self, state: TurnState):
        return self.update(state, "consent", self.engine.set_ai_consent(state.scene, state.event), True)

    def answer(self, state: TurnState):
        reply = self.engine.answer_question(state.scene, state.event)
        # Preserve the current collection task and its deadline during a question.
        return self.update(state, "answer", reply, True)

    def report(self, state: TurnState):
        reply = self.engine.export_pack(state.scene, state.event)
        # Reporting does not replace the collection instruction or reset its timer.
        return self.update(state, "report", reply, True)

    def plan(self, state: TurnState):
        reply = self.engine.pack.next_instruction(state.scene)
        self.engine._publish(state.scene, reply)
        return self.update(state, "plan", reply, True)

    def invoke(self, scene: SceneState, event: InputEvent) -> TurnState:
        state = TurnState(scene=scene, event=event)
        # Immediate duplicate input must not be reinterpreted as a new answer.
        if event.event_id == scene.last_event_id:
            return state
        if self.compiled is not None:
            return TurnState.model_validate(self.compiled.invoke({"scene": scene, "event": event}))
        node = "safety"
        while node != "end":
            state = TurnState.model_validate({**state.__dict__, **self.nodes[node](state)})
            node = self.next_node(state)
        return state
