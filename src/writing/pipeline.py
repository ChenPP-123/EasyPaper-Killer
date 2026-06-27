from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths
from src.models import EvidenceChunk, OutlineNode, SourceRecord, TaskRequirements
from src.planning.requirements import RequirementsLoader
from src.writing.sections import SectionDraft, SectionGenerationPlan, SectionWriter


@dataclass(slots=True)
class WritingSummary:
    section_count: int
    prompt_file_count: int
    draft_file_count: int
    next_reply: str


class WritingPipeline:
    """Creates section-by-section writing packets for model-driven generation."""

    def __init__(self) -> None:
        self.requirements_loader = RequirementsLoader()
        self.section_writer = SectionWriter()

    def run(self, project_root: Path) -> WritingSummary:
        paths = ProjectPaths(project_root.resolve())
        paths.prompt_dir.mkdir(parents=True, exist_ok=True)
        paths.section_draft_dir.mkdir(parents=True, exist_ok=True)

        requirements = self.requirements_loader.load(paths.input_dir / "topic" / "任务需求.md")
        sources = self._load_dataclass_list(paths.sources_file, SourceRecord)
        evidence = self._load_dataclass_list(paths.evidence_file, EvidenceChunk)
        outline = self._load_dataclass_list(paths.outline_json_file, OutlineNode)
        display_title = (
            requirements.draft_title
            or requirements.topic_direction
            or self._load_outline_title(paths.outline_file)
            or "待确认"
        )

        section_plans: list[SectionGenerationPlan] = []
        section_drafts: list[SectionDraft] = []
        for node in outline:
            plan = self.section_writer.plan_section(node, evidence, sources, requirements)
            section_plans.append(plan)
            section_drafts.append(self.section_writer.write_section(node, evidence, sources, requirements))

        prompt_file_count = self._write_prompt_files(paths.prompt_dir, section_plans)
        draft_file_count = self._write_section_drafts(paths.section_draft_dir, section_drafts)
        self._write_section_plan(paths.section_plan_file, section_plans)
        self._write_master_draft(paths.draft_file, display_title, section_drafts, section_plans)

        return WritingSummary(
            section_count=len(section_plans),
            prompt_file_count=prompt_file_count,
            draft_file_count=draft_file_count,
            next_reply="大纲已拆分为分章节写作批次。请从第一章第一批 prompt 开始生成。",
        )

    def _load_dataclass_list(self, file_path: Path, cls: type):
        if not file_path.exists():
            return []
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return [cls(**item) for item in payload]

    def _load_outline_title(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- 最终题目："):
                return line.split("：", 1)[1].strip()
        return ""

    def _write_prompt_files(self, prompt_dir: Path, section_plans: list[SectionGenerationPlan]) -> int:
        count = 0
        for plan in section_plans:
            section_path = prompt_dir / f"{plan.section_id}_{plan.title}.md"
            lines = [
                f"# {plan.section_id} {plan.title}",
                "",
                f"- 本章目标字数：{plan.target_words}",
                f"- 单批次建议字数：{plan.batch_word_target}",
                f"- 下一步：{plan.next_action}",
                "",
            ]
            for index, packet in enumerate(plan.packets, start=1):
                lines.extend(
                    [
                        f"## 批次 {index}",
                        "",
                        f"- 可用文献：{'、'.join(packet.allowed_source_ids) if packet.allowed_source_ids else '无'}",
                        f"- 证据块数量：{len(packet.evidence_chunks)}",
                    ]
                )
                if packet.warning_notes:
                    for note in packet.warning_notes:
                        lines.append(f"- 风险提示：{note}")
                lines.extend(["", "```text", packet.prompt_text, "```", ""])
                count += 1
            section_path.write_text("\n".join(lines), encoding="utf-8")
        return count

    def _write_section_drafts(self, draft_dir: Path, section_drafts: list[SectionDraft]) -> int:
        for draft in section_drafts:
            file_path = draft_dir / f"{draft.section_id}_{draft.title}.md"
            lines = [f"# {draft.title}", "", draft.body, ""]
            file_path.write_text("\n".join(lines), encoding="utf-8")
        return len(section_drafts)

    def _write_section_plan(self, output_path: Path, section_plans: list[SectionGenerationPlan]) -> None:
        lines = [
            "# 章节写作计划",
            "",
            "本文件用于把整篇论文拆成多次模型调用，避免一次性整篇生成超出单次 token 限制。",
            "",
            "## 使用原则",
            "",
            "- 一次只生成一章中的一个批次。",
            "- 每个批次只使用对应 prompt 文件里的证据块。",
            "- 完成一个批次后，再继续下一个批次，不要跨章同时展开。",
            "- 如果某批次证据不足，应暂停并提示补资料。",
            "",
        ]
        for index, plan in enumerate(section_plans, start=1):
            lines.extend(
                [
                    f"## 第 {index} 章：{plan.title}",
                    "",
                    f"- 章节编号：{plan.section_id}",
                    f"- 目标字数：{plan.target_words}",
                    f"- 建议批次数：{len(plan.packets)}",
                    f"- 单批次建议字数：{plan.batch_word_target}",
                    f"- 推荐动作：{plan.next_action}",
                    "",
                ]
            )
        output_path.write_text("\n".join(lines), encoding="utf-8")

    def _write_master_draft(
        self,
        output_path: Path,
        display_title: str,
        section_drafts: list[SectionDraft],
        section_plans: list[SectionGenerationPlan],
    ) -> None:
        lines = [
            "# 正文草稿",
            "",
            f"- 当前题目：{display_title}",
            f"- 当前状态：已生成分章节写作槽位，等待模型逐批补全文本。",
            f"- 章节总数：{len(section_drafts)}",
            "",
            "## agent 使用说明",
            "",
            "- 先打开 `workspace/当前项目/05_章节写作计划.md` 确认批次顺序。",
            "- 再打开 `workspace/当前项目/prompts/` 下对应章节 prompt 文件。",
            "- 每次只让模型生成一个批次，把结果填回当前章节草稿。",
            "- 不要一次性生成整篇论文，以免触发单次最大输出 token 限制。",
            "",
        ]
        for draft, plan in zip(section_drafts, section_plans, strict=False):
            lines.extend(
                [
                    f"## {draft.title}",
                    "",
                    f"- 章节编号：{draft.section_id}",
                    f"- 建议批次数：{len(plan.packets)}",
                    "",
                    draft.body,
                    "",
                ]
            )
        output_path.write_text("\n".join(lines), encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare model-driven section writing packets.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = WritingPipeline()
    summary = pipeline.run(Path(args.project_root))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
