"""Nature-style academic writing guidance router.

Loads writing fragments from static/ and references/ based on paper type,
section, language, and journal. Follows the routing protocol defined in the
nature-writing skill specification.

Usage from agent:
    from src.writing.nature import load_fragments
    fragments = load_fragments(paper_type='research', section='intro', language='zh-to-en')
    for fragment in fragments:
        print(fragment.content)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

SKILL_DIR = Path(__file__).parent

_MANIFEST: dict = {
    "always_load": [
        "static/core/stance.md",
        "static/core/workflow.md",
        "static/core/output-format.md",
    ],
    "axes": {
        "paper_type": {
            "values": {
                "research": "static/fragments/paper_type/research.md",
                "methods": "static/fragments/paper_type/methods.md",
                "hypothesis": "static/fragments/paper_type/hypothesis.md",
                "algorithmic": "static/fragments/paper_type/algorithmic.md",
                "review": "static/fragments/paper_type/review.md",
            },
            "default": "research",
            "multi": False,
        },
        "section": {
            "values": {
                "abstract": "static/fragments/section/abstract.md",
                "intro": "static/fragments/section/intro.md",
                "related-work": "static/fragments/section/related-work.md",
                "method": "static/fragments/section/method.md",
                "experiments": "static/fragments/section/experiments.md",
                "discussion": "static/fragments/section/discussion.md",
                "conclusion": "static/fragments/section/conclusion.md",
                "title": "static/fragments/section/title.md",
            },
            "multi": True,
        },
        "language": {
            "values": {
                "en": "static/fragments/language/en.md",
                "zh-to-en": "static/fragments/language/zh-to-en.md",
            },
            "default": "en",
            "multi": False,
        },
        "journal": {
            "values": {
                "nature": "static/fragments/journal/nature.md",
                "nat-comms": "static/fragments/journal/nat-comms.md",
                "generic": "static/fragments/journal/generic.md",
            },
            "default": "generic",
            "multi": False,
        },
    },
    "references": {
        "on_demand": [
            {
                "condition": "section-level structure, argument order, or published-article patterns",
                "path": "references/article-architecture.md",
            },
            {
                "condition": "drafting/revising abstract",
                "path": "references/abstract.md",
            },
            {
                "condition": "Nature-family broad-audience summary paragraph or introduction opening",
                "path": "references/nature-summary-paragraph.md",
            },
            {
                "condition": "drafting/revising introduction",
                "path": "references/introduction.md",
            },
            {
                "condition": "rebuilding related work as topic synthesis",
                "path": "references/related-work.md",
            },
            {
                "condition": "writing method sections",
                "path": "references/method.md",
            },
            {
                "condition": "planning/writing experiments",
                "path": "references/experiments.md",
            },
            {
                "condition": "writing conclusion",
                "path": "references/conclusion.md",
            },
            {
                "condition": "paragraph flow check",
                "path": "references/paragraph-flow.md",
            },
            {
                "condition": "final manuscript self-review",
                "path": "references/paper-review.md",
            },
            {
                "condition": "Chinese-author repair patterns",
                "path": "references/chinese-author-workflow.md",
            },
            {
                "condition": "concrete examples",
                "path": "references/examples/index.md",
            },
        ],
    },
}

try:
    import yaml
except ImportError:
    yaml = None


@dataclass(slots=True)
class Fragment:
    name: str
    path: str
    content: str


@dataclass(slots=True)
class LoadedFragments:
    paper_type: str
    section: str
    language: str
    journal: str
    core: list[Fragment] = field(default_factory=list)
    paper_type_frags: list[Fragment] = field(default_factory=list)
    section_frags: list[Fragment] = field(default_factory=list)
    language_frags: list[Fragment] = field(default_factory=list)
    journal_frags: list[Fragment] = field(default_factory=list)
    missing_shared: list[str] = field(default_factory=list)

    def all_content(self) -> list[str]:
        """Return all loaded fragment contents in priority order."""
        fragments = (
            self.core
            + self.paper_type_frags
            + self.section_frags
            + self.journal_frags
            + self.language_frags
        )
        return [f.content for f in fragments]

    def core_content(self) -> list[str]:
        return [f.content for f in self.core]


class NatureWritingRouter:
    """Load Nature-style writing fragments based on axis values."""

    def __init__(self, skill_dir: Path | None = None) -> None:
        self.skill_dir = Path(skill_dir) if skill_dir else SKILL_DIR
        self._manifest: dict | None = None

    def manifest(self) -> dict:
        if self._manifest is not None:
            return self._manifest
        manifest_path = self.skill_dir / "manifest.yaml"
        if manifest_path.exists():
            self._manifest = self._parse_manifest(manifest_path.read_text(encoding="utf-8"))
        else:
            self._manifest = _MANIFEST
        return self._manifest

    def _parse_manifest(self, content: str) -> dict:
        if yaml is not None:
            parsed = yaml.safe_load(content)
            if parsed:
                return parsed
        return _MANIFEST

    def load_fragments(
        self,
        paper_type: str = "research",
        section: str = "",
        language: str = "zh-to-en",
        journal: str = "generic",
    ) -> LoadedFragments:
        m = self.manifest()
        result = LoadedFragments(
            paper_type=paper_type,
            section=section,
            language=language,
            journal=journal,
        )

        always_load = m.get("always_load", [])
        for rel_path in always_load:
            frag_path = self._resolve_path(rel_path)
            if frag_path:
                content = self._read_file(frag_path)
                result.core.append(Fragment(name=rel_path, path=str(frag_path), content=content))
            elif rel_path.startswith("../_shared/"):
                result.missing_shared.append(rel_path)

        axes = m.get("axes", {})

        axis_attr_map = {
            "paper_type": "paper_type_frags",
            "section": "section_frags",
            "language": "language_frags",
            "journal": "journal_frags",
        }
        for axis_name, axis_def in axes.items():
            value = getattr(result, axis_name, "")
            if not value:
                continue
            paths = axis_def.get("values", {})
            frag_rel = paths.get(value)
            if frag_rel:
                frag = self._load_axis_fragment(axis_name, value, frag_rel)
                if frag:
                    attr_name = axis_attr_map.get(axis_name, "")
                    if attr_name:
                        getattr(result, attr_name).append(frag)

        return result

    def _load_axis_fragment(self, axis_name: str, value: str, rel_path: str) -> Fragment | None:
        frag_path = self._resolve_path(rel_path)
        if not frag_path:
            return None
        return Fragment(
            name=f"{axis_name}/{value}",
            path=str(frag_path),
            content=self._read_file(frag_path),
        )

    def available_values(self) -> dict:
        m = self.manifest()
        axes = m.get("axes", {})
        return {
            name: {
                "values": list(axis.get("values", {}).keys()),
                "default": axis.get("default", ""),
                "multi": axis.get("multi", False),
            }
            for name, axis in axes.items()
        }

    def list_references(self) -> list[dict]:
        m = self.manifest()
        refs = m.get("references", {}).get("on_demand", [])
        return [
            {"condition": r.get("condition", ""), "path": r.get("path", "")}
            for r in refs
        ]

    def get_reference(self, ref_path: str) -> str:
        frag_path = self._resolve_path(ref_path)
        if frag_path:
            return self._read_file(frag_path)
        return ""

    def _resolve_path(self, rel_path: str) -> Path | None:
        normalized = Path(rel_path.replace("\\", "/"))
        if normalized.is_absolute():
            return normalized if normalized.exists() else None
        full_path = self.skill_dir / normalized
        try:
            resolved = full_path.resolve()
            if resolved.exists():
                return resolved
        except Exception:
            pass
        return None

    def _read_file(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""


_DEFAULT_ROUTER: NatureWritingRouter | None = None


def get_router() -> NatureWritingRouter:
    global _DEFAULT_ROUTER
    if _DEFAULT_ROUTER is None:
        _DEFAULT_ROUTER = NatureWritingRouter()
    return _DEFAULT_ROUTER


def load_fragments(
    paper_type: str = "research",
    section: str = "",
    language: str = "zh-to-en",
    journal: str = "generic",
) -> LoadedFragments:
    return get_router().load_fragments(
        paper_type=paper_type,
        section=section,
        language=language,
        journal=journal,
    )


def available_values() -> dict:
    return get_router().available_values()


def list_references() -> list[dict]:
    return get_router().list_references()


def get_reference(path: str) -> str:
    return get_router().get_reference(path)