# START

这个目录是 EasyPaper Killer，给 Claude Code、Codex、OpenCode 这类 agent 直接进入并工作的论文写作环境。

## 前置

Python 命令路径可能因环境而异，运行 `python -m src.app init --project-root <项目目录>` 后会自动提示当前应使用的正确路径。不要盲目把 `.venv/bin/python` 当作唯一正确路径。

## 第一步

先判断当前有没有正在进行的任务：

```bash
python -m src.app init --project-root <项目目录>
```

它会告诉你：

- 工作台是否已有任务
- 是什么题目
- agent 下一步应该先确认用户意图还是可以直接开工

## 第二步

如果用户确认开始新任务，先归档旧任务再开始工作。如果需要自动归档：

```bash
python -m src.app archive --project-root <项目目录>
```

如果要一键归档并重置为空白状态：

```bash
python -m src.app reset --project-root <项目目录>
```

## 第三步

确认当前状态和下一步动作：

```bash
python -m src.app guide --project-root <项目目录>
```

## 建议的工作方式

- 可以先快速浏览 `README.md`、`AGENTS.md`、`docs/项目设计.md`，这样后续判断会更稳。
- 也可以直接开工。
- 正文必须按章节、按批次推进，不要一次性生成整篇论文。
- 完成一篇论文后，使用 `archive` 归档任务，避免串题。

## 常用命令

```bash
python -m src.app init --project-root <项目目录>          # 初始化/恢复任务
python -m src.app status --project-root <项目目录>        # 查看状态
python -m src.app archive --project-root <项目目录>       # 归档任务
python -m src.app reset --project-root <项目目录>         # 归档并重置
python -m src.app ingest --project-root <项目目录>        # 资料入库
python -m src.app plan --project-root <项目目录>           # 生成大纲
python -m src.app write-prepare --project-root <项目目录>   # 准备写作计划
python -m src.app refresh --project-root <项目目录>        # 刷新工作台
```
