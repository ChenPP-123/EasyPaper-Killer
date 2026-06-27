from __future__ import annotations

import re

from src.models import OutlineNode, SourceRecord, TaskRequirements


class OutlinePlanner:
    """Creates section plans that stay within the available evidence."""

    def build_outline(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
    ) -> list[OutlineNode]:
        total_words = requirements.target_words or 5000
        paper_type = self._normalize_paper_type(requirements, sources)
        relevant_sources = self._filter_relevant_sources(requirements, sources)
        section_blueprints = self._build_section_blueprints(paper_type)
        word_plan = self._allocate_words(total_words, len(section_blueprints))

        outline: list[OutlineNode] = []
        for index, blueprint in enumerate(section_blueprints, start=1):
            allowed_ids = self._select_sources_for_section(blueprint["title"], blueprint["goal"], relevant_sources)
            notes = []
            if not allowed_ids:
                notes.append("当前资料中缺少直接支撑本章的文献，建议补资料。")
            elif len(allowed_ids) < 2:
                notes.append("本章可用文献较少，写作时需要控制论断力度。")

            outline.append(
                OutlineNode(
                    section_id=f"SEC-{index:02d}",
                    title=blueprint["title"],
                    goal=blueprint["goal"],
                    allowed_source_ids=allowed_ids,
                    target_words=word_plan[index - 1],
                    notes=" ".join(notes),
                )
            )

        return outline

    def _normalize_paper_type(self, requirements: TaskRequirements, sources: list[SourceRecord]) -> str:
        explicit = requirements.paper_type.strip()
        if explicit:
            if any(keyword in explicit for keyword in ["综述", "进展", "展望"]):
                return "review"
            if any(keyword in explicit for keyword in ["对策", "建议", "成效", "路径"]):
                return "policy"

        text = " ".join(part for part in [requirements.draft_title, requirements.topic_direction] if part)
        if any(keyword in text for keyword in ["综述", "进展", "展望"]):
            return "review"
        if any(keyword in text for keyword in ["对策", "建议", "成效", "路径"]):
            return "policy"
        return "analysis"

    def _filter_relevant_sources(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
    ) -> list[SourceRecord]:
        topic_text = " ".join(part for part in [requirements.draft_title, requirements.topic_direction] if part)
        if not topic_text.strip():
            return sources

        relevant = []
        for source in sources:
            source_text = source.title + " " + source.abstract
            if self._has_topic_overlap(topic_text, source_text):
                relevant.append(source)
        return relevant or sources

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
        cleaned = re.sub(r"[“”\"（）()，,。；;：:\-]", " ", text)
        parts = re.split(r"\s+|与|和|及|的|在|基于", cleaned)
        phrases = [part.strip() for part in parts if len(part.strip()) >= 4]
        return phrases

    def _build_section_blueprints(self, paper_type: str) -> list[dict[str, str]]:
        if paper_type == "review":
            return [
                {"title": "引言", "goal": "说明选题背景、研究意义和论文结构。"},
                {"title": "核心概念与研究背景", "goal": "界定核心概念，并交代研究问题所处背景。"},
                {"title": "研究现状与文献综述主体", "goal": "按主题梳理现有研究的主要观点、路径和阶段性进展。"},
                {"title": "现有研究的不足与主要挑战", "goal": "总结文献中暴露的争议、缺口和现实挑战。"},
                {"title": "发展趋势与进一步研究方向", "goal": "在已有研究基础上提炼未来趋势与改进方向。"},
                {"title": "结论", "goal": "总结全文核心结论，收束论文。"},
            ]

        if paper_type == "policy":
            return [
                {"title": "引言", "goal": "说明选题背景、现实意义和论文安排。"},
                {"title": "政策背景与分析框架", "goal": "交代相关背景、核心概念和分析切入点。"},
                {"title": "当前现状与阶段性成效", "goal": "梳理当前发展现状、主要成绩或已有进展。"},
                {"title": "主要问题及成因分析", "goal": "概括现实问题，并分析形成这些问题的主要原因。"},
                {"title": "优化路径与对策建议", "goal": "提出与问题对应的改进方向和对策建议。"},
                {"title": "结论", "goal": "对全文进行收束并总结。"},
            ]

        return [
            {"title": "引言", "goal": "说明选题背景、研究意义和文章结构。"},
            {"title": "核心概念与研究背景", "goal": "交代核心概念和本题所处背景。"},
            {"title": "现状分析", "goal": "梳理主题当前的发展情况、主要表现和阶段性特点。"},
            {"title": "问题与挑战", "goal": "总结当前存在的主要问题、难点和限制因素。"},
            {"title": "优化方向与发展展望", "goal": "提出可行的优化方向并总结未来发展趋势。"},
            {"title": "结论", "goal": "回收全文要点，给出整体判断。"},
        ]

    def _allocate_words(self, total_words: int, section_count: int) -> list[int]:
        weights = [0.10, 0.15, 0.30, 0.20, 0.15, 0.10][:section_count]
        if len(weights) < section_count:
            weights.extend([1 / section_count] * (section_count - len(weights)))

        allocated = [max(200, int(total_words * weight)) for weight in weights]
        diff = total_words - sum(allocated)
        allocated[-1] += diff
        return allocated

    def _select_sources_for_section(
        self,
        section_title: str,
        section_goal: str,
        sources: list[SourceRecord],
    ) -> list[str]:
        if not sources:
            return []

        section_terms = self._extract_terms(section_title + " " + section_goal)
        scored_sources: list[tuple[int, int, SourceRecord]] = []
        for index, source in enumerate(sources):
            source_terms = self._extract_terms(source.title + " " + source.abstract)
            overlap = len(section_terms & source_terms)
            abstract_bonus = 1 if source.abstract else 0
            scored_sources.append((overlap, abstract_bonus, source))

        scored_sources.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [item[2].source_id for item in scored_sources if item[0] > 0][:4]

        if selected:
            return selected
        if len(sources) <= 4:
            return [source.source_id for source in sources]
        return [source.source_id for source in sources[:3]]

    def _extract_terms(self, text: str) -> set[str]:
        normalized = re.sub(r"[“”\"（）()，,。；;：:\-]", " ", text)
        parts = re.split(r"\s+|与|和|及|的", normalized)
        terms = {part.strip() for part in parts if len(part.strip()) >= 2}
        return {term for term in terms if term not in {"研究", "分析", "现状", "问题", "背景", "结论"}}
