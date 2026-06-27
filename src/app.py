from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from src.citation.pipeline import CitationPipeline
from src.config.paths import ProjectPaths
from src.export.pipeline import ExportPipeline
from src.ingest.pipeline import MaterialIngestionPipeline
from src.planning.pipeline import PlanningPipeline
from src.qa.checks import QualityChecker
from src.qa.pipeline import QAPipeline
from src.writing.pipeline import WritingPipeline
from src.writing.render import DraftRenderer


@dataclass(slots=True)
class ProjectStatus:
    current_stage: str
    completed: list[str]
    next_actions: list[str]
    key_files: list[str]


@dataclass(slots=True)
class GuideMessage:
    current_stage: str
    completed: list[str]
    message: str
    next_reply: str
    key_files: list[str]


@dataclass(slots=True)
class AdvanceResult:
    initial_stage: str
    final_stage: str
    executed_steps: list[str]
    blocked_reason: str
    next_actions: list[str]
    key_files: list[str]


import sys


def detect_python() -> str:
    """Returns the recommended python command for documentation and agent use."""
    exe = sys.executable
    cwd = Path.cwd().resolve()
    try:
        relative = exe.removeprefix(str(cwd) + "/")
        if relative != exe:
            return relative
    except (ValueError, TypeError):
        pass
    return exe


@dataclass(slots=True)
class TaskInitResult:
    has_existing_task: bool
    detected_topic: str
    proposed_action: str
    message: str
    next_reply_options: list[str]


@dataclass(slots=True)
class ArchiveResult:
    archived_task: str
    archive_path: str
    action: str


_TASK_REQUIREMENTS_TEMPLATE = """\
# 任务需求

- 课程名称：
- 论文方向：
- 当前初始题目：
- 论文类型：
- 目标字数：
- 是否需要摘要：
- 是否需要关键词：
- 是否需要致谢：
"""

_FORMAT_CONSTRAINTS_TEMPLATE = """\
# 格式与写作要求

本文件用于汇总学校模板、老师要求和本次论文的额外限制。若用户没有手动填写，agent 应在对话中主动提取并补全关键信息。

## 模板信息

- 使用模板文件：
- 模板是否已核对：
- 是否已有明确封面要求：
- 是否需要目录：

## 标题与层级要求

- 论文题目格式：
- 一级标题格式：
- 二级标题格式：
- 三级标题格式：

## 正文格式要求

- 正文字体：
- 正文字号：
- 行距：
- 段前段后：
- 页边距：
- 页码要求：

## 摘要与关键词要求

- 中文摘要要求：
- 中文关键词数量：
- 英文摘要要求：

## 参考文献要求

- 参考文献格式标准：
- 是否要求知网格式优先：
- 是否要求文献数量下限：
- 是否要求近年文献比例：

## 内容写作要求

- 是否偏综述：
- 是否强调学术风：
- 是否允许明显口语化表达：
- 是否需要避免绝对化结论：

## agent 使用说明

如果本文件中有空缺，agent 应按以下顺序处理：

1. 先从模板中提取能确定的信息。
2. 再从用户对话中补充。
3. 仍无法确认时，在校验报告中标记为待确认项。

agent 不应在格式要求不明确时假装已经完全满足模板。
"""


class ProjectApp:
    def __init__(self) -> None:
        self.qa_checker = QualityChecker()

    def init_workspace(self, project_root: Path) -> TaskInitResult:
        paths = ProjectPaths(project_root.resolve())
        python_cmd = detect_python()
        has_task = paths.workspace_dir.exists() and any(paths.workspace_dir.iterdir())

        def _build_message(base_message: str) -> str:
            templates = sorted(paths.template_dir.glob("*.docx")) if paths.template_dir.exists() else []
            constraints_file = paths.input_dir / "constraints" / "格式与写作要求.md"
            constraints_is_empty = True
            if constraints_file.exists():
                content = constraints_file.read_text(encoding="utf-8")
                constraints_is_empty = not any(
                    line.startswith("- ") and line.split("：")[-1].strip()
                    for line in content.splitlines()
                    if line.startswith("- ")
                )
            if templates and constraints_is_empty:
                template_name = templates[0].name
                return (
                    f"{base_message}\n\n"
                    f"⚠️ 检测到模板文件 `template/{template_name}` 但 `input/constraints/格式与写作要求.md` 尚未填写格式规则。\n"
                    f"请先拆包模板 docx（`{python_cmd} -m src.export.office.unpack`），提取样式定义中的字体、字号、行距等信息，"
                    f"回填到 `input/constraints/格式与写作要求.md` 的对应字段。"
                )
            return base_message

        if not has_task:
            return TaskInitResult(
                has_existing_task=False,
                detected_topic="",
                proposed_action="start_new",
                message=_build_message(f"当前工作台为空，可以直接开始新任务。跟用户确认论文方向和基本要求即可进入题目收敛阶段。后续运行命令时请使用 `{python_cmd} -m src.app <命令>` 格式。"),
                next_reply_options=["开始新任务"],
            )

        detected_topic = self._detect_topic(paths)
        archive_cmd = f"`{python_cmd} -m src.app archive --project-root \"{project_root}\"`"
        if detected_topic:
            return TaskInitResult(
                has_existing_task=True,
                detected_topic=detected_topic,
                proposed_action="ask_user",
                message=f"检测到正在进行中的任务，题目为：{detected_topic}。请先向用户确认是想继续这个任务还是开始新任务。如果开始新任务，会先归档当前内容（命令：{archive_cmd}）。",
                next_reply_options=[
                    "继续上次任务",
                    "归档当前任务并开始新任务",
                    "先看看当前进度再决定",
                ],
            )
        return TaskInitResult(
            has_existing_task=True,
            detected_topic="",
            proposed_action="ask_user",
            message=f"检测到工作台有残留文件，但未识别出明确题目。建议先向用户确认是否开始新任务。如需归档：{archive_cmd}。",
            next_reply_options=[
                "继续查看当前状态",
                "归档当前任务并开始新任务",
            ],
        )

    def archive_task(self, project_root: Path) -> ArchiveResult:
        paths = ProjectPaths(project_root.resolve())
        if not paths.workspace_dir.exists() or not any(paths.workspace_dir.iterdir()):
            return ArchiveResult(
                archived_task="无",
                archive_path="",
                action="skipped",
            )

        detected_topic = self._detect_topic(paths)
        safe_name = self._safe_archive_name(detected_topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_subdir = paths.archive_dir / f"{timestamp}_{safe_name}"
        archive_subdir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(paths.workspace_dir), str(archive_subdir))

        self._cleanup_session_data(paths)

        return ArchiveResult(
            archived_task=detected_topic or "未识别题目",
            archive_path=str(archive_subdir),
            action="archived",
        )

    def reset_workspace(self, project_root: Path) -> ArchiveResult:
        archive_result = self.archive_task(project_root)
        paths = ProjectPaths(project_root.resolve())
        paths.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_session_data(paths)
        return archive_result

    def _cleanup_session_data(self, paths: ProjectPaths) -> None:
        """Reset session-scoped data files to clean template state after archive/reset."""
        for file_path in [paths.sources_file, paths.evidence_file, paths.references_file]:
            try:
                file_path.write_text("[]", encoding="utf-8")
            except OSError:
                pass

        try:
            paths.constraints_file.write_text(_FORMAT_CONSTRAINTS_TEMPLATE, encoding="utf-8")
        except OSError:
            pass

        try:
            paths.task_requirements_file.write_text(_TASK_REQUIREMENTS_TEMPLATE, encoding="utf-8")
        except OSError:
            pass

        for raw_dir in [paths.raw_references_dir, paths.raw_pdf_dir]:
            if not raw_dir.exists():
                continue
            for item in raw_dir.iterdir():
                if item.name == ".DS_Store" or item.name == ".gitkeep":
                    continue
                try:
                    if item.is_file() or item.is_symlink():
                        item.unlink()
                    else:
                        shutil.rmtree(str(item))
                except OSError:
                    pass

        try:
            paths.raw_pdf_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def _detect_topic(self, paths: ProjectPaths) -> str:
        if paths.outline_file.exists():
            topic = self._extract_topic_from_outline(paths.outline_file)
            if topic:
                return topic
        for candidate in [paths.topic_refinement_file, paths.material_review_file]:
            if candidate.exists():
                topic = self._extract_topic_from_doc(candidate)
                if topic:
                    return topic
        return ""

    def _extract_topic_from_outline(self, file_path: Path) -> str:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- 最终题目："):
                return line.split("：", 1)[1].strip()
        return ""

    def _extract_topic_from_doc(self, file_path: Path) -> str:
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("- 当前基础方向：") or line.startswith("- 当前题目方向："):
                return line.split("：", 1)[1].strip()
        return ""

    def _safe_archive_name(self, topic: str) -> str:
        if not topic:
            return "未知任务"
        for char in r'\/:*?"<>|':
            topic = topic.replace(char, "_")
        return topic[:40] if len(topic) > 40 else topic

    def status(self, project_root: Path) -> ProjectStatus:
        paths = ProjectPaths(project_root.resolve())
        completed: list[str] = []
        next_actions: list[str] = []
        key_files: list[str] = []

        has_existing = paths.workspace_dir.exists() and any(paths.workspace_dir.iterdir())
        detected_topic = self._detect_topic(paths) if has_existing else ""

        if paths.sources_file.exists():
            completed.append("已完成资料入库")
            key_files.append(str(paths.sources_file))
        else:
            result = ProjectStatus(
                current_stage="等待资料入库",
                completed=completed,
                next_actions=[
                    "让用户把 PDF 放到 input/references/raw/pdf/。",
                    "让用户把查新引文和参考文献文本放到 input/references/raw/。",
                    "然后运行或调用 ingest 阶段。",
                ],
                key_files=[str(paths.raw_references_dir)],
            )
            if has_existing:
                result.next_actions.insert(0, "当前工作台存在旧任务文件，建议先运行 `src.app init` 确认是继续还是开始新任务。")
            return result

        if paths.outline_file.exists():
            completed.append("已生成论文大纲")
            key_files.append(str(paths.outline_file))
        else:
            return ProjectStatus(
                current_stage="等待大纲生成",
                completed=completed,
                next_actions=["运行或调用 planning 阶段，生成选题、大纲和资料盘点。"],
                key_files=key_files,
            )

        if paths.section_plan_file.exists() and paths.section_draft_dir.exists():
            completed.append("已生成分章节写作计划")
            key_files.append(str(paths.section_plan_file))
        else:
            return ProjectStatus(
                current_stage="等待写作拆分",
                completed=completed,
                next_actions=["运行或调用 writing 阶段，生成章节计划、prompt 包和草稿槽位。"],
                key_files=key_files,
            )

        draft_text = paths.draft_file.read_text(encoding="utf-8") if paths.draft_file.exists() else ""
        pending_batches = self.qa_checker.find_pending_generation_batches(draft_text)
        if pending_batches:
            return ProjectStatus(
                current_stage="正文分批写作中",
                completed=completed,
                next_actions=[
                    "让 agent 按 05_章节写作计划.md 顺序逐批完成正文。",
                    "每完成一章后重建总草稿并运行引用整理、校验。",
                ],
                key_files=key_files + [str(paths.section_plan_file), str(paths.section_draft_dir)],
            )

        completed.append("已形成正文草稿")
        key_files.append(str(paths.draft_file))

        if paths.qa_report_file.exists() and paths.output_dir.joinpath("论文初稿.docx").exists():
            completed.append("已生成校验报告与 docx 初稿")
            key_files.extend([str(paths.qa_report_file), str(paths.output_dir / "论文初稿.docx")])
            return ProjectStatus(
                current_stage="可进入精修或终稿阶段",
                completed=completed,
                next_actions=[
                    "检查校验报告中的风险项。",
                    "如需要，继续补资料或微调正文、摘要和参考文献。",
                ],
                key_files=key_files,
            )

        return ProjectStatus(
            current_stage="等待后处理与导出",
            completed=completed,
            next_actions=["运行 render、citation、qa、export 阶段，生成完整初稿交付物。"],
            key_files=key_files,
        )

    def refresh(self, project_root: Path) -> dict[str, object]:
        renderer = DraftRenderer().run(project_root)
        citation = CitationPipeline().run(project_root)
        qa = QAPipeline().run(project_root)
        export = ExportPipeline().run(project_root)
        return {
            "render": asdict(renderer),
            "citation": asdict(citation),
            "qa": asdict(qa),
            "export": asdict(export),
        }

    def guide(self, project_root: Path) -> GuideMessage:
        status = self.status(project_root)
        message, next_reply = self._build_guide_text(status, project_root)
        return GuideMessage(
            current_stage=status.current_stage,
            completed=status.completed,
            message=message,
            next_reply=next_reply,
            key_files=status.key_files,
        )

    def advance(self, project_root: Path) -> AdvanceResult:
        initial = self.status(project_root)
        executed_steps: list[str] = []
        blocked_reason = ""

        while True:
            current = self.status(project_root)

            if current.current_stage == "等待资料入库":
                raw_dir = ProjectPaths(project_root.resolve()).raw_references_dir
                has_raw_files = raw_dir.exists() and any(raw_dir.iterdir())
                has_pdf_dir_files = ProjectPaths(project_root.resolve()).raw_pdf_dir.exists() and any(
                    ProjectPaths(project_root.resolve()).raw_pdf_dir.iterdir()
                )
                if not (has_raw_files or has_pdf_dir_files):
                    blocked_reason = "当前还没有原始资料，无法自动推进资料入库。"
                    break
                MaterialIngestionPipeline().run(project_root)
                executed_steps.append("ingest")
                continue

            if current.current_stage == "等待大纲生成":
                PlanningPipeline().run(project_root)
                executed_steps.append("plan")
                continue

            if current.current_stage == "等待写作拆分":
                WritingPipeline().run(project_root)
                executed_steps.append("write-prepare")
                continue

            if current.current_stage == "等待后处理与导出":
                self.refresh(project_root)
                executed_steps.append("refresh")
                continue

            if current.current_stage == "正文分批写作中":
                blocked_reason = "正文已经进入必须由 agent 逐批生成的阶段，自动推进会在这里停止。"
                break

            blocked_reason = "当前已经处于稳定阶段，无需继续自动推进。"
            break

        final = self.status(project_root)
        return AdvanceResult(
            initial_stage=initial.current_stage,
            final_stage=final.current_stage,
            executed_steps=executed_steps,
            blocked_reason=blocked_reason,
            next_actions=final.next_actions,
            key_files=final.key_files,
        )

    def _build_guide_text(self, status: ProjectStatus, project_root: Path) -> tuple[str, str]:
        pr = str(project_root)
        if status.current_stage == "等待资料入库":
            return (
                f"当前还没有完成资料入库。请先提醒用户把论文 PDF 放到 `input/references/raw/pdf/`，把查新引文和参考文献文本放到 `input/references/raw/`。资料放好后，你可以直接运行 `python -m src.app ingest --project-root \"{pr}\"` 进入下一阶段。",
                "资料已放入",
            )
        if status.current_stage == "等待大纲生成":
            return (
                f"资料已经入库，但还没有生成大纲。你现在可以直接运行 `python -m src.app plan --project-root \"{pr}\"`，然后把 `workspace/当前项目/01_选题收敛.md`、`03_资料盘点.md` 和 `04_论文大纲.md` 作为当前讨论基础。",
                "继续生成大纲",
            )
        if status.current_stage == "等待写作拆分":
            return (
                f"大纲已经有了，但还没有拆成分章节写作任务。你现在可以运行 `python -m src.app write-prepare --project-root \"{pr}\"`，随后按 `workspace/当前项目/05_章节写作计划.md` 和 `workspace/当前项目/prompts/` 开始逐章逐批写作。",
                "开始分章写作",
            )
        if status.current_stage == "正文分批写作中":
            return (
                f"正文已经进入逐批写作阶段。注意流程闸门：只能按章节逐批推进，不能一次性生成整篇。优先读取 `workspace/当前项目/05_章节写作计划.md` 和 `workspace/当前项目/prompts/`，把本批结果回填到 `workspace/当前项目/section_drafts/`。每章的 prompt 已按章节定位（引言/主体/结论）配置了不同的引用密度规则：引言可以较密集引文，主体以分析为主，结论避免句句挂引用。完成当前章节后，再运行 `python -m src.app refresh --project-root \"{pr}\"`。",
                "继续下一批",
            )
        if status.current_stage == "等待后处理与导出":
            return (
                f"正文草稿已经成形，但还没有完成引用整理、校验和导出。注意流程闸门：正文未全部完成时不能提前做摘要和导出。你现在可以直接运行 `python -m src.app refresh --project-root \"{pr}\"`，它会重建总草稿、整理引用、生成校验报告并导出 docx。",
                "开始整理导出",
            )
        return (
            f"当前项目已经处于可精修或终稿阶段。优先查看 `workspace/当前项目/09_校验报告.md` 和 `output/论文初稿.docx`，根据风险项决定是补资料、微调正文，还是直接进入终稿完善。完成这篇后，可以运行 `python -m src.app archive --project-root \"{pr}\"` 归档，再开始新任务。",
            "继续精修",
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified entrypoint for the paper-writing agent workspace.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_project_root_arg(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--project-root", default=".", help="Project root directory.")

    add_project_root_arg(subparsers.add_parser("init", help="Check workspace and guide first-time task setup."))
    add_project_root_arg(subparsers.add_parser("status", help="Show current workflow stage and next actions."))
    add_project_root_arg(subparsers.add_parser("guide", help="Show agent-facing next-step guidance."))
    add_project_root_arg(subparsers.add_parser("advance", help="Advance automatically to the next stable stage when possible."))
    add_project_root_arg(subparsers.add_parser("archive", help="Archive current workspace and recreate a clean one."))
    add_project_root_arg(subparsers.add_parser("reset", help="Archive + recreate a clean workspace (non-interactive)."))
    add_project_root_arg(subparsers.add_parser("ingest", help="Run material ingestion."))
    add_project_root_arg(subparsers.add_parser("plan", help="Run planning stage."))
    add_project_root_arg(subparsers.add_parser("write-prepare", help="Prepare section writing packets."))
    add_project_root_arg(subparsers.add_parser("refresh", help="Rebuild draft, citations, QA, and export outputs."))
    add_project_root_arg(subparsers.add_parser("export", help="Generate abstract/keywords and export docx."))
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    project_root = Path(args.project_root)
    app = ProjectApp()

    if args.command == "init":
        print(json.dumps(asdict(app.init_workspace(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "archive":
        print(json.dumps(asdict(app.archive_task(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "reset":
        print(json.dumps(asdict(app.reset_workspace(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(asdict(app.status(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "guide":
        print(json.dumps(asdict(app.guide(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "advance":
        print(json.dumps(asdict(app.advance(project_root)), ensure_ascii=False, indent=2))
        return 0
    if args.command == "ingest":
        result = MaterialIngestionPipeline().run(project_root)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    if args.command == "plan":
        result = PlanningPipeline().run(project_root)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    if args.command == "write-prepare":
        result = WritingPipeline().run(project_root)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0
    if args.command == "refresh":
        print(json.dumps(app.refresh(project_root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "export":
        result = ExportPipeline().run(project_root)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
