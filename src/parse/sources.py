from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.models import EvidenceChunk, SourceRecord


@dataclass(slots=True)
class ParsedReferenceEntry:
    entry_number: int
    authors: list[str]
    title: str
    journal: str
    source_type: str
    abstract: str
    cnki_url: str
    citation_text_raw: str
    reference_text_raw: str


@dataclass(slots=True)
class MetadataFields:
    authors: list[str]
    title: str
    journal: str
    source_type: str


class SourceParser:
    """Turns raw reference text into structured source records."""

    _SECTION_TITLE_PATTERN = re.compile(r"^\s*(查新引文|参考文献)[:：]\s*$", re.MULTILINE)
    _ENTRY_PATTERN = re.compile(r"^\[(\d+)\]\s*(.*?)(?=^\[\d+\]\s*|\Z)", re.MULTILINE | re.DOTALL)
    _METADATA_PATTERN = re.compile(
        r"^\s*(?P<authors>.+?)\.\s*[\"“”]?(?P<title>.+?)[\"“”]?\[(?P<source_type>[^\]]+)\]\.\s*(?P<journal>[^,，\n]+)",
        re.DOTALL,
    )
    _URL_PATTERN = re.compile(r"https?://\S+")

    def parse_reference_text(self, text: str, start_index: int = 1) -> list[SourceRecord]:
        """Parse numbered citation/reference text into formal sources."""
        sections = self._split_sections(text)
        citation_entries = self._parse_numbered_entries(sections.get("查新引文", ""))
        reference_entries = self._parse_numbered_entries(sections.get("参考文献", ""))

        entry_numbers = sorted(set(citation_entries) | set(reference_entries))
        sources: list[SourceRecord] = []

        for offset, entry_number in enumerate(entry_numbers, start=0):
            parsed = self._merge_entry(
                entry_number,
                citation_entries.get(entry_number, ""),
                reference_entries.get(entry_number, ""),
            )
            if not parsed.title:
                continue

            sources.append(
                SourceRecord(
                    source_id=f"SRC-{start_index + offset:03d}",
                    title=parsed.title,
                    authors=parsed.authors,
                    journal=parsed.journal,
                    source_type=parsed.source_type,
                    cnki_url=parsed.cnki_url,
                    abstract=parsed.abstract,
                    citation_text_raw=parsed.citation_text_raw,
                    reference_text_raw=parsed.reference_text_raw,
                )
            )

        return sources

    def build_evidence_chunks(self, source: SourceRecord) -> list[EvidenceChunk]:
        """Extract evidence candidates from a formal source."""
        if not source.abstract:
            return []

        chunks = [
            EvidenceChunk(
                chunk_id=f"{source.source_id}-ABS",
                source_id=source.source_id,
                text=source.abstract,
                location="abstract",
                evidence_type="abstract_full",
                confidence="high",
            )
        ]

        sentences = self._split_sentences(source.abstract)
        for index, sentence in enumerate(sentences[:5], start=1):
            if len(sentence) < 20:
                continue
            chunks.append(
                EvidenceChunk(
                    chunk_id=f"{source.source_id}-S{index}",
                    source_id=source.source_id,
                    text=sentence,
                    location=f"abstract_sentence_{index}",
                    evidence_type="abstract_sentence",
                    confidence="medium",
                )
            )
        return chunks

    def parse_pdf(self, pdf_path: Path) -> str:
        """Return a placeholder until PDF extraction is implemented."""
        _ = pdf_path
        return ""

    def attach_pdf_paths(self, source: SourceRecord, pdf_files: list[Path]) -> None:
        source.file_paths = [str(path) for path in self._match_pdf_files(source.title, pdf_files)]

    def _split_sections(self, text: str) -> dict[str, str]:
        normalized = text.replace("\r\n", "\n")
        matches = list(self._SECTION_TITLE_PATTERN.finditer(normalized))
        if not matches:
            return {"参考文献": normalized}

        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            name = match.group(1)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            sections[name] = normalized[start:end].strip()
        return sections

    def _parse_numbered_entries(self, section_text: str) -> dict[int, str]:
        entries: dict[int, str] = {}
        for match in self._ENTRY_PATTERN.finditer(section_text.strip()):
            entry_number = int(match.group(1))
            entries[entry_number] = self._normalize_inline_text(match.group(2))
        return entries

    def _merge_entry(
        self,
        entry_number: int,
        citation_text: str,
        reference_text: str,
    ) -> ParsedReferenceEntry:
        citation_meta, abstract = self._split_abstract(citation_text)
        citation_fields = self._extract_metadata(citation_meta)
        reference_fields = self._extract_metadata(reference_text)

        authors = citation_fields.authors or reference_fields.authors
        title = citation_fields.title or reference_fields.title
        journal = reference_fields.journal or citation_fields.journal
        source_type = reference_fields.source_type or citation_fields.source_type or "journal"
        cnki_url = self._extract_url(reference_text)

        return ParsedReferenceEntry(
            entry_number=entry_number,
            authors=authors,
            title=title,
            journal=journal,
            source_type=source_type,
            abstract=abstract,
            cnki_url=cnki_url,
            citation_text_raw=citation_text,
            reference_text_raw=reference_text,
        )

    def _split_abstract(self, citation_text: str) -> tuple[str, str]:
        if not citation_text:
            return "", ""

        parts = re.split(r"摘要[:：]", citation_text, maxsplit=1)
        if len(parts) == 1:
            return self._normalize_inline_text(parts[0]), ""
        return self._normalize_inline_text(parts[0]), self._normalize_inline_text(parts[1])

    def _extract_metadata(self, entry_text: str) -> MetadataFields:
        if not entry_text:
            return MetadataFields(authors=[], title="", journal="", source_type="")

        cleaned = self._normalize_inline_text(entry_text)
        match = self._METADATA_PATTERN.search(cleaned)
        if not match:
            return MetadataFields(authors=[], title="", journal="", source_type="")

        authors_raw = match.group("authors").strip()
        authors = [part.strip() for part in re.split(r"[，,]", authors_raw) if part.strip()]
        return MetadataFields(
            authors=authors,
            title=re.sub(r"[“”\"]", "", match.group("title")).strip(),
            journal=match.group("journal").strip(),
            source_type=match.group("source_type").strip(),
        )

    def _extract_url(self, entry_text: str) -> str:
        match = self._URL_PATTERN.search(entry_text)
        return match.group(0).rstrip(".,;") if match else ""

    def _match_pdf_files(self, title: str, pdf_files: list[Path]) -> list[Path]:
        if not title:
            return []

        normalized_title = self._normalize_lookup_text(title)
        matched = []
        for pdf_file in pdf_files:
            normalized_stem = self._normalize_lookup_text(pdf_file.stem)
            if normalized_title and (normalized_title in normalized_stem or normalized_stem in normalized_title):
                matched.append(pdf_file)
        return matched

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[。！？；])", text)
        return [self._normalize_inline_text(part) for part in parts if self._normalize_inline_text(part)]

    def _normalize_inline_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _normalize_lookup_text(self, text: str) -> str:
        return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", text).lower()
