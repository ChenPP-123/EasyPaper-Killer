# Changelog

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