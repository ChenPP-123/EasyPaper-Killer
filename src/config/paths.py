from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    root: Path

    def ensure_runtime_dirs(self) -> None:
        self.parsed_references_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"

    @property
    def template_dir(self) -> Path:
        return self.root / "template"

    @property
    def input_dir(self) -> Path:
        return self.root / "input"

    @property
    def raw_references_dir(self) -> Path:
        return self.input_dir / "references" / "raw"

    @property
    def raw_pdf_dir(self) -> Path:
        return self.raw_references_dir / "pdf"

    @property
    def parsed_references_dir(self) -> Path:
        return self.input_dir / "references" / "parsed"

    @property
    def sources_file(self) -> Path:
        return self.parsed_references_dir / "sources.json"

    @property
    def evidence_file(self) -> Path:
        return self.parsed_references_dir / "evidence.json"

    @property
    def references_file(self) -> Path:
        return self.parsed_references_dir / "references.json"

    @property
    def workspace_root_dir(self) -> Path:
        return self.root / "workspace"

    @property
    def archive_dir(self) -> Path:
        return self.workspace_root_dir / "archive"

    @property
    def workspace_dir(self) -> Path:
        return self.workspace_root_dir / "当前项目"

    @property
    def template_constraint_file(self) -> Path:
        return self.workspace_dir / "00_模版要求.md"

    @property
    def topic_refinement_file(self) -> Path:
        return self.workspace_dir / "01_选题收敛.md"

    @property
    def query_file(self) -> Path:
        return self.workspace_dir / "02_检索式.md"

    @property
    def material_review_file(self) -> Path:
        return self.workspace_dir / "03_资料盘点.md"

    @property
    def outline_file(self) -> Path:
        return self.workspace_dir / "04_论文大纲.md"

    @property
    def section_plan_file(self) -> Path:
        return self.workspace_dir / "05_章节写作计划.md"

    @property
    def draft_file(self) -> Path:
        return self.workspace_dir / "06_正文草稿.md"

    @property
    def numbered_draft_file(self) -> Path:
        return self.workspace_dir / "06_正文草稿_引用整理版.md"

    @property
    def abstract_keywords_file(self) -> Path:
        return self.workspace_dir / "07_摘要与关键词.md"

    @property
    def reference_list_file(self) -> Path:
        return self.workspace_dir / "08_参考文献列表.md"

    @property
    def qa_report_file(self) -> Path:
        return self.workspace_dir / "09_校验报告.md"

    @property
    def prompt_dir(self) -> Path:
        return self.workspace_dir / "prompts"

    @property
    def section_draft_dir(self) -> Path:
        return self.workspace_dir / "section_drafts"

    @property
    def outline_json_file(self) -> Path:
        return self.workspace_dir / "04_论文大纲.json"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"
