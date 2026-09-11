"""Read-only local policy and duties tools."""
import os
from pathlib import Path
from importlib.resources import files
from pydantic import ValidationError
from .contracts import ToolSpec, ToolError
from .registry import ToolRegistry, ToolRegistration
from ..models.knowledge import SourceCorpus, KnowledgeQuery, KnowledgeAnswer
from ..knowledge.local import LocalKnowledgeRetriever
from ..knowledge.ingestion import load_corpus


def register_knowledge_tools(registry: ToolRegistry):
    try:
        custom = os.getenv("CRISIS_COACH_KNOWLEDGE_DIR")
        root = Path(custom) if custom else Path(str(files("crisis_coach.domains.collision").joinpath("resources/knowledge")))
        if not root.is_dir(): raise OSError("Source directory is unavailable")
        retriever = LocalKnowledgeRetriever(load_corpus(root))
    except (OSError, ValidationError):
        retriever = LocalKnowledgeRetriever(SourceCorpus(passages=()), unavailable=True)
    def policy(args, context):
        if args.corpus != "policy": raise ToolError("Policy tool requires the policy corpus")
        return retriever.retrieve(args)
    def duties(args, context):
        if args.corpus != "duties": raise ToolError("Duties tool requires the duties corpus")
        return retriever.retrieve(args)
    registry.register(ToolRegistration(ToolSpec(name="check_policy"), KnowledgeQuery, policy, KnowledgeAnswer))
    registry.register(ToolRegistration(ToolSpec(name="assess_duties"), KnowledgeQuery, duties, KnowledgeAnswer))
