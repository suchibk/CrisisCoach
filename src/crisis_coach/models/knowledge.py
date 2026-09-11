"""Source and retrieval contracts; citations carry the actual supporting passage."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class KnowledgeContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    policy_id: str | None = None
    jurisdiction: str | None = None
    reference_date: date | None = None
    allow_synthetic: bool = False

class SourcePassage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    corpus: Literal["policy", "duties"]
    policy_id: str | None = None
    jurisdiction: str | None = None
    effective_from: date
    effective_until: date | None = None
    topics: tuple[str, ...] = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    synthetic: bool = False
    reviewed: bool = False

    @model_validator(mode="after")
    def validate_scope(self):
        if self.corpus == "policy" and not self.policy_id:
            raise ValueError("Policy passages require a policy ID")
        if self.corpus == "duties" and not self.jurisdiction:
            raise ValueError("Duty passages require a jurisdiction")
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Source effective dates are reversed")
        return self

class SourceCorpus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal[1] = 1
    passages: tuple[SourcePassage, ...]

    @model_validator(mode="after")
    def unique_sources(self):
        ids = [passage.source_id for passage in self.passages]
        if len(ids) != len(set(ids)): raise ValueError("Duplicate source IDs")
        return self

class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    corpus: Literal["policy", "duties"]
    topic: str = Field(min_length=1)
    context: KnowledgeContext

class KnowledgeAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    question: str
    status: Literal["found", "not_found", "refused"]
    message: str
    citations: tuple[SourcePassage, ...] = ()

    @model_validator(mode="after")
    def citations_required(self):
        if (self.status == "found") != bool(self.citations):
            raise ValueError("Only supported results may contain citations; found requires citations")
        return self
