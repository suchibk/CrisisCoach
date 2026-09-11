# Reporting

completeness.py computes exact applicable-item coverage using Pydantic reports. It counts attachments once per item, excludes user reports from stored coverage, and accepts export validation problems. In-memory calculations do not independently read the filesystem.

evidence_pack.py validates incident-scoped attachment paths and hashes, embeds images/text into a DOCX, and records gaps for unavailable or unreadable content. Optional python-docx imports occur only when generating a report. EvidencePackReference persists the artifact path, checksum, snapshot revision, export timestamp, coverage counts, and export problems.

The build_evidence_pack tool runs through the shared executor and graph report node. Both interfaces require active, cleared safety gates for building or downloading a pack. Report actions do not mark a session complete or replace its collection instruction. No external delivery or model-written narrative is included.
