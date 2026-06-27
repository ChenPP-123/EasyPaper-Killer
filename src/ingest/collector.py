from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CollectedMaterials:
    pdf_files: list[Path]
    text_files: list[Path]
    template_files: list[Path]

    @property
    def has_formal_materials(self) -> bool:
        return bool(self.text_files or self.pdf_files)


class MaterialCollector:
    """Collects user-provided files from the agreed folders."""

    def collect(self, raw_dir: Path, template_dir: Path) -> CollectedMaterials:
        pdf_dir = raw_dir / "pdf"
        pdf_files = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
        if not pdf_files:
            # Support ad hoc sample folders where PDFs are placed directly under raw_dir.
            pdf_files = sorted(path for path in raw_dir.glob("*.pdf") if path.is_file())

        text_files = sorted(path for path in raw_dir.glob("*.txt") if path.is_file())
        template_files = sorted(template_dir.glob("*.docx"))
        return CollectedMaterials(
            pdf_files=pdf_files,
            text_files=text_files,
            template_files=template_files,
        )
