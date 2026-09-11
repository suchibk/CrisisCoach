"""Local file and verbatim statement capture; no image quality claims."""
from pathlib import Path
from .contracts import ToolSpec, FileCaptureArgs, StatementArgs, CaptureResult, ToolError
from .registry import ToolRegistry, ToolRegistration
from .executor import ToolExecutor
from ..persistence.attachments import AttachmentStore, MAX_FILE_BYTES


def build_capture_executor(root: Path, knowledge_root: Path | None = None) -> ToolExecutor:
    store = AttachmentStore(root)
    registry = ToolRegistry()

    def capture_photo(args, context):
        source = Path(args.source_path).expanduser()
        if not source.is_file(): raise ToolError("Select a readable image file")
        with source.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES: raise ToolError("Image exceeds 20 MiB")
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            media = "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            media = "image/jpeg"
        else:
            raise ToolError("Only JPEG and PNG files are supported")
        # Signature detection is format screening, not decoding or photo QA.
        return CaptureResult(attachment=store.put(context.incident_id, data, media))

    def record_statement(args, context):
        return CaptureResult(attachment=store.put(context.incident_id, args.text.encode("utf-8"), "text/plain"), original_text=args.text)

    registry.register(ToolRegistration(ToolSpec(name="capture_photo"), FileCaptureArgs, capture_photo))
    registry.register(ToolRegistration(ToolSpec(name="record_statement"), StatementArgs, record_statement))
    from ..reporting.evidence_pack import EvidencePackArgs, build_evidence_pack
    from ..models.reports import EvidencePackReference
    registry.register(ToolRegistration(ToolSpec(name="build_evidence_pack"), EvidencePackArgs,
        lambda args, context: build_evidence_pack(args, root, root.parent / "exports", context.event_id),
        result_model=EvidencePackReference))
    from .knowledge import register_knowledge_tools
    register_knowledge_tools(registry, knowledge_root)
    return ToolExecutor(registry)
