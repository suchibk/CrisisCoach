"""Explicit registration; placeholder folders never become executable domains."""
from .contracts import DomainPack, DomainMetadata

class DomainRegistry:
    def __init__(self):
        self._packs: dict[str, DomainPack] = {}

    def register(self, pack: DomainPack) -> None:
        metadata = DomainMetadata.model_validate(pack.metadata)
        if metadata.domain_id in self._packs:
            raise ValueError(f"Domain already registered: {metadata.domain_id}")
        self._packs[metadata.domain_id] = pack

    def get(self, domain_id: str) -> DomainPack:
        try:
            return self._packs[domain_id]
        except KeyError:
            raise ValueError(f"Domain is not available: {domain_id}") from None

    def available(self) -> tuple[DomainMetadata, ...]:
        return tuple(self._packs[key].metadata for key in sorted(self._packs))
