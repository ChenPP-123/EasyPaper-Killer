from __future__ import annotations

from dataclasses import dataclass, field
import re

from src.models import ClaimStatus, ClaimUnit, OutlineNode, SourceRecord, TemplateSpec


@dataclass(slots=True)
class CheckReport:
    completed_checks: list[str] = field(default_factory=list)
    risk_items: list[str] = field(default_factory=list)
    must_fix_items: list[str] = field(default_factory=list)
    optional_improvements: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


class QualityChecker:
    """Runs the minimum checks before draft or final export."""

    _SOURCE_CITATION_PATTERN = re.compile(r"\[(SRC-\d{3}|\d+)\]")
    _PENDING_PATTERN = re.compile(r"\[待模型生成：")

    def check_claim_support(self, claims: list[ClaimUnit]) -> list[str]:
        return [
            claim.claim_id
            for claim in claims
            if claim.status in {ClaimStatus.WEAK, ClaimStatus.UNSUPPORTED}
        ]

    def check_outline_coverage(
        self,
        outline: list[OutlineNode],
        sources: list[SourceRecord],
    ) -> list[str]:
        available_ids = {source.source_id for source in sources}
        missing_sections: list[str] = []
        for node in outline:
            if not set(node.allowed_source_ids) & available_ids:
                missing_sections.append(node.section_id)
        return missing_sections

    def check_template_ready(self, template_spec: TemplateSpec | None) -> bool:
        return template_spec is not None

    def find_pending_generation_batches(self, text: str) -> int:
        return len(self._PENDING_PATTERN.findall(text))

    def find_unknown_source_citations(self, text: str, sources: list[SourceRecord]) -> list[str]:
        available_ids = {source.source_id for source in sources}
        unknown = []
        for match in self._SOURCE_CITATION_PATTERN.findall(text):
            if match.startswith("SRC-") and match not in available_ids and match not in unknown:
                unknown.append(match)
        return unknown

    def find_unused_sources(self, text: str, sources: list[SourceRecord]) -> list[str]:
        used = set(self._SOURCE_CITATION_PATTERN.findall(text))
        return [source.source_id for source in sources if source.source_id not in used]

    def has_real_content(self, text: str) -> bool:
        stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
        meaningful = [line for line in stripped_lines if not line.startswith("#") and "待模型生成" not in line]
        return bool(meaningful)
