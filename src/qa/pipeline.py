from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths
from src.models import OutlineNode, SourceRecord
from src.qa.checks import CheckReport, QualityChecker


@dataclass(slots=True)
class QASummary:
    pending_batch_count: int
    must_fix_count: int
    risk_count: int
    report_file: str


class QAPipeline:
    """Builds a user-facing quality report from current draft artifacts."""

    def __init__(self) -> None:
        self.checker = QualityChecker()

    def run(self, project_root: Path) -> QASummary:
        paths = ProjectPaths(project_root.resolve())
        sources = self._load_dataclass_list(paths.sources_file, SourceRecord)
        outline = self._load_dataclass_list(paths.outline_json_file, OutlineNode)
        draft_text = paths.draft_file.read_text(encoding="utf-8") if paths.draft_file.exists() else ""
        numbered_text = paths.numbered_draft_file.read_text(encoding="utf-8") if paths.numbered_draft_file.exists() else draft_text
        section_draft_text = self._load_section_draft_text(paths.section_draft_dir)

        pending_count = self.checker.find_pending_generation_batches(draft_text)
        unknown_citations = self.checker.find_unknown_source_citations(numbered_text, sources)
        unused_sources = self.checker.find_unused_sources(draft_text, sources)
        outline_gaps = self.checker.check_outline_coverage(outline, sources)
        has_real_content = self.checker.has_real_content(section_draft_text)

        report = CheckReport(
            completed_checks=[
                "检查了当前正文草稿是否仍存在待生成批次。",
                "检查了正文中的来源占位是否能映射到正式文献。",
                "检查了大纲章节是否至少能对应到正式文献。",
                "检查了当前正式文献是否已在正文中使用。",
            ],
            risk_items=[],
            must_fix_items=[],
            optional_improvements=[],
            next_actions=[],
        )

        if pending_count:
            report.must_fix_items.append(f"当前仍有 {pending_count} 个批次尚未生成正文，不能进入终稿阶段。")
            report.next_actions.append("按 `05_章节写作计划.md` 的顺序逐批完成模型生成。")

        if not has_real_content:
            report.must_fix_items.append("当前正文仍以占位槽位为主，尚未形成可审阅初稿。")
            report.next_actions.append("先至少完成前两章正文生成，再重新运行引用整理和校验。")

        if unknown_citations:
            report.must_fix_items.append(
                "正文中存在无法映射到正式文献库的来源标记：" + "、".join(unknown_citations) + "。"
            )
            report.next_actions.append("检查模型输出的 `[SRC-xxx]` 是否来自已入库文献。")

        if unused_sources:
            report.risk_items.append(
                "以下正式文献尚未在正文中使用：" + "、".join(unused_sources) + "。"
            )

        if outline_gaps:
            report.risk_items.append(
                "以下章节在大纲层面存在资料覆盖风险：" + "、".join(outline_gaps) + "。"
            )

        if not report.must_fix_items:
            report.optional_improvements.append("可开始检查论证强度、段落衔接和摘要生成。")
            report.next_actions.append("如正文已经完整，可进入摘要、关键词和参考文献精修阶段。")

        self._write_report(paths.qa_report_file, report)
        return QASummary(
            pending_batch_count=pending_count,
            must_fix_count=len(report.must_fix_items),
            risk_count=len(report.risk_items),
            report_file=str(paths.qa_report_file),
        )

    def _load_dataclass_list(self, file_path: Path, cls: type):
        if not file_path.exists():
            return []
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return [cls(**item) for item in payload]

    def _load_section_draft_text(self, draft_dir: Path) -> str:
        if not draft_dir.exists():
            return ""
        chunks = []
        for file_path in sorted(draft_dir.glob("*.md")):
            chunks.append(file_path.read_text(encoding="utf-8"))
        return "\n\n".join(chunks)

    def _write_report(self, output_path: Path, report: CheckReport) -> None:
        lines = ["# 校验报告", ""]

        lines.extend(["## 已完成检查项", ""])
        for item in report.completed_checks:
            lines.append(f"- {item}")

        lines.extend(["", "## 必须修复项", ""])
        if report.must_fix_items:
            for item in report.must_fix_items:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前没有必须修复项。")

        lines.extend(["", "## 风险项", ""])
        if report.risk_items:
            for item in report.risk_items:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前没有额外风险项。")

        lines.extend(["", "## 可选优化项", ""])
        if report.optional_improvements:
            for item in report.optional_improvements:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前暂无可选优化项。")

        lines.extend(["", "## 用户下一步动作", ""])
        if report.next_actions:
            for item in report.next_actions:
                lines.append(f"- {item}")
        else:
            lines.append("- 当前无需额外动作。")

        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run quality checks for the current paper draft.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = QAPipeline()
    summary = pipeline.run(Path(args.project_root))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
