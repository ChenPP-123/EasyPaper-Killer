from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from pathlib import Path

from src.models import TemplateSpec


@dataclass(slots=True)
class ExportPayload:
    title: str
    abstract: str
    keywords: list[str]
    sections: list[tuple[str, str]]
    references: list[str]


class DocxExporter:
    """Renders a final paper draft into a template-based docx file."""

    def export(self, payload: ExportPayload, template: TemplateSpec, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as docx:
            docx.writestr("[Content_Types].xml", self._content_types_xml())
            docx.writestr("_rels/.rels", self._root_rels_xml())
            docx.writestr("docProps/core.xml", self._core_props_xml(payload.title))
            docx.writestr("docProps/app.xml", self._app_props_xml())
            docx.writestr("word/document.xml", self._document_xml(payload))
            docx.writestr("word/styles.xml", self._styles_xml())
            docx.writestr("word/settings.xml", self._settings_xml())
            docx.writestr("word/fontTable.xml", self._font_table_xml())
            docx.writestr("word/_rels/document.xml.rels", self._document_rels_xml())
        return output_path

    def _content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/settings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
            '<Override PartName="/word/fontTable.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    def _root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    def _core_props_xml(self, title: str) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        safe_title = escape(title)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{safe_title}</dc:title>'
            '<dc:creator>OpenCode</dc:creator>'
            '<cp:lastModifiedBy>OpenCode</cp:lastModifiedBy>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>'
        )

    def _app_props_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>OpenCode</Application>'
            '</Properties>'
        )

    def _document_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" '
            'Target="settings.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" '
            'Target="fontTable.xml"/>'
            '</Relationships>'
        )

    def _settings_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:zoom w:percent="100"/>'
            '<w:defaultTabStop w:val="420"/>'
            '<w:characterSpacingControl w:val="doNotCompress"/>'
            '</w:settings>'
        )

    def _font_table_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:font w:name="宋体"/><w:font w:name="黑体"/>'
            '</w:fonts>'
        )

    def _styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/>'
            '<w:qFormat/>'
            '<w:rPr><w:rFonts w:ascii="宋体" w:eastAsia="宋体" w:hAnsi="宋体"/>'
            '<w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
            '</w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1">'
            '<w:name w:val="heading 1"/>'
            '<w:basedOn w:val="Normal"/><w:qFormat/>'
            '<w:pPr><w:spacing w:before="240" w:after="160"/><w:outlineLvl w:val="0"/></w:pPr>'
            '<w:rPr><w:rFonts w:ascii="黑体" w:eastAsia="黑体" w:hAnsi="黑体"/>'
            '<w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>'
            '</w:style>'
            '</w:styles>'
        )

    def _document_xml(self, payload: ExportPayload) -> str:
        body_parts: list[str] = []
        body_parts.append(self._paragraph_xml(payload.title, style="title", align="center", bold=True, font="黑体", size=32))
        body_parts.append(self._heading_xml("摘要"))
        for paragraph in self._split_paragraphs(payload.abstract):
            body_parts.append(self._paragraph_xml(paragraph))
        body_parts.append(self._paragraph_xml("关键词：" + "；".join(payload.keywords), first_line=False))

        for title, body in payload.sections:
            body_parts.append(self._heading_xml(title))
            for paragraph in self._split_paragraphs(body):
                body_parts.append(self._paragraph_xml(paragraph))

        body_parts.append(self._heading_xml("参考文献"))
        for reference in payload.references:
            body_parts.append(self._paragraph_xml(reference, first_line=False, hanging=True))

        section_props = (
            '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
            'w:header="720" w:footer="720" w:gutter="0"/>'
            '</w:sectPr>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>' + "".join(body_parts) + section_props + '</w:body></w:document>'
        )

    def _heading_xml(self, text: str) -> str:
        safe = escape(text)
        return (
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="黑体" w:eastAsia="黑体" w:hAnsi="黑体"/>'
            '<w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>'
            f'<w:t>{safe}</w:t></w:r></w:p>'
        )

    def _paragraph_xml(
        self,
        text: str,
        *,
        style: str = "Normal",
        align: str = "left",
        bold: bool = False,
        font: str = "宋体",
        size: int = 24,
        first_line: bool = True,
        hanging: bool = False,
    ) -> str:
        safe = escape(text)
        indent_xml = ''
        if hanging:
            indent_xml = '<w:ind w:left="420" w:hanging="420"/>'
        elif first_line:
            indent_xml = '<w:ind w:firstLine="420"/>'
        jc_xml = '' if align == "left" else f'<w:jc w:val="{align}"/>'
        bold_xml = '<w:b/>' if bold else ''
        return (
            '<w:p><w:pPr>'
            f'<w:pStyle w:val="{style}"/>'
            '<w:spacing w:line="420" w:lineRule="auto" w:after="120"/>'
            f'{indent_xml}{jc_xml}'
            '</w:pPr><w:r><w:rPr>'
            f'<w:rFonts w:ascii="{font}" w:eastAsia="{font}" w:hAnsi="{font}"/>'
            f'{bold_xml}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
            '</w:rPr>'
            f'<w:t xml:space="preserve">{safe}</w:t>'
            '</w:r></w:p>'
        )

    def _split_paragraphs(self, text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]
