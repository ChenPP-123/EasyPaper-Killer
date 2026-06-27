from __future__ import annotations

from pathlib import Path

from src.models import TemplateSpec


class TemplateParser:
    """Extracts reusable formatting rules from a user template."""

    def parse(self, template_path: Path) -> TemplateSpec:
        raise NotImplementedError
