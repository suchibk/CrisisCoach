"""Validated events accepted by the conversation workflow."""
from enum import StrEnum
from .knowledge import KnowledgeContext
from typing import Annotated, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

class Control(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    REPEAT = "repeat"
    SLOW_DOWN = "slow_down"

class Event(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)

class TextEvent(Event):
    kind: Literal["text"] = "text"
    text: str

class ControlEvent(Event):
    kind: Literal["control"] = "control"
    control: Control

class CaptureEvent(Event):
    kind: Literal["capture"] = "capture"
    item_id: str = Field(min_length=1)
    tool: Literal["capture_photo", "record_statement"]
    arguments: dict[str, str]

class QuestionEvent(Event):
    kind: Literal["question"] = "question"
    question: str = Field(min_length=1, max_length=2000)

class ContextEvent(Event):
    kind: Literal["context"] = "context"
    context: KnowledgeContext

class AIConsentEvent(Event):
    kind: Literal["ai_consent"] = "ai_consent"
    capability: Literal["text", "images"]
    allowed: bool

class ReportEvent(Event):
    kind: Literal["report"] = "report"

class TimerEvent(Event):
    kind: Literal["timer"] = "timer"
    timer_id: str = Field(min_length=1)

InputEvent = Annotated[TextEvent | ControlEvent | TimerEvent | CaptureEvent | ReportEvent | QuestionEvent | ContextEvent | AIConsentEvent, Field(discriminator="kind")]
INPUT_EVENT_ADAPTER = TypeAdapter(InputEvent)
