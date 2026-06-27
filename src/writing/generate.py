from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from src.config.paths import ProjectPaths
from src.writing.provider import OpenAICompatibleProvider


@dataclass(slots=True)
class GenerationSummary:
    section_count: int
    generated_batch_count: int
    updated_files: list[str]


class BatchGenerationPipeline:
    """Optional helper that calls an external model and fills section drafts."""

    _PROMPT_BLOCK_PATTERN = re.compile(r"## 批次\s+(\d+).*?```text\n(.*?)```", re.DOTALL)
    _PLACEHOLDER_PATTERN = re.compile(r"(#### 批次\s+(\d+)\n\n)(.*?)(?=\n#### 批次\s+\d+\n\n|\Z)", re.DOTALL)

    def __init__(self) -> None:
        self.provider = OpenAICompatibleProvider.from_env()

    def run(self, project_root: Path, section_limit: int = 0) -> GenerationSummary:
        paths = ProjectPaths(project_root.resolve())
        prompt_files = sorted(paths.prompt_dir.glob("*.md"))
        if section_limit > 0:
            prompt_files = prompt_files[:section_limit]

        updated_files: list[str] = []
        generated_batch_count = 0

        for prompt_file in prompt_files:
            section_id = prompt_file.stem.split("_", 1)[0]
            draft_candidates = sorted(paths.section_draft_dir.glob(f"{section_id}_*.md"))
            if not draft_candidates:
                continue
            draft_file = draft_candidates[0]
            prompt_batches = self._load_prompt_batches(prompt_file)
            draft_text = draft_file.read_text(encoding="utf-8")
            new_text = draft_text

            for batch_number, prompt_text in prompt_batches:
                current_batch_text = self._extract_batch_text(new_text, batch_number)
                if current_batch_text and "待模型生成" not in current_batch_text:
                    continue

                continuity = self._collect_previous_text(new_text, batch_number)
                full_prompt = prompt_text
                if continuity:
                    full_prompt += (
                        "\n\n补充上下文：以下内容已经写好，请不要重复这些表述，而是在其基础上继续本章。\n"
                        + continuity
                    )
                generated = self.provider.generate(full_prompt)
                new_text = self._replace_batch_text(new_text, batch_number, generated)
                generated_batch_count += 1

            if new_text != draft_text:
                draft_file.write_text(new_text, encoding="utf-8")
                updated_files.append(str(draft_file))

        return GenerationSummary(
            section_count=len(prompt_files),
            generated_batch_count=generated_batch_count,
            updated_files=updated_files,
        )

    def _load_prompt_batches(self, file_path: Path) -> list[tuple[int, str]]:
        text = file_path.read_text(encoding="utf-8")
        return [(int(number), prompt.strip()) for number, prompt in self._PROMPT_BLOCK_PATTERN.findall(text)]

    def _extract_batch_text(self, draft_text: str, batch_number: int) -> str:
        for _, number, body in self._PLACEHOLDER_PATTERN.findall(draft_text):
            if int(number) == batch_number:
                return body.strip()
        return ""

    def _collect_previous_text(self, draft_text: str, batch_number: int) -> str:
        chunks = []
        for _, number, body in self._PLACEHOLDER_PATTERN.findall(draft_text):
            if int(number) >= batch_number:
                continue
            body = body.strip()
            if body and "待模型生成" not in body:
                chunks.append(body)
        return "\n\n".join(chunks)

    def _replace_batch_text(self, draft_text: str, batch_number: int, generated: str) -> str:
        def replace(match: re.Match[str]) -> str:
            prefix, number, body = match.groups()
            if int(number) != batch_number:
                return match.group(0)
            replacement = generated.strip() + "\n"
            return prefix + replacement

        return self._PLACEHOLDER_PATTERN.sub(replace, draft_text)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optional helper: generate section drafts from prompt batches using an external API model."
    )
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument("--section-limit", type=int, default=0, help="Optional number of sections to generate.")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    pipeline = BatchGenerationPipeline()
    summary = pipeline.run(Path(args.project_root), section_limit=args.section_limit)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
