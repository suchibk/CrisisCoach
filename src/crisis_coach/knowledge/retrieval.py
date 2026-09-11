"""Provider-independent retrieval interface."""
from typing import Protocol
from ..models.knowledge import KnowledgeQuery, KnowledgeAnswer

class KnowledgeRetriever(Protocol):
    def retrieve(self, query: KnowledgeQuery) -> KnowledgeAnswer: ...
