from __future__ import annotations

from dataclasses import dataclass
import re

from src.models import SourceRecord, TaskRequirements


@dataclass(slots=True)
class TopicOption:
    title: str
    rationale: str
    risk: str


@dataclass(slots=True)
class QueryPlan:
    base_topic: str
    core_terms: list[str]
    related_terms: list[str]
    search_queries: list[str]
    screening_tips: list[str]


class TopicPlanner:
    """Builds narrower paper topics and search queries."""

    _GENERIC_STOPWORDS = {
        "研究",
        "分析",
        "现状",
        "对策",
        "建议",
        "综述",
        "展望",
        "时期",
        "背景",
        "问题",
        "技术",
        "发展",
        "路径",
    }

    def refine_topic(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord] | None = None,
    ) -> list[TopicOption]:
        base_topic = self._derive_base_topic(requirements, sources or [])
        theme_terms = self._derive_theme_terms(base_topic, sources or [])
        focus = self._strip_title_suffix(theme_terms[0] if theme_terms else base_topic)
        background = theme_terms[1:3]
        background_text = "、".join(background) if background else "课程要求与现有文献"
        paper_type = self._normalize_paper_type(requirements, sources or [])

        if paper_type == "policy":
            return [
                TopicOption(
                    title=f"{focus}的现状、问题与对策研究",
                    rationale="结构清晰，最适合课程论文的标准三段式展开。",
                    risk="如果政策或案例文献不足，问题与对策部分容易空泛。",
                ),
                TopicOption(
                    title=f"{focus}在{background_text}背景下的优化路径分析",
                    rationale="能把宏观背景和具体问题绑在一起，容易形成完整论证。",
                    risk="背景铺陈过多时，正文主体容易失衡。",
                ),
                TopicOption(
                    title=f"基于文献资料的{focus}成效与改进方向探讨",
                    rationale="更适合现有资料以综述和政策评述为主的情况。",
                    risk="需要控制措辞，避免把综述写成主观评论。",
                ),
            ]

        if paper_type == "review":
            return [
                TopicOption(
                    title=f"{focus}研究现状综述",
                    rationale="题目最稳，和文献综述型写法高度匹配。",
                    risk="如果只罗列资料，容易缺少结构层次。",
                ),
                TopicOption(
                    title=f"{focus}的研究进展、主要问题与发展展望",
                    rationale="自然对应综述论文常见的三段式结构。",
                    risk="需要保证“问题”和“展望”都能找到文献支撑。",
                ),
                TopicOption(
                    title=f"{focus}相关研究的核心议题与趋势分析",
                    rationale="适合想让论文看起来更像整理研究脉络的写法。",
                    risk="如果资料范围较窄，趋势分析部分会偏弱。",
                ),
            ]

        return [
            TopicOption(
                title=f"{focus}的现状分析与优化建议",
                rationale="适合大部分课程论文，题目明确且容易展开。",
                risk="需要避免“现状”和“建议”两部分比例失衡。",
            ),
            TopicOption(
                title=f"{focus}的主要问题与改进路径研究",
                rationale="更强调问题意识，适合老师偏好分析型写法的场景。",
                risk="如果问题证据不足，改进路径会显得牵强。",
            ),
            TopicOption(
                title=f"{focus}相关研究的阶段性进展与趋势探讨",
                rationale="更接近轻综述写法，适合资料以论文摘要和综述材料为主的情况。",
                risk="需要避免写成简单摘要拼接。",
            ),
        ]

    def build_cnki_query(
        self,
        requirements: TaskRequirements,
        sources: list[SourceRecord] | None = None,
    ) -> QueryPlan:
        base_topic = self._derive_base_topic(requirements, sources or [])
        theme_terms = self._derive_theme_terms(base_topic, sources or [])
        core_terms = theme_terms[:3] or [base_topic]
        related_terms = self._derive_related_terms(base_topic, requirements, sources or [])

        query_one = self._format_cnki_query(core_terms[:2], related_terms[:2])
        query_two = self._format_cnki_query(core_terms[:1], related_terms[:4])
        query_three = self._format_cnki_query(core_terms[:3], [])

        screening_tips = [
            "优先保留题目和摘要都直接围绕核心主题的论文。",
            "优先选择近 5 年文献，但保留 1-2 篇较早的代表性综述或政策基础文献。",
            "如果题目偏对策建议，至少补充 2-3 篇能直接支撑“问题成因”或“政策效果”的文献。",
            "下载 PDF 的同时，保留查新引文和参考文献文本，方便后续自动入库。",
        ]

        return QueryPlan(
            base_topic=base_topic,
            core_terms=core_terms,
            related_terms=related_terms,
            search_queries=[query_one, query_two, query_three],
            screening_tips=screening_tips,
        )

    def _derive_base_topic(self, requirements: TaskRequirements, sources: list[SourceRecord]) -> str:
        for candidate in (requirements.draft_title, requirements.topic_direction):
            if candidate.strip():
                return self._clean_topic(candidate)
        if sources:
            return self._clean_topic(sources[0].title)
        return "课程论文主题"

    def _derive_theme_terms(self, base_topic: str, sources: list[SourceRecord]) -> list[str]:
        candidates = [base_topic]
        candidates.extend(source.title for source in sources[:6])

        phrases: list[str] = []
        for text in candidates:
            cleaned = self._clean_topic(text)
            if cleaned:
                phrases.append(cleaned)
            phrases.extend(self._extract_fragments(text))

        return self._dedupe_preserve_order([term for term in phrases if len(term) >= 2])[:6]

    def _derive_related_terms(
        self,
        base_topic: str,
        requirements: TaskRequirements,
        sources: list[SourceRecord],
    ) -> list[str]:
        terms = self._derive_theme_terms(base_topic, sources)
        paper_type = self._normalize_paper_type(requirements, sources)
        if paper_type == "policy":
            terms.extend(["政策", "路径", "成效", "问题"])
        elif paper_type == "review":
            terms.extend(["进展", "综述", "趋势", "挑战"])
        else:
            terms.extend(["现状", "问题", "优化", "发展"])
        return self._dedupe_preserve_order(terms)[1:7]

    def _normalize_paper_type(self, requirements: TaskRequirements, sources: list[SourceRecord]) -> str:
        explicit = requirements.paper_type.strip()
        if explicit:
            if any(keyword in explicit for keyword in ["综述", "进展", "展望"]):
                return "review"
            if any(keyword in explicit for keyword in ["对策", "建议", "路径", "成效"]):
                return "policy"

        text = " ".join(part for part in [requirements.draft_title, requirements.topic_direction] if part)
        if any(keyword in text for keyword in ["综述", "进展", "展望"]):
            return "review"
        if any(keyword in text for keyword in ["对策", "建议", "路径", "成效"]):
            return "policy"
        return "analysis"

    def _format_cnki_query(self, left_terms: list[str], right_terms: list[str]) -> str:
        left = "+".join(f"'{term}'" for term in left_terms if term)
        right = "+".join(f"'{term}'" for term in right_terms if term)
        if left and right:
            return f"TKA=({left})*({right})"
        return f"TKA=({left or right})"

    def _extract_fragments(self, text: str) -> list[str]:
        normalized = self._clean_topic(text)
        parts = re.split(r"[、，,：:（）()\-\s]|与|和|及|的", normalized)
        fragments = []
        for part in parts:
            part = part.strip()
            if len(part) < 2:
                continue
            if part in self._GENERIC_STOPWORDS:
                continue
            fragments.append(part)
        return fragments

    def _clean_topic(self, text: str) -> str:
        text = re.sub(r"[“”\"]", "", text)
        return re.sub(r"\s+", " ", text).strip(" .。；;，,")

    def _strip_title_suffix(self, text: str) -> str:
        return re.sub(r"(研究|分析|综述|探讨)$", "", text).strip()

    def _dedupe_preserve_order(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result
