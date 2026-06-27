"""Advanced OOXML document editing tools.

Provides unpack/pack, validation, tracked-changes acceptance, and
comment management for .docx files. Zero-external-dependency for basic
operations; XSD schema validation optionally requires lxml.

Usage:
    python -m src.export.office.unpack  input.docx  unpacked/
    python -m src.export.office.pack    unpacked/   output.docx
    python -m src.export.office.validate output.docx
"""

from .unpack import unpack
from .pack import pack
from .comment import add_comment
from .accept_changes import accept_changes
from pathlib import Path

_HAS_LXML = False
try:
    import lxml.etree  # noqa: F401
    _HAS_LXML = True
except ImportError:
    pass

_HAS_LIBREOFFICE = False
try:
    from .soffice import get_soffice_env  # noqa: F401
    _HAS_LIBREOFFICE = True
except Exception:
    pass


def is_lxml_available() -> bool:
    return _HAS_LXML


def is_libreoffice_available() -> bool:
    return _HAS_LIBREOFFICE


def validate_docx(file_path: str) -> str:
    if not _HAS_LXML:
        return "XSD validation requires lxml (pip install lxml)."
    from .validate import DOCXSchemaValidator
    path = Path(file_path)
    if path.suffix.lower() != ".docx":
        return f"Validation not supported for {path.suffix}"
    return DOCXSchemaValidator().validate(str(path))