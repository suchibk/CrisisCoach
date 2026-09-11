# Local capture tools

ToolRegistry contains explicit metadata, argument models, and handlers. ToolExecutor validates Pydantic arguments/results and blocks external or approval-required tools. There is no implemented external approval flow or insurer delivery tool yet.

Implemented tools:
- capture_photo: copies a user-selected JPEG/PNG file, up to 20 MiB, into the local attachment store.
- record_statement: saves original text verbatim as UTF-8, up to 20,000 characters; also used for user-entered party/contact details.

Only the workflow graph invokes the executor. Safety, lifecycle, domain applicability, and expected capture type are checked first. Interface controls submit CaptureEvents. File signatures are checked, but images are not decoded or quality-verified. No OCR, vision service, network call, or file execution occurs.

Immutable blobs use incident/content hashes, atomic file replacement, and fsync. SQLite stores validated attachment references with the evidence transition. A database failure may leave an unreferenced blob; it does not mark evidence collected. Retrying reuses matching content. Garbage collection is not implemented yet.
