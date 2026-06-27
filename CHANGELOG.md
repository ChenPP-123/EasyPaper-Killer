# Changelog

## [0.2.1] — 2026-06-27

### Added
- **归档自动清理**：`archive` / `reset` 自动调用 `_cleanup_session_data()`，清空 parsed JSON、重置约束/任务文件为模板、清理 raw 目录用户数据，杜绝任务间的数据残留
- `init` 阶段自动检测：模板 docx 存在但 `格式与写作要求.md` 为空时输出回填提示
- `init` 自动创建运行时目录和模板文件（`任务需求.md`、`格式与写作要求.md`）
- `TemplateSpec` 新增 `abstract_font_rule`、`keywords_font_rule`、`citation_superscript` 字段

### Changed
- `DocxExporter` 现在从 `TemplateSpec` 读取摘要/关键词字体规则（默认楷体），fontTable 已注册楷体
- `DocxExporter._build_runs()` 引用上标可通过 `apply_superscript` 参数控制
- `ExportPipeline` 移除硬编码关键词偏好列表
- `AGENTS.md` 新增「docx 导出规则」：严禁 agent 自行编写一次性脚本构建 docx
- `AGENTS.md` 新增「资料收集要求」：明确三个目录路径、两种格式、三种材料区别，含可直接使用的提示模板
- `AGENTS.md` 模版优先原则新增强制规则：拆包模板后必须将格式信息回填到 `input/constraints/格式与写作要求.md`

### Fixed
- **`.gitignore` bug**：`workspace/current/` → `workspace/当前项目/`，修复实际工作台目录名从未被忽略的问题
- 全面排除运行时数据目录（`input/`、`workspace/`、`output/`、`template/`），Git 仓库只追源码
- README 保持零命令用户体验，移除数据分离相关的命令行说明

### Removed
- 清理测试产生的 `scripts/` 自定义导出脚本（被管线禁止的旁路代码）
- 清除上一轮测试残留的 `evidence.json`、`references.json`、`sources.json` 数据
- 从 Git 追踪中移除所有 `input/` 下的用户数据文件，改为 `init` 按需创建

---

## [0.2.0] — 2026-06-27

### Added
- **docx 引用自动上标**：导出时 `[1]`、`[1,2]`、`[1-3]` 等引用格式自动渲染为上标，同时支持 OOXML（`docx.py`）和 JS（`render_docx.js`）双渲染器
- **docx 高级编辑工具** (`src/export/office/`)：拆包、打包、校验、批注、修订接受，全部基于 Python 标准库，零强制外部依赖
- **Nature 风格写作指引** (`src/writing/nature/`)：按 paper_type / section / language / journal 四轴加载写作规则碎片，内置 3 核心碎片 + 8 章节碎片 + 5 期刊碎片 + 12 按需参考文档
- 导出管线集成 post-export 结构校验

### Changed
- 重写 README：对话式叙事、完整目录结构、功能亮点
- `AGENTS.md` 新增「项目内集成技能」章节

### Removed
- 删除 `Skills/` 外部目录，全部技能内容融入 `src/` 实现项目自包含

---

## [0.1.0] — 2026-06-25

### Added
- 项目初始化：对话式论文写作工作台骨架
- 标准 7 阶段流程（选题收敛 → 检索准备 → 资料盘点 → 大纲生成 → 分批写作 → 整理校验 → 导出交付）
- 流程闸门机制：每阶段之间显式确认
- `src/app.py` 统一入口（init / guide / advance / refresh / export 等命令）
- 资料导入、解析、大纲规划、章节写作、引用管理、模板导出、质量校验全部管线
- 基础 docx 导出（零依赖 OOXML 生成）

### Fixed
- 移除硬编码路径，补全 `guide` 命令 `--project-root` 参数

### Removed
- 残留用户数据