from __future__ import annotations

from src.models import AgentInstruction, WorkflowContext, WorkflowStage


class WorkflowOrchestrator:
    """Coordinates the conversation-first writing workflow."""

    def next_instruction(self, context: WorkflowContext) -> AgentInstruction:
        if context.stage == WorkflowStage.TASK_INTAKE:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=[],
                current_issues=["Topic scope and constraints still need confirmation."],
                next_actions=[
                    "Confirm course name, topic direction, and word count.",
                    "Narrow the topic before generating a search query.",
                ],
                file_targets=[],
                completion_reply="题目已确认",
            )

        if context.stage == WorkflowStage.QUERY_PREPARATION:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=["Topic has been narrowed enough for literature search."],
                current_issues=[],
                next_actions=[
                    "Generate CNKI search terms.",
                    "Ask the user to download 5-10 relevant papers.",
                ],
                file_targets=[
                    "input/references/raw/pdf/",
                    "input/references/raw/",
                ],
                completion_reply="资料已放入",
            )

        if context.stage == WorkflowStage.WAITING_FOR_MATERIALS:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=["Search query and collection instructions have been prepared."],
                current_issues=["Formal sources are not in place yet."],
                next_actions=[
                    "Wait for the user to place PDFs and reference text in the input folder.",
                ],
                file_targets=[
                    "input/references/raw/pdf/",
                    "input/references/raw/",
                    "input/constraints/格式与写作要求.md",
                ],
                completion_reply="资料已放入",
            )

        if context.stage == WorkflowStage.MATERIAL_REVIEW:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=["Materials are ready for parsing and coverage review."],
                current_issues=[],
                next_actions=[
                    "Parse formal sources.",
                    "Check whether the current material set can support the topic.",
                ],
                file_targets=["input/references/parsed/"],
                completion_reply="继续生成大纲",
            )

        if context.stage == WorkflowStage.OUTLINE_CONFIRMATION:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=["A draft outline should now be available for review."],
                current_issues=[],
                next_actions=[
                    "Ask the user to confirm or revise the outline.",
                    "Mark sections that still need more evidence.",
                ],
                file_targets=["workspace/当前项目/04_论文大纲.md"],
                completion_reply="大纲已确认",
            )

        if context.stage == WorkflowStage.SECTION_WRITING:
            return AgentInstruction(
                current_stage=context.stage,
                completed_work=["Outline has been confirmed."],
                current_issues=[],
                next_actions=[
                    "Generate the next section in small batches using only approved sources.",
                    "Pause if evidence is missing.",
                    "Do not ask the model to generate the whole paper in one pass.",
                ],
                file_targets=[
                    "workspace/当前项目/05_章节写作计划.md",
                    "workspace/当前项目/prompts/",
                    "workspace/当前项目/06_正文草稿.md",
                ],
                completion_reply="继续下一章",
            )

        return AgentInstruction(
            current_stage=context.stage,
            completed_work=["Main writing is complete."],
            current_issues=[],
            next_actions=[
                "Generate abstract and references.",
                "Run citation and format checks.",
                "Export the final docx.",
            ],
            file_targets=[
                "workspace/当前项目/09_校验报告.md",
                "output/",
            ],
            completion_reply="导出完成",
        )
