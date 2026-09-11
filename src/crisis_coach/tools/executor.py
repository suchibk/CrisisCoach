"""One entry point for validated local tool execution."""
from pydantic import BaseModel, ValidationError
from .contracts import ToolContext, CaptureResult, ToolError, ApprovalRequired
from .registry import ToolRegistry

class ToolExecutor:
    def __init__(self, registry: ToolRegistry): self.registry = registry
    def execute(self, name: str, arguments: dict, context: ToolContext) -> BaseModel:
        tool = self.registry.get(name)
        # No external tools are supported in this milestone. Never accept a
        # caller-provided approved=True flag as authorization.
        if tool.spec.external or tool.spec.requires_approval:
            raise ApprovalRequired("This tool requires an approval flow that is not yet implemented")
        try:
            args = tool.arguments.model_validate(arguments)
            return tool.result_model.model_validate(tool.handler(args, context))
        except (ValidationError, OSError) as exc:
            raise ToolError("Tool operation failed; check the input and try again") from exc
