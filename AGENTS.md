# EasyPaper Killer Agent 约定

## 项目定位

这个目录不是一个“内部自带模型服务”的应用项目，而是一个供 Claude Code、Codex、OpenCode 等 agent 工具直接进入并工作的论文写作环境。

默认执行方式：

- agent 进入本目录
- 读取 `docs/`、`input/`、`workspace/` 下的文件
- 在对话中引导用户推进论文流程
- 必要时读写工作台文件

外部 API 直连不是默认路径，只是可选扩展。

## 开箱即用要求

- 项目默认应在不额外安装依赖的前提下可用。
- agent 不应要求用户再安装 `pandoc`、额外 pip 包或新的 npm 依赖才能推进主流程。
- 优先使用项目内已有脚本和标准库能力。
- 统一入口为 `python -m src.app`。
- 默认优先尝试 `python -m src.app guide` 和 `python -m src.app advance`。
- 运行 `src.app init` 后，工具会自动提示当前应使用的 Python 命令路径。不要盲目把 `.venv/bin/python` 当作唯一正确路径。如果找不到 Python 项目应先告诉用户，而不是自动尝试检查和安装虚拟环境。

## 核心工作方式

- 主要交互发生在 agent 和用户的对话中。
- 用户尽量只做三类动作：描述需求、确认决策、把资料放入指定目录。
- agent 负责告诉用户当前阶段、已完成事项、下一步该做什么。
- agent 不应默认假设项目内一定配置了外部模型 API。
- agent 可以直接开始工作，但先快速理解项目结构通常会得到更稳定的结果。

## 标准流程

1. 收集任务需求并收敛题目。
2. 生成检索式，提示用户准备资料。
3. 解析资料并输出资料盘点。
4. 生成并确认论文大纲。
5. 按章节、按批次推进正文写作。
6. 整理引用、参考文献和校验报告。
7. 最后再做摘要、关键词和 docx 导出。

## 流程闸门

每个阶段之间都有一道显式闸门，agent 不能跳跃推进。违反闸门规则的推进本身就是 bug。

| 阶段 | 可以做的事 | 禁止做的事 |
|------|-----------|-----------|
| 1. 题目未确认 | 讨论选题方向、给候选题目 | 给正式检索式、推进到资料收集 |
| 2. 题目已确认，资料未入库 | 给检索式、提示用户准备资料 | 生成正式大纲、进入正文写作 |
| 3. 资料已入库 | 盘点资料、判断资料是否足够 | 资料明显不足时仍然进入大纲 |
| 4. 大纲已生成 | 讨论大纲结构、调整章节 | 大纲未确认就进入正文写作 |
| 5. 大纲已确认 | 按章节逐批写作 | 一次性生成整篇、跨章同时展开 |
| 6. 正文写作完成 | 整理引用、校验、摘要、导出 | 正文未全部完成就进入导出 |

## 写作规则

- 不要一次性生成整篇论文。
- 必须按章节分批次完成，避免单次输出超出 token 限制。
- 每一批只使用当前批次允许的证据块。
- 没有证据支持的事实不要写入正文。
- 引用先使用 `[SRC-xxx]` 占位，后续再统一整理为编号引用。
- 引言可以较密集引用文献来交代背景和问题意识。
- 主体分析章节以整合分析为主，只在关键判断、数据和明确结论处插入引用。
- 结论以总结为主，不要句句挂引用，除非必须回扣某个事实。

## 优先读取的文件

- `README.md`
- `START.md`
- `docs/项目设计.md`
- `docs/使用流程.md`
- `docs/Prompt策略.md`
- `input/topic/任务需求.md`
- `workspace/当前项目/05_章节写作计划.md`
- `python -m src.app status` 的输出结果
- `python -m src.app guide` 的输出结果
- `src/writing/nature/`（写作阶段需要时加载写作指引片段）
- `src/export/office/__init__.py`（docx 高级编辑时参考）

## agent 回复要求

除纯讨论外，尽量明确说明：

- 当前阶段
- 已完成内容
- 发现的问题
- 用户下一步动作
- 相关文件路径

## 可选扩展

如果当前 agent 运行环境本身支持外部模型 API，可以使用 `src/writing/generate.py` 之类的辅助脚本；如果没有，也应优先通过当前 agent 会话本身完成逐批生成，而不是把“缺少 API”当作主流程阻塞点。

## 项目内集成技能

### 1. docx 高级编辑工具（`src/export/office/`）

零外部依赖的 OOXML 文档编辑工具集，用于高级 docx 操作。

| 工具 | 命令 | 用途 |
|------|------|------|
| 拆包 | `python -m src.export.office.unpack input.docx unpacked/` | 将 docx 解包为可编辑的 XML |
| 打包 | `python -m src.export.office.pack unpacked/ output.docx` | 将编辑后的 XML 重新打包为 docx |
| 校验 | `python -m src.export.office.validate output.docx` | 校验 docx 结构完整性（需 `lxml`，可选） |
| 接受修订 | `python -m src.export.office.accept_changes input.docx output.docx` | 接受全部修订标记（需 LibreOffice） |
| 批注 | `python -m src.export.office.comment unpacked/ 0 "内容"` | 向文档添加批注 |

使用时机：
- 需要调整已生成 docx 的结构（如修改章节标题、添加页眉页脚）
- 需要对文档应用修订跟踪或批注审阅
- 需要校验导出的 docx 是否符合 OOXML 标准
- 常规 docx 导出使用 `src/export/docx.py`（已在导出流程自动调用）

Python API：
```python
from src.export.office import unpack, pack, add_comment, accept_changes, validate_docx
```

### 2. Nature 风格学术写作指引（`src/writing/nature/`）

Nature 期刊风格的论文写作指引系统，为 agent 的正文写作提供分章节、分类型的高质量写作规则。

使用方式：
```python
from src.writing.nature import load_fragments, available_values, list_references

# 查看可用维度
print(available_values())  # paper_type, section, language, journal

# 加载当前章节的写作指引
fragments = load_fragments(
    paper_type='research',   # research/methods/hypothesis/algorithmic/review
    section='intro',          # abstract/intro/method/experiments/discussion/conclusion/title
    language='zh-to-en',      # en/zh-to-en
    journal='generic',        # nature/nat-comms/generic
)
for content in fragments.all_content():
    pass  # 将写作规则纳入写作 prompt 或直接应用
```

使用时机：
- 写作阶段（流程第 5 步）生成各章节时，读取对应章节的写作指引
- 撰写摘要、引言、方法、实验、讨论、结论时，按 section 取值加载
- 中文笔记转写英文时，使用 `language='zh-to-en'` 获取中译英规则
- 面向 Nature 子刊投稿时，使用 `journal='nature'` 获取期刊风格约束
- 每章写作前应先加载该章的写作指引，并将规则纳入 prompt 上下文

指引原则：
- 证据优先：不编造数据、机制、统计量或创新性
- 按章节类型控制引用密度和措辞强度
- 每段有清晰论点，段首句表达该段核心主张

## 推荐入口顺序

agent 进入目录后，建议默认顺序如下：

1. 运行 `python -m src.app init --project-root <项目目录>`，判断是新任务还是继续上次。
2. 如果是新任务但工作台有旧内容，先让用户确认：
   - 继续 -> 跳过归档
   - 新任务 -> 运行 `python -m src.app archive --project-root <项目目录>` 或 `python -m src.app reset --project-root <项目目录>`
3. 运行 `python -m src.app guide --project-root <项目目录>` 获取下一步指令。
4. 如可自动推进，再运行 `python -m src.app advance --project-root <项目目录>`。
5. 完成论文后，运行 `python -m src.app archive --project-root <项目目录>` 归档当前任务。
6. 只有在需要精细控制某个阶段时，再单独调用 `ingest`、`plan`、`write-prepare`、`refresh`、`export`。

## 任务归档目录

已归档的任务会保存到 `workspace/archive/<时间戳>_<题目>/`，方便回看记录。如果归档时未识别题目，会显示为 `未知任务`。
