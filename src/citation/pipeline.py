from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.citation.manager import CitationManager
from src.config.paths import ProjectPaths
from src.models import SourceRecord


@dataclass(slots=True)
class CitationSummary:
    section_count: int
    cited_source_count: int
    generated_files: list[str]


class CitationPipeline:
    """Collects section drafts, resolves source placeholders, and writes references."""

    def __init__(self) -> None:
        self.manager = CitationManager()

    def run(self, project_root: Path) -> CitationSummary:
        paths = ProjectPaths(project_root.resolve())
        sources = self._load_sources(paths.sources_file)
        sections = self._load_section_drafts(paths.section_draft_dir)
        number_map = self.manager.assign_numbers_from_texts([section[1] for section in sections])

        numbered_sections = [
            (title, self.manager.replace_source_placeholders(content, number_map))
            for title, content in sections
        ]
        reference_lines = self.manager.format_reference_list(sources, number_map)

        self._write_numbered_draft(paths.numbered_draft_file, numbered_sections)
        self._write_reference_list(paths.reference_list_file, reference_lines)

        return CitationSummary(
            section_count=len(numbered_sections),
            cited_source_count=len(number_map),
            generated_files=[str(paths.numbered_draft_file), str(paths.reference_list_file)],
        )

    def _load_sources(self, file_path: Path) -> list[SourceRecord]:
        if not file_path.exists():
            return []
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return [SourceRecord(**item) for item in payload]

    def _load_section_drafts(self, draft_dir: Path) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        if not draft_dir.exists():
            return sections
        for file_path in sorted(draft_dir.glob("*.md")):
            raw_text = file_path.read_text(encoding="utf-8")
            lines = raw_text.splitlines()
            title = lines[0].lstrip("# ").strip() if lines else file_path.stem
            content = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""
            sections.append((title, content))
        return sections

    def _write_numbered_draft(self, output_path: Path, sections: list[tuple[str, str]]) -> None:
        lines = [
            "# 正文草稿引用整理版",
            "",
            "本文件基于 `section_drafts/` 自动汇总生成。当前仍可能包含未完成批次占位，编号整理仅针对已经写出的 `[SRC-xxx]` 引用。",
            "",
        ]
        for title, content in sections:
            lines.extend([f"## {title}", "", content, ""])
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _write_reference_list(self, output_path: Path, reference_lines: list[str]) -> None:
        lines = ["# 参考文献列表", ""]
        if reference_lines:
            lines.extend(reference_lines)
        else:
            lines.append("- 当前尚未在正文中检测到正式引用占位 `[SRC-xxx]`，因此还不能生成正式参考文献列表。")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve source placeholders into numbered citations.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = CitationPipeline()
    summary = pipeline.run(Path(args.project_root))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
