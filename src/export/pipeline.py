from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths
from src.export.docx import DocxExporter, ExportPayload
from src.models import TemplateSpec
from src.planning.requirements import RequirementsLoader


@dataclass(slots=True)
class ExportSummary:
    keyword_count: int
    section_count: int
    generated_files: list[str]


class SummaryGenerator:
    _STOPWORDS = {
        "研究",
        "分析",
        "现状",
        "问题",
        "对策",
        "建议",
        "时期",
        "工作",
        "论文",
        "进行",
        "本文",
        "当前",
    }

    def build_abstract(self, title: str, sections: list[tuple[str, str]]) -> str:
        section_map = {name: body for name, body in sections}
        intro = self._first_sentence(section_map.get("引言", ""))
        achievements = self._first_sentence(section_map.get("当前现状与阶段性成效", ""))
        problems = self._first_sentence(section_map.get("主要问题及成因分析", ""))
        conclusion = self._last_sentence(section_map.get("结论", ""))

        parts = [
            f"本文围绕《{title}》这一主题，在已有文献基础上对相关问题进行了梳理和讨论。",
        ]
        for sentence in [intro, achievements, problems, conclusion]:
            cleaned = self._clean_sentence(sentence)
            if cleaned and cleaned not in parts:
                parts.append(cleaned)
        return "".join(parts)

    def build_keywords(self, title: str, sections: list[tuple[str, str]]) -> list[str]:
        keywords: list[str] = []
        title_parts = re.split(r"与|和|及", title)
        for part in title_parts:
            cleaned = self._normalize_keyword(part)
            if cleaned and cleaned not in keywords:
                keywords.append(cleaned)

        section_text = " ".join(body for _, body in sections)
        for preferred in ["碳达峰", "节能降碳", "能源结构转型", "产业转型升级", "绿色低碳发展"]:
            if preferred in section_text and preferred not in keywords:
                keywords.append(preferred)

        for phrase in self._extract_keywords(title + " " + section_text):
            normalized = self._normalize_keyword(phrase)
            if normalized and normalized not in keywords:
                keywords.append(normalized)
        return keywords[:5] or [title]

    def _first_sentence(self, text: str) -> str:
        parts = re.split(r"(?<=[。！？])", text)
        for part in parts:
            cleaned = self._clean_sentence(part)
            if cleaned:
                return cleaned
        return ""

    def _last_sentence(self, text: str) -> str:
        parts = [self._clean_sentence(part) for part in re.split(r"(?<=[。！？])", text)]
        parts = [part for part in parts if part]
        return parts[-1] if parts else ""

    def _clean_sentence(self, text: str) -> str:
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\s+", "", text)
        return text.strip()

    def _extract_keywords(self, text: str) -> list[str]:
        cleaned = re.sub(r"[《》“”\"\[\]（）()，,。；;：:0-9]+", " ", text)
        raw_parts = re.split(r"\s+|与|和|及|的|在|对|并|而|以", cleaned)
        phrases: list[str] = []
        for part in raw_parts:
            part = part.strip()
            if len(part) < 2 or part in self._STOPWORDS:
                continue
            if part not in phrases:
                phrases.append(part)
        return phrases

    def _normalize_keyword(self, text: str) -> str:
        text = re.sub(r"(研究|分析|探讨|现状|成效)$", "", text).strip()
        text = text.replace("十五五对策", "十五五时期对策")
        if text == "十五五":
            text = "十五五时期"
        return text.strip()


class ExportPipeline:
    def __init__(self) -> None:
        self.requirements_loader = RequirementsLoader()
        self.summary_generator = SummaryGenerator()
        self.exporter = DocxExporter()

    def run(self, project_root: Path) -> ExportSummary:
        paths = ProjectPaths(project_root.resolve())
        requirements = self.requirements_loader.load(paths.input_dir / "topic" / "任务需求.md")
        title = self._load_title(paths.outline_file) or requirements.draft_title or requirements.topic_direction or "论文初稿"
        sections = self._load_sections(paths.numbered_draft_file)
        references = self._load_references(paths.reference_list_file)

        abstract = self.summary_generator.build_abstract(title, sections)
        keywords = self.summary_generator.build_keywords(title, sections)
        self._write_abstract_file(paths.abstract_keywords_file, title, abstract, keywords)

        payload = ExportPayload(
            title=title,
            abstract=abstract,
            keywords=keywords,
            sections=sections,
            references=references,
        )
        template_name = self._select_template_name(paths.template_dir)
        output_path = paths.output_dir / "论文初稿.docx"
        self.exporter.export(
            payload,
            TemplateSpec(template_name=template_name),
            output_path,
        )

        validation_msg = self._validate_export(output_path)

        return ExportSummary(
            keyword_count=len(keywords),
            section_count=len(sections),
            generated_files=[
                str(paths.abstract_keywords_file),
                str(output_path),
            ],
        )

    def _validate_export(self, output_path: Path) -> str:
        try:
            from src.export.office import validate_docx
            return validate_docx(str(output_path))
        except Exception:
            return ""

    def _load_title(self, file_path: Path) -> str:
        if not file_path.exists():
            return ""
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- 最终题目："):
                return line.split("：", 1)[1].strip()
        return ""

    def _load_sections(self, file_path: Path) -> list[tuple[str, str]]:
        if not file_path.exists():
            return []
        lines = file_path.read_text(encoding="utf-8").splitlines()
        sections: list[tuple[str, list[str]]] = []
        current_title = ""
        current_body: list[str] = []
        for line in lines:
            if line.startswith("## ") and not line.startswith("## agent"):
                if current_title:
                    sections.append((current_title, current_body))
                current_title = line[3:].strip()
                current_body = []
                continue
            if not current_title:
                continue
            if line.startswith("#### 批次"):
                continue
            if line.startswith("本文件基于"):
                continue
            current_body.append(line)
        if current_title:
            sections.append((current_title, current_body))

        result: list[tuple[str, str]] = []
        for title, body_lines in sections:
            body = "\n".join(line for line in body_lines if line.strip()).strip()
            if title and body:
                result.append((title, body))
        return result

    def _load_references(self, file_path: Path) -> list[str]:
        if not file_path.exists():
            return []
        return [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

    def _write_abstract_file(self, file_path: Path, title: str, abstract: str, keywords: list[str]) -> None:
        lines = [
            "# 摘要与关键词",
            "",
            f"- 论文题目：{title}",
            "",
            "## 中文摘要",
            "",
            abstract,
            "",
            "## 中文关键词",
            "",
            "；".join(keywords),
            "",
        ]
        file_path.write_text("\n".join(lines), encoding="utf-8")

    def _select_template_name(self, template_dir: Path) -> str:
        templates = sorted(template_dir.glob("*.docx"))
        return templates[0].name if templates else "未提供模板"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate abstract/keywords and export a paper docx.")
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = ExportPipeline()
    summary = pipeline.run(Path(args.project_root))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
