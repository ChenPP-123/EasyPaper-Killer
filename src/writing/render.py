from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths


@dataclass(slots=True)
class RenderSummary:
    section_count: int
    output_file: str


class DraftRenderer:
    """Rebuilds the master draft from current section draft files."""

    def run(self, project_root: Path) -> RenderSummary:
        paths = ProjectPaths(project_root.resolve())
        sections = self._load_sections(paths.section_draft_dir)
        title = self._load_outline_title(paths.outline_file)

        lines = [
            "# 正文草稿",
            "",
            f"- 当前题目：{title or '待确认'}",
            "- 当前状态：已根据 `section_drafts/` 汇总当前章节草稿。",
            f"- 章节总数：{len(sections)}",
            "",
            "## agent 使用说明",
            "",
            "- 如果需要继续生成新批次，优先更新 `section_drafts/` 下对应章节文件。",
            "- 更新后重新运行正文汇总、引用整理和校验流程。",
            "- 若某章仍需重写，只重写该章，不要一次性推倒整篇。",
            "",
        ]
        for title_text, body in sections:
            lines.extend([f"## {title_text}", "", body, ""])

        paths.draft_file.write_text("\n".join(lines), encoding="utf-8")
        return RenderSummary(section_count=len(sections), output_file=str(paths.draft_file))

    def _load_sections(self, section_dir: Path) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        for file_path in sorted(section_dir.glob("*.md")):
            lines = file_path.read_text(encoding="utf-8").splitlines()
            title = lines[0].lstrip("# ").strip() if lines else file_path.stem
            body = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""
            sections.append((title, body))
        return sections

    def _load_outline_title(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- 最终题目："):
                return line.split("：", 1)[1].strip()
        return ""


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the master draft from section draft files.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    renderer = DraftRenderer()
    summary = renderer.run(Path(args.project_root))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
