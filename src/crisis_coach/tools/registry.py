"""Explicit typed tool registration; no model-supplied executable code."""
from typing import Callable
from pydantic import BaseModel
from .contracts import ToolSpec, ToolContext, CaptureResult, ToolError

class ToolRegistration:
    def __init__(self, spec: ToolSpec, arguments: type[BaseModel], handler: Callable[[BaseModel, ToolContext], BaseModel], result_model: type[BaseModel] = CaptureResult):
        self.spec, self.arguments, self.handler = spec, arguments, handler
        self.result_model = result_model

class ToolRegistry:
    def __init__(self): self._tools: dict[str, ToolRegistration] = {}
    def register(self, tool: ToolRegistration) -> None:
        if tool.spec.name in self._tools: raise ValueError("Tool already registered")
        self._tools[tool.spec.name] = tool
    def get(self, name: str) -> ToolRegistration:
        if name not in self._tools: raise ToolError("Unknown tool")
        return self._tools[name]
    def available(self) -> tuple[ToolSpec, ...]:
        return tuple(tool.spec for tool in self._tools.values())
