"""Immutable local blobs; deterministic paths make retries idempotent."""
import hashlib
import os
import tempfile
from pathlib import Path
from ..tools.contracts import AttachmentReference, ToolError

MAX_FILE_BYTES = 20 * 1024 * 1024

class AttachmentStore:
    def __init__(self, root: Path): self.root = Path(root).resolve()

    def put(self, incident_id: str, data: bytes, media_type: str) -> AttachmentReference:
        if not data or len(data) > MAX_FILE_BYTES: raise ToolError("File must be between 1 byte and 20 MiB")
        digest = hashlib.sha256(data).hexdigest()
        # Never concatenate user-controlled IDs or filenames into a path.
        incident_key = hashlib.sha256(incident_id.encode()).hexdigest()
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "text/plain": ".txt"}[media_type]
        relative = Path(incident_key) / (digest + suffix)
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root): raise ToolError("Invalid attachment path")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ToolError("Existing attachment failed integrity validation")
        else:
            descriptor, name = tempfile.mkstemp(dir=target.parent)
            temporary = Path(name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        return AttachmentReference(relative_path=relative.as_posix(), sha256=digest,
                                   size_bytes=len(data), media_type=media_type)

    def read(self, incident_id: str, reference: AttachmentReference) -> bytes:
        incident_key = hashlib.sha256(incident_id.encode()).hexdigest()
        path = (self.root / reference.relative_path).resolve()
        if not path.is_relative_to(self.root / incident_key):
            raise ToolError("Attachment reference is outside this incident")
        try:
            with path.open("rb") as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
        except OSError as exc:
            raise ToolError("Stored attachment is missing or unreadable") from exc
        if len(data) != reference.size_bytes or hashlib.sha256(data).hexdigest() != reference.sha256:
            raise ToolError("Stored attachment failed integrity validation")
        return data
