# EasyPaper Killer

## 项目目标

这个项目用于辅助生成偏文科、偏综述型的课程论文。系统的核心目标不是自由发挥式写作，而是基于用户提供的真实资料，完成选题细化、大纲规划、正文生成、引用绑定和 docx 导出。

## 使用原则

- 用户的主要体验应当是和 agent 对话。
- 用户尽量只做三类动作：描述需求、确认关键决策、把资料放进指定文件夹。
- agent 在每一步都要明确告知用户当前状态、下一步要做什么、资料应该放到哪里。
- 正式引用只能来自用户已提供并已入库的资料，不能凭空编造。

## 运行方式

本项目默认不是一个“内部封装好模型 API 的自动化程序”，而是一个给 Claude Code、Codex、OpenCode 这一类 agent 工具直接使用的工作环境。

默认用法是：

1. 用户在本目录中打开 agent 工具。
2. agent 读取 `docs/`、`input/`、`workspace/` 中的上下文文件。
3. agent 在对话中推进论文任务，并在需要时更新工作台文件。

`src/` 下的脚本主要用于辅助整理资料、生成工作台文件和做后处理，不应被理解为必须依赖外部 API 才能使用本项目。

## 开箱即用

这个项目现在默认按“无需额外安装依赖”来组织：

- Python 侧仅使用标准库。
- docx 导出不再依赖 `pandoc`、`npm install` 或额外 pip 包。
- agent 进入目录后，可以直接读文档和运行项目内现成脚本推进主流程；如果先快速理解项目结构，后续效果通常会更稳。

推荐统一入口：

```bash
.venv/bin/python -m src.app status --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
```

如果 agent 想直接知道当前该怎么和用户沟通，优先使用：

```bash
.venv/bin/python -m src.app guide --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
```

如果 agent 想把项目自动推进到下一个稳定阶段，优先使用：

```bash
.venv/bin/python -m src.app advance --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
```

常用命令：

```bash
.venv/bin/python -m src.app ingest --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
.venv/bin/python -m src.app plan --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
.venv/bin/python -m src.app write-prepare --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
.venv/bin/python -m src.app refresh --project-root "/Users/chenyule/WorkSpace/TempWork/论文写作"
```

## 适用范围

- 适合：课程论文、综述型论文、现状分析、对策建议类文章。
- 不适合：高公式推导、强实验设计、强数据建模、需要严密原创研究结论的论文。

## 标准工作流

1. 用户在对话中告诉 agent 论文方向和约束条件。
2. agent 帮用户收敛选题，并生成知网检索式。
3. agent 明确提示用户把查新引文、参考文献文本、PDF 放入指定目录。
4. 用户放入资料后，agent 解析资料并总结当前文献覆盖情况。
5. agent 生成论文大纲，与用户确认后分章写作。
6. agent 输出正文、摘要、参考文献和校验报告。
7. agent 按模板导出 docx。

## 目录说明

- `docs/`：项目规则、流程、数据结构、校验约束。
- `template/`：用户提供的论文模板。
- `input/`：用户原始输入资料和格式约束。
- `workspace/`：agent 生成的中间产物。
- `output/`：最终导出的论文文件。

## 当前版本边界

当前版本优先搭建文档骨架和流程规范，目标是让后续实现时有稳定的项目结构和交互约束。

## 关键提醒

- 如果 agent 判断资料不足，应先提示用户补充资料，而不是直接硬写。
- 如果 agent 发现需要补新文献，只能先给出候选建议，并提示用户补充对应资料后再纳入正式引用。
