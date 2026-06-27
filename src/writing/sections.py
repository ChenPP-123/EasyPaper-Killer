from __future__ import annotations

from dataclasses import dataclass, field
import math
import re

from src.models import ClaimUnit, EvidenceChunk, OutlineNode, SourceRecord, TaskRequirements


@dataclass(slots=True)
class SectionDraft:
    section_id: str
    title: str
    body: str
    claims: list[ClaimUnit] = field(default_factory=list)


@dataclass(slots=True)
class SectionPromptPacket:
    section_id: str
    title: str
    target_words: int
    chunk_batch_count: int
    allowed_source_ids: list[str] = field(default_factory=list)
    evidence_chunks: list[EvidenceChunk] = field(default_factory=list)
    prompt_text: str = ""
    warning_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DraftBatch:
    batch_id: str
    chunk_ids: list[str]
    prompt_text: str


@dataclass(slots=True)
class SectionGenerationPlan:
    section_id: str
    title: str
    target_words: int
    batch_word_target: int
    packets: list[SectionPromptPacket] = field(default_factory=list)
    next_action: str = ""


class SectionWriter:
    """Builds model-facing section packets with hard evidence constraints."""

    def __init__(self, max_chunks_per_batch: int = 4) -> None:
        self.max_chunks_per_batch = max_chunks_per_batch

    def plan_section(
        self,
        outline_node: OutlineNode,
        evidence_chunks: list[EvidenceChunk],
        sources: list[SourceRecord],
        requirements: TaskRequirements,
    ) -> SectionGenerationPlan:
        relevant_chunks = self._select_relevant_chunks(outline_node, evidence_chunks)
        if not relevant_chunks:
            packet = SectionPromptPacket(
                section_id=outline_node.section_id,
                title=outline_node.title,
                target_words=outline_node.target_words or 600,
                chunk_batch_count=0,
                allowed_source_ids=outline_node.allowed_source_ids,
                evidence_chunks=[],
                prompt_text=self._build_empty_prompt(outline_node, requirements),
                warning_notes=["当前没有可直接使用的证据块，本章应暂停写作并先补资料。"],
            )
            return SectionGenerationPlan(
                section_id=outline_node.section_id,
                title=outline_node.title,
                target_words=outline_node.target_words or 600,
                batch_word_target=outline_node.target_words or 600,
                packets=[packet],
                next_action="暂停本章写作，提示用户补充与本章目标直接相关的文献。",
            )

        batches = self._split_batches(relevant_chunks)
        batch_word_target = max(180, math.ceil((outline_node.target_words or 600) / max(1, len(batches))))
        packets: list[SectionPromptPacket] = []
        for index, batch in enumerate(batches, start=1):
            prompt = self._build_section_prompt(
                outline_node=outline_node,
                batch_chunks=batch,
                sources=sources,
                requirements=requirements,
                batch_index=index,
                batch_count=len(batches),
                batch_word_target=batch_word_target,
            )
            warning_notes = []
            if len(outline_node.allowed_source_ids) < 2:
                warning_notes.append("本章授权文献偏少，生成时要减少横向扩展和绝对化判断。")
            packets.append(
                SectionPromptPacket(
                    section_id=outline_node.section_id,
                    title=outline_node.title,
                    target_words=outline_node.target_words or 600,
                    chunk_batch_count=len(batches),
                    allowed_source_ids=outline_node.allowed_source_ids,
                    evidence_chunks=batch,
                    prompt_text=prompt,
                    warning_notes=warning_notes,
                )
            )

        next_action = "按批次把 prompt 交给模型生成，再将每批结果顺序合并为本章草稿。"
        if len(batches) > 1:
            next_action += " 不要一次性要求模型生成整章全文。"

        return SectionGenerationPlan(
            section_id=outline_node.section_id,
            title=outline_node.title,
            target_words=outline_node.target_words or 600,
            batch_word_target=batch_word_target,
            packets=packets,
            next_action=next_action,
        )

    def write_section(
        self,
        outline_node: OutlineNode,
        evidence_chunks: list[EvidenceChunk],
        sources: list[SourceRecord],
        requirements: TaskRequirements,
    ) -> SectionDraft:
        plan = self.plan_section(outline_node, evidence_chunks, sources, requirements)
        placeholders = []
        for index, packet in enumerate(plan.packets, start=1):
            chunk_ids = "、".join(chunk.chunk_id for chunk in packet.evidence_chunks) or "无"
            placeholders.extend(
                [
                    f"#### 批次 {index}",
                    "",
                    f"[待模型生成：本批目标约 {plan.batch_word_target} 字；证据块：{chunk_ids}]",
                    "",
                ]
            )

        return SectionDraft(
            section_id=outline_node.section_id,
            title=outline_node.title,
            body="\n".join(placeholders).strip(),
            claims=[],
        )

    def _select_relevant_chunks(
        self,
        outline_node: OutlineNode,
        evidence_chunks: list[EvidenceChunk],
    ) -> list[EvidenceChunk]:
        allowed = set(outline_node.allowed_source_ids)
        filtered = [chunk for chunk in evidence_chunks if chunk.source_id in allowed]
        if not filtered:
            return []

        preferred = []
        backup = []
        section_terms = self._extract_terms(outline_node.title + " " + outline_node.goal)
        for chunk in filtered:
            chunk_terms = self._extract_terms(chunk.text)
            if section_terms & chunk_terms:
                preferred.append(chunk)
            else:
                backup.append(chunk)
        return preferred + backup

    def _split_batches(self, evidence_chunks: list[EvidenceChunk]) -> list[list[EvidenceChunk]]:
        if not evidence_chunks:
            return []
        return [
            evidence_chunks[index : index + self.max_chunks_per_batch]
            for index in range(0, len(evidence_chunks), self.max_chunks_per_batch)
        ]

    def _build_section_prompt(
        self,
        outline_node: OutlineNode,
        batch_chunks: list[EvidenceChunk],
        sources: list[SourceRecord],
        requirements: TaskRequirements,
        batch_index: int,
        batch_count: int,
        batch_word_target: int,
    ) -> str:
        source_map = {source.source_id: source for source in sources}
        evidence_lines = []
        for chunk in batch_chunks:
            source = source_map.get(chunk.source_id)
            source_title = source.title if source else chunk.source_id
            evidence_lines.append(
                f"- 证据块 {chunk.chunk_id} | 来源 {chunk.source_id} | 标题：{source_title} | 内容：{chunk.text}"
            )

        section_type = self._classify_section_type(outline_node)
        citation_rules = self._citation_rules_for(section_type, batch_word_target)

        style_lines = [
            "使用课程论文常见的学术表达，避免口语化。",
            "允许模型组织语言，但不允许超出证据块自行添加新事实。",
            "如果证据只能支持弱结论，应使用保守措辞，例如“表明”“显示”“可以看出”。",
            "本批次只写本章的一部分，不要总结整篇论文。",
        ]
        if requirements.paper_type:
            style_lines.append(f"当前论文类型为：{requirements.paper_type}。段落组织应与该类型一致。")

        return "\n".join(
            [
                f"你正在写课程论文的一个章节片段：{outline_node.title}",
                f"章节目标：{outline_node.goal}",
                f"本章定位：{section_type}",
                f"这是本章第 {batch_index}/{batch_count} 个生成批次，目标字数约 {batch_word_target} 字。",
                "",
                "硬约束：",
                "- 只能使用下面给出的证据块，不要编造新数据、新政策或新结论。",
                "- 不要写摘要、结论或其他章节内容。",
                "- 不要输出项目符号列表，直接输出自然段正文。",
                "- 不要伪造参考文献编号，引用位置仅用 [SRC-xxx] 临时占位。",
                "",
                "引用密度规则：",
                *[f"- {rule}" for rule in citation_rules],
                "",
                "写作风格要求：",
                *[f"- {line}" for line in style_lines],
                "",
                "可用证据：",
                *evidence_lines,
                "",
                "输出要求：",
                "- 输出 2-4 个自然段。",
                "- 每个自然段尽量体现清晰的小层次。",
                "- 在使用某条证据形成判断时，在句末附上 [SRC-xxx]。",
                "- 如果证据不足以支撑更强结论，就停留在可证实的层面。",
            ]
        )

    def _classify_section_type(self, outline_node: OutlineNode) -> str:
        title = outline_node.title
        if any(kw in title for kw in ["引言", "背景"]):
            return "intro"
        if any(kw in title for kw in ["结论", "总结"]):
            return "conclusion"
        return "body"

    def _citation_rules_for(self, section_type: str, batch_word_target: int) -> list[str]:
        if section_type == "intro":
            budget = max(1, batch_word_target // 200)
            return [
                f"本章定位为引言/背景，可以较密集地引用文献来交代研究背景和问题意识。",
                f"本批次大致允许 {budget}-{budget+1} 处引用，但不要句句都挂引用编号。",
                "引用的作用是让读者知道判断来自何处，不是让每一行变成文献笔记。",
            ]
        if section_type == "conclusion":
            return [
                "本章定位为结论/总结，以你自己的分析归纳为主。",
                "除非必须回扣某个明确事实或数据，否则不要密集插入引用。",
                "不要在结论段里新推出一堆引用文献，结论应体现出对全文的提炼而不是把前面引用的文献再抄一遍。",
            ]
        return [
            "本章定位为主体分析，以你自己的整合分析为主，文献只是辅助证据。",
            "只在关键判断、明确数据和重要结论处附上 [SRC-xxx]。",
            "不要句句挂引用。如果你发现自己每一句话后面都写了一个 [SRC-xxx]，说明你在做文献摘编，不是在做有观点的分析。",
        ]

    def _classify_section_by_index(self, section_id: str, total_sections: int) -> str:
        try:
            num = int(section_id.replace("SEC-", ""))
        except ValueError:
            return "body"
        if num == 1:
            return "intro"
        if num == total_sections:
            return "conclusion"
        return "body"

    def _build_empty_prompt(self, outline_node: OutlineNode, requirements: TaskRequirements) -> str:
        return "\n".join(
            [
                f"当前章节：{outline_node.title}",
                f"章节目标：{outline_node.goal}",
                f"论文类型：{requirements.paper_type or '未指定'}",
                "当前没有足够证据块支持本章写作。不要生成正文，请先提示用户补资料。",
            ]
        )

    def _extract_terms(self, text: str) -> set[str]:
        normalized = re.sub(r"[“”\"（）()，,。；;：:\-]", " ", text)
        parts = re.split(r"\s+|与|和|及|的|在|对|并", normalized)
        return {part.strip() for part in parts if len(part.strip()) >= 2}
