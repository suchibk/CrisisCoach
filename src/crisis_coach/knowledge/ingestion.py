"""Load reviewed JSON source records, without fetching URLs or executing content."""
from pathlib import Path
from ..models.knowledge import SourceCorpus


def load_corpus(directory: Path) -> SourceCorpus:
    passages = []
    for path in sorted(Path(directory).rglob("*.json")):
        corpus = SourceCorpus.model_validate_json(path.read_text(encoding="utf-8"))
        passages.extend(corpus.passages)
    return SourceCorpus(passages=tuple(passages))
