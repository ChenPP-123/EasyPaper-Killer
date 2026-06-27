from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.config.paths import ProjectPaths
from src.ingest.collector import MaterialCollector
from src.models import EvidenceChunk, SourceRecord
from src.parse.sources import SourceParser


@dataclass(slots=True)
class IngestionSummary:
    source_count: int
    evidence_count: int
    text_file_count: int
    pdf_file_count: int
    template_file_count: int


class MaterialIngestionPipeline:
    """Collect raw materials, parse them, and write structured JSON output."""

    def __init__(self) -> None:
        self.collector = MaterialCollector()
        self.parser = SourceParser()

    def run(self, project_root: Path, raw_dir: Path | None = None) -> IngestionSummary:
        paths = ProjectPaths(project_root.resolve())
        paths.ensure_runtime_dirs()

        effective_raw_dir = raw_dir.resolve() if raw_dir else paths.raw_references_dir
        materials = self.collector.collect(effective_raw_dir, paths.template_dir)

        sources = self._parse_sources(materials.text_files, materials.pdf_files)
        evidence = self._build_evidence(sources)

        self._write_json(paths.sources_file, [asdict(source) for source in sources])
        self._write_json(paths.evidence_file, [asdict(chunk) for chunk in evidence])
        self._write_json(paths.references_file, self._build_reference_rows(sources))

        return IngestionSummary(
            source_count=len(sources),
            evidence_count=len(evidence),
            text_file_count=len(materials.text_files),
            pdf_file_count=len(materials.pdf_files),
            template_file_count=len(materials.template_files),
        )

    def _parse_sources(self, text_files: list[Path], pdf_files: list[Path]) -> list[SourceRecord]:
        sources: list[SourceRecord] = []
        next_index = 1

        for text_file in text_files:
            text = text_file.read_text(encoding="utf-8")
            parsed_sources = self.parser.parse_reference_text(text, start_index=next_index)
            next_index += len(parsed_sources)

            for source in parsed_sources:
                self.parser.attach_pdf_paths(source, pdf_files)
            sources.extend(parsed_sources)

        return sources

    def _build_evidence(self, sources: list[SourceRecord]) -> list[EvidenceChunk]:
        evidence: list[EvidenceChunk] = []
        for source in sources:
            evidence.extend(self.parser.build_evidence_chunks(source))
        return evidence

    def _build_reference_rows(self, sources: list[SourceRecord]) -> list[dict[str, str]]:
        rows = []
        for source in sources:
            rows.append(
                {
                    "source_id": source.source_id,
                    "title": source.title,
                    "reference_text": source.reference_text_raw,
                    "cnki_url": source.cnki_url,
                }
            )
        return rows

    def _write_json(self, output_path: Path, payload: Any) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse raw paper materials into structured JSON.")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory containing input/, template/, and workspace/.",
    )
    parser.add_argument(
        "--raw-dir",
        default="",
        help="Optional override for the raw materials directory.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = MaterialIngestionPipeline()
    summary = pipeline.run(
        project_root=Path(args.project_root),
        raw_dir=Path(args.raw_dir) if args.raw_dir else None,
    )
    print(
        json.dumps(
            asdict(summary),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
