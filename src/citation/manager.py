from __future__ import annotations

import re

from src.models import ClaimUnit, SourceRecord


class CitationManager:
    """Maps claims to source numbers and builds reference output."""

    _SOURCE_CITATION_PATTERN = re.compile(r"\[(SRC-\d{3})\]")

    def assign_citation_numbers(self, claims: list[ClaimUnit]) -> dict[str, int]:
        order: list[str] = []
        for claim in claims:
            for source_id in claim.supporting_source_ids:
                if source_id not in order:
                    order.append(source_id)
        return {source_id: index for index, source_id in enumerate(order, start=1)}

    def assign_numbers_from_texts(self, section_texts: list[str]) -> dict[str, int]:
        ordered_ids: list[str] = []
        for text in section_texts:
            for source_id in self.extract_source_ids(text):
                if source_id not in ordered_ids:
                    ordered_ids.append(source_id)
        return {source_id: index for index, source_id in enumerate(ordered_ids, start=1)}

    def extract_source_ids(self, text: str) -> list[str]:
        found: list[str] = []
        for match in self._SOURCE_CITATION_PATTERN.findall(text):
            if match not in found:
                found.append(match)
        return found

    def replace_source_placeholders(self, text: str, number_map: dict[str, int]) -> str:
        def replace(match: re.Match[str]) -> str:
            source_id = match.group(1)
            number = number_map.get(source_id)
            return f"[{number}]" if number is not None else match.group(0)

        return self._SOURCE_CITATION_PATTERN.sub(replace, text)

    def format_reference_list(
        self,
        sources: list[SourceRecord],
        number_map: dict[str, int],
    ) -> list[str]:
        source_map = {source.source_id: source for source in sources}
        rows: list[tuple[int, str]] = []
        for source_id, number in number_map.items():
            source = source_map.get(source_id)
            if not source:
                continue
            reference_text = source.reference_text_raw or source.title
            rows.append((number, f"[{number}] {reference_text}"))
        rows.sort(key=lambda item: item[0])
        return [row for _, row in rows]
