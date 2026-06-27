from __future__ import annotations

import re
from pathlib import Path

from src.models import TaskRequirements


class RequirementsLoader:
    """Loads task requirements from the project markdown template."""

    _LINE_PATTERN = re.compile(r"^-\s*(?P<key>[^：:]+)[：:]\s*(?P<value>.*)$")

    _FIELD_MAP = {
        "课程名称": "course_name",
        "论文方向": "topic_direction",
        "当前初始题目": "draft_title",
        "目标字数": "target_words",
        "截止时间": "deadline",
        "论文类型": "paper_type",
        "是否需要摘要": "need_abstract",
        "是否需要关键词": "need_keywords",
        "是否需要英文摘要": "need_english_abstract",
        "是否需要致谢": "need_acknowledgements",
        "是否已有学校或课程模板": "has_template",
    }

    _EXTRA_FIELDS = {
        "希望 agent 帮我做的重点",
        "老师特别强调的要求",
        "明确不能写的内容",
        "倾向保守写法还是希望更有观点",
        "其他说明",
    }

    def load(self, file_path: Path) -> TaskRequirements:
        if not file_path.exists():
            return TaskRequirements()

        requirements = TaskRequirements()
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            match = self._LINE_PATTERN.match(raw_line.strip())
            if not match:
                continue

            key = match.group("key").strip()
            value = match.group("value").strip()
            if not value:
                continue

            field_name = self._FIELD_MAP.get(key)
            if field_name:
                setattr(requirements, field_name, self._coerce_value(field_name, value))
                continue

            if key in self._EXTRA_FIELDS:
                requirements.extra_requirements.append(f"{key}：{value}")

        return requirements

    def with_overrides(self, requirements: TaskRequirements, **overrides: object) -> TaskRequirements:
        for key, value in overrides.items():
            if value in (None, ""):
                continue
            if hasattr(requirements, key):
                setattr(requirements, key, value)
        return requirements

    def _coerce_value(self, field_name: str, value: str) -> object:
        if field_name == "target_words":
            digits = re.sub(r"\D", "", value)
            return int(digits) if digits else None

        if field_name.startswith("need_") or field_name == "has_template":
            if value in {"是", "需要", "有", "true", "True"}:
                return True
            if value in {"否", "不需要", "无", "false", "False"}:
                return False

        # Skip the template placeholder string when no specific type was chosen.
        if field_name == "paper_type" and "/" in value:
            return ""

        return value
