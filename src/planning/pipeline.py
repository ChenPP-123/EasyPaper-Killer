from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths
from src.models import OutlineNode, SourceRecord, TaskRequirements
from src.planning.outline import OutlinePlanner
from src.planning.requirements import RequirementsLoader
from src.planning.topic import QueryPlan, TopicOption, TopicPlanner


@dataclass(slots=True)
class PlanningSummary:
    base_topic: str
    topic_option_count: int
    source_count: int
    outline_section_count: int
    generated_files: list[str]


class PlanningPipeline:
    """Generates workspace planning documents from requirements and parsed sources."""

    def __init__(self) -> None:
        self.requirements_loader = RequirementsLoader()
        self.topic_planner = TopicPlanner()
        self.outline_planner = OutlinePlanner()

    def run(
        self,
        project_root: Path,
        **requirement_overrides: object,
    ) -> PlanningSummary:
        paths = ProjectPaths(project_root.resolve())
        paths.workspace_dir.mkdir(parents=True, exist_ok=True)

        requirements = self.requirements_loader.load(paths.input_dir / "topic" / "任务需求.md")
        requirements = self.requirements_loader.with_overrides(requirements, **requirement_overrides)
        sources = self._load_sources(paths.sources_file)

        topic_options = self.topic_planner.refine_topic(requirements, sources)
        query_plan = self.topic_planner.build_cnki_query(requirements, sources)
        outline = self.outline_planner.build_outline(requirements, sources)

        self._write_markdown(paths.topic_refinement_file, self._render_topic_file(requirements, topic_options, query_plan))
        self._write_markdown(paths.query_file, self._render_query_file(query_plan))
        self._write_markdown(paths.material_review_file, self._render_material_review_file(requirements, sources, outline))
        self._write_markdown(paths.outline_file, self._render_outline_file(requirements, sources, outline))
        self._write_json(paths.outline_json_file, [asdict(node) for node in outline])

        return PlanningSummary(
            base_topic=query_plan.base_topic,
            topic_option_count=len(topic_options),
            source_count=len(sources),
            outline_section_count=len(outline),
            generated_files=[
                str(paths.topic_refinement_file),
                str(paths.query_file),
                str(paths.material_review_file),
                str(paths.outline_file),
                str(paths.outline_json_file),
            ],
        )

    def _load_sources(self, file_path: Path) -> list[SourceRecord]:
        if not file_path.exists():
            return []
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        return [SourceRecord(**item) for item in payload]

    def _render_topic_file(
        self,
        requirements: TaskRequirements,
        topic_options: list[TopicOption],
        query_plan: QueryPlan,
    ) -> str:
        lines = [
            "# 选题收敛",
            "",
            f"- 当前基础方向：{query_plan.base_topic}",
            f"- 课程名称：{requirements.course_name or '未提供'}",
            f"- 论文类型：{requirements.paper_type or '待进一步确认'}",
            "",
            "## 建议题目",
            "",
        ]
        for index, option in enumerate(topic_options, start=1):
            lines.extend(
                [
                    f"### 方案 {index}",
                    "",
                    f"- 题目：{option.title}",
                    f"- 适用理由：{option.rationale}",
                    f"- 风险提醒：{option.risk}",
                    "",
                ]
            )

        lines.extend(
            [
                "## agent 下一步提示",
                "",
                "- 如果用户尚未确认题目，先让用户在上述题目中确认或提出修改方向。",
                "- 题目确认后，再进入检索式生成和资料收集阶段。",
                "- 如果用户说题目还想更偏稳妥或更偏综述，应基于当前基础方向再缩小范围。",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_query_file(self, query_plan: QueryPlan) -> str:
        lines = [
            "# 检索式",
            "",
            f"- 基础主题：{query_plan.base_topic}",
            f"- 核心关键词：{'、'.join(query_plan.core_terms) if query_plan.core_terms else '待补充'}",
            f"- 关联关键词：{'、'.join(query_plan.related_terms) if query_plan.related_terms else '待补充'}",
            "",
            "## 推荐检索式（CNKI 专业检索，可直接粘贴）",
            "",
            "字段说明：`TKA` = 篇名 + 关键词 + 摘要。",
            "",
        ]
        for index, query in enumerate(query_plan.search_queries, start=1):
            lines.append(f"{index}. `{query}`")

        lines.extend(
            [
                "",
                "### 使用方式",
                "",
                "1. 打开知网高级检索 → 切换到「专业检索」标签。",
                "2. 将上面任一检索式完整粘贴到输入框。",
                "3. 如需缩小范围：增加 `*` 后的条件项。如需扩大范围：删减 `*` 后的条件项。",
                "",
                "### 筛文建议",
                "",
            ]
        )
        for tip in query_plan.screening_tips:
            lines.append(f"- {tip}")

        lines.extend(
            [
                "",
                "## agent 给用户的下一步指令",
                "",
                "- 下载 5-10 篇最相关论文 PDF，放到 `input/references/raw/pdf/`。",
                "- 把查新引文和参考文献文本放到 `input/references/raw/`。",
                "- 如果老师有额外格式要求，补到 `input/constraints/格式与写作要求.md`。",
                "- 完成后回复：`资料已放入`。",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_material_review_file(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
        outline: list[OutlineNode],
    ) -> str:
        source_titles = [source.title for source in sources]
        related_sources, off_topic_sources = self._split_sources_by_relevance(requirements, sources)
        lines = [
            "# 资料盘点",
            "",
            f"- 当前题目方向：{requirements.draft_title or requirements.topic_direction or '未明确'}",
            f"- 当前正式文献数量：{len(sources)}",
            f"- 与当前题目明显相关的文献数：{len(related_sources)}",
            f"- 已生成大纲章节数：{len(outline)}",
            "",
            "## 当前已入库文献",
            "",
        ]
        if source_titles:
            for index, title in enumerate(source_titles, start=1):
                lines.append(f"{index}. {title}")
        else:
            lines.append("- 当前尚无正式入库文献。")

        lines.extend(["", "## 覆盖情况判断", ""])
        if len(related_sources) >= 5:
            lines.append("- 当前资料数量基本可支撑课程论文初稿，但仍需看题目是否过大。")
        elif related_sources:
            lines.append("- 当前资料可用于搭建初步大纲，但正文阶段可能仍需补充文献。")
        else:
            lines.append("- 当前资料不足，不能进入稳定写作阶段。")

        weak_sections = [node.title for node in outline if "缺少直接支撑" in node.notes or "较少" in node.notes]
        lines.extend(["", "## 风险提示", ""])
        if off_topic_sources:
            lines.append(f"- 以下文献与当前题目相关性偏弱，后续应谨慎使用：{'、'.join(off_topic_sources)}。")
        if weak_sections:
            for title in weak_sections:
                lines.append(f"- `{title}` 章节的直接支撑文献偏少。")
        if not off_topic_sources and not weak_sections:
            lines.append("- 当前未发现明显缺口章节，但仍需人工确认题目和资料匹配度。")

        return "\n".join(lines) + "\n"

    def _split_sources_by_relevance(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
    ) -> tuple[list[str], list[str]]:
        topic_text = requirements.draft_title or requirements.topic_direction
        if not topic_text.strip():
            return ([source.title for source in sources], [])

        related: list[str] = []
        off_topic: list[str] = []
        for source in sources:
            source_text = source.title + " " + source.abstract
            if self._has_topic_overlap(topic_text, source_text):
                related.append(source.title)
            else:
                off_topic.append(source.title)
        return related, off_topic

    def _has_topic_overlap(self, topic_text: str, source_text: str) -> bool:
        topic_phrases = self._extract_phrases(topic_text)
        normalized_source = source_text.replace("“", "").replace("”", "")
        for phrase in topic_phrases:
            if phrase in normalized_source:
                return True

        topic_terms = self._extract_terms(topic_text)
        source_terms = self._extract_terms(source_text)
        return bool(topic_terms & source_terms)

    def _extract_phrases(self, text: str) -> list[str]:
        cleaned = text.replace("“", " ").replace("”", " ")
        for char in "（）()，,。；;：:-":
            cleaned = cleaned.replace(char, " ")
        parts = []
        for raw in cleaned.split():
            parts.extend(re.split(r"与|和|及|的|在|基于", raw))
        return [part.strip() for part in parts if len(part.strip()) >= 4]

    def _extract_terms(self, text: str) -> set[str]:
        cleaned = text.replace("“", " ").replace("”", " ")
        for char in "（）()，,。；;：:-":
            cleaned = cleaned.replace(char, " ")
        parts = []
        for raw in cleaned.split():
            parts.extend(re.split(r"与|和|及|的", raw))
        return {part.strip() for part in parts if len(part.strip()) >= 2}

    def _render_outline_file(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
        outline: list[OutlineNode],
    ) -> str:
        title = requirements.draft_title or requirements.topic_direction or "待确认题目"
        lines = [
            "# 论文大纲",
            "",
            "本文件由 planning 管线自动生成，用于给用户确认大纲后再进入正文写作。",
            "",
            "## 当前论文信息",
            "",
            f"- 最终题目：{title}",
            f"- 论文类型：{requirements.paper_type or '待进一步确认'}",
            f"- 目标字数：{requirements.target_words or 5000}",
            f"- 当前资料数量：{len(sources)}",
            f"- 模板要求是否已确认：{'是' if requirements.has_template else '否'}",
            "",
            "## 大纲草案",
            "",
        ]
        for index, node in enumerate(outline, start=1):
            cn_index = self._to_cn_index(index)
            allowed = "、".join(node.allowed_source_ids) if node.allowed_source_ids else "待补资料"
            lines.extend(
                [
                    f"### {cn_index}、{node.title}",
                    "",
                    f"- 本章目标：{node.goal}",
                    f"- 主要内容：围绕本章目标，优先使用已分配文献组织材料。",
                    f"- 建议字数：{node.target_words or ''}",
                    f"- 可用文献：{allowed}",
                    f"- 风险提示：{node.notes or '当前无明显结构性风险。'}",
                    "",
                ]
            )

        lines.extend(
            [
                "## 用户确认项",
                "",
                "1. 这个结构是否符合课程论文习惯。",
                "2. 哪一章需要加强。",
                "3. 是否需要删减章节。",
                "4. 是否要突出某个特定观点。",
                "",
                "## agent 输出要求",
                "",
                "- 当前大纲是否已经适合进入写作阶段。",
                "- 哪些章节资料充分。",
                "- 哪些章节建议补资料。",
                "- 如果用户认可，下一步将开始写哪一章。",
            ]
        )
        return "\n".join(lines) + "\n"

    def _write_markdown(self, output_path: Path, content: str) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def _write_json(self, output_path: Path, payload: object) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _to_cn_index(self, index: int) -> str:
        mapping = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八"}
        return mapping.get(index, str(index))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate planning documents for the paper project.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument("--course-name", default="", help="Optional course name override.")
    parser.add_argument("--topic-direction", default="", help="Optional topic direction override.")
    parser.add_argument("--draft-title", default="", help="Optional draft title override.")
    parser.add_argument("--target-words", type=int, default=0, help="Optional target word count override.")
    parser.add_argument("--paper-type", default="", help="Optional paper type override.")
    parser.add_argument("--has-template", action="store_true", help="Mark that a formal template is available.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = PlanningPipeline()
    summary = pipeline.run(
        project_root=Path(args.project_root),
        course_name=args.course_name,
        topic_direction=args.topic_direction,
        draft_title=args.draft_title,
        target_words=args.target_words or None,
        paper_type=args.paper_type,
        has_template=args.has_template,
    )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
