from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceStatus(str, Enum):
    FORMAL = "formal"
    CANDIDATE = "candidate"
    DISCARDED = "discarded"


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    WEAK = "weak"
    UNSUPPORTED = "unsupported"


class WorkflowStage(str, Enum):
    TASK_INTAKE = "task_intake"
    QUERY_PREPARATION = "query_preparation"
    WAITING_FOR_MATERIALS = "waiting_for_materials"
    MATERIAL_REVIEW = "material_review"
    OUTLINE_CONFIRMATION = "outline_confirmation"
    SECTION_WRITING = "section_writing"
    FINALIZATION = "finalization"


@dataclass(slots=True)
class TaskRequirements:
    course_name: str = ""
    topic_direction: str = ""
    draft_title: str = ""
    target_words: int | None = None
    deadline: str = ""
    paper_type: str = ""
    need_abstract: bool = True
    need_keywords: bool = True
    need_english_abstract: bool = False
    need_acknowledgements: bool = False
    has_template: bool = False
    extra_requirements: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceRecord:
    source_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    journal: str = ""
    source_type: str = "journal"
    cnki_url: str = ""
    abstract: str = ""
    citation_text_raw: str = ""
    reference_text_raw: str = ""
    file_paths: list[str] = field(default_factory=list)
    status: SourceStatus = SourceStatus.FORMAL


@dataclass(slots=True)
class EvidenceChunk:
    chunk_id: str
    source_id: str
    text: str
    location: str = ""
    evidence_type: str = "abstract_summary"
    confidence: str = "high"


@dataclass(slots=True)
class OutlineNode:
    section_id: str
    title: str
    goal: str
    allowed_source_ids: list[str] = field(default_factory=list)
    target_words: int | None = None
    notes: str = ""


@dataclass(slots=True)
class ClaimUnit:
    claim_id: str
    section_id: str
    text: str
    supporting_source_ids: list[str] = field(default_factory=list)
    supporting_chunk_ids: list[str] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.SUPPORTED


@dataclass(slots=True)
class TemplateSpec:
    template_name: str
    required_sections: list[str] = field(default_factory=list)
    heading_rules: dict[str, str] = field(default_factory=dict)
    body_font_rule: str = ""
    line_spacing_rule: str = ""
    reference_style_rule: str = "GB/T 7714-2015"
    abstract_font_rule: str = ""
    keywords_font_rule: str = ""
    citation_superscript: bool = True


@dataclass(slots=True)
class AgentInstruction:
    current_stage: WorkflowStage
    completed_work: list[str] = field(default_factory=list)
    current_issues: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    file_targets: list[str] = field(default_factory=list)
    completion_reply: str = ""


@dataclass(slots=True)
class WorkflowContext:
    requirements: TaskRequirements = field(default_factory=TaskRequirements)
    stage: WorkflowStage = WorkflowStage.TASK_INTAKE
    sources: list[SourceRecord] = field(default_factory=list)
    evidence_chunks: list[EvidenceChunk] = field(default_factory=list)
    outline: list[OutlineNode] = field(default_factory=list)
    claims: list[ClaimUnit] = field(default_factory=list)
    template_spec: TemplateSpec | None = None
