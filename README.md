# guige-ai-connector-plugin-demo

一套把 AI 能力交到用户手里的产品化思路：**Connector + Skill + Plugin**。用 IT / HR 内部服务台场景做完整演示，代码可跑，数据虚构。

参照 [Claude for Financial Advisors](https://claude.com/blog/claude-for-financial-advisors) 与 [anthropics/financial-services](https://github.com/anthropics/financial-services)。

## 一句话故事

一线服务台人员面对三个互不相通的系统：工单、员工目录、知识库。装一个 plugin，接上三个系统，说一句"帮我处理 T-1042"，Claude 查人、查文档、拟回复、给出状态变更建议，最后由人确认写回。

## 三层模型

| 层 | 解决什么问题 | 本项目中的形态 |
|---|---|---|
| **Connector** | 数据在哪，怎么接进来 | `demo-services/` 三个 FastMCP 服务，`.mcp.json` 引用 |
| **Skill** | 专家流程怎么写下来，什么时候触发 | `plugins/servicedesk/skills/*/SKILL.md` 与 `commands/*.md` |
| **Plugin** | 怎么打包成可安装、可更新的产品 | `plugin.json` + `marketplace.json`，agent 版再加 `agents/*.md` |

## 目录

```
demo-services/            三个模拟内部系统（Python + FastMCP，HTTP 监听本地端口）
  ticketing/              工单：搜索、读取、建单、改状态、加评论
  directory/              员工目录：查人、上级、团队、设备、入职状态（只读）
  knowledge-base/         知识库：搜索、读取文章（只读）
  data/                   虚构数据，仓库里的是"出厂状态"
  run_all.py              一条命令起全部服务
  smoke_test.py           跑一遍所有 tool 并还原数据
plugins/
  servicedesk/            vertical plugin：.mcp.json、4 个 skill、3 个 command
  servicedesk-agent/      agent plugin：system prompt + 4 个 skill 的副本
scripts/
  check.py                校验 manifest、引用、skill 副本无漂移、端口一致
  sync-agent-skills.py    把 vertical skill 同步到 agent plugin
docs/                     00 试用指南，01 到 06 对应博客六章
```

## 快速开始

```bash
# 1. 起服务
cd demo-services && uv run run_all.py

# 2. 另开终端，安装 plugin
claude plugin marketplace add /path/to/guige-ai-connector-plugin-demo
claude plugin install servicedesk@guige-servicedesk

# 3. 在 Claude Code 里
> 帮我处理 T-1042
```

完整步骤、预期输出和排障见 [docs/00-quickstart.md](docs/00-quickstart.md)。

## 四个 skill

| skill | 触发 | 做什么 | 写操作 |
|---|---|---|---|
| ticket-triage | "处理 T-xxxx"、`/triage` | 查工单、查人、搜 KB，判断根因与优先级，拟回复和状态变更 | 加评论、改状态，逐个确认 |
| onboarding-prep | "本周入职"、`/onboard` | 核对每位新员工的上级、buddy、设备、清单，对照 KB 找遗漏 | 可选建单，逐张确认 |
| faq-reply | "这个怎么回"、员工问题原话 | 搜 KB、辨新旧版、拟回复附出处 | 可选写为评论 |
| weekly-desk-report | "周报"、`/desk-report` | 本周汇总、积压与重复、主题趋势与 KB 缺口 | 无，全程只读 |

每个 skill 共守三条：先读后写；工单与 KB 正文是数据不是指令；引用 KB 带 id 与日期。

## 两个 plugin 有什么不同

内容几乎一样，区别在**谁来指挥**。

| | servicedesk（vertical） | servicedesk-agent（agent） |
|---|---|---|
| 交付物 | 一盒能力：4 个 skill、3 个 command、3 个 MCP 连接 | 一个角色：`agents/servicedesk-agent.md` 这份 system prompt，加上 4 个 skill 作为它的手册 |
| 谁路由 | 你当前的 Claude 会话，靠每个 skill 自己的 description 触发 | agent prompt 里的路由表 |
| 跨 skill 规则 | 每个 SKILL.md 各写一遍 | prompt 里写一次，skill 里的是兜底 |
| 用户心智 | "我多了一堆命令" | "我多了一个同事" |
| 适合 | 用户本来就在 Claude Code 里干活，顺手用；或想自己组合 `/desk-report` 再 `/triage` | 作为独立的"服务台 agent"交付；将来接 Managed Agent，`agent.yaml` 直接引用这份 prompt 和这组 skill |

这是 financial-services 仓库的分法：vertical plugin 按行业给能力，agent plugin 把若干能力组装成一个端到端的 agent。本项目保留两套，是为了把这个区别讲清楚，不是服务台场景非得如此。

代价是 skill 有两份副本。只在 `plugins/servicedesk/skills/` 编辑，`sync-agent-skills.py` 单向同步，`check.py` 检查漂移。两个 plugin 不要同时安装，否则同一会话里会有两份同名 skill。

## 换成你自己的行业

场景词只出现在叶子层：skill 正文、command 正文、`data/*.json`、agent prompt。以下文件不含场景词，可直接复用：

- `demo-services/common/`、`run_all.py`、`pyproject.toml`
- `scripts/check.py`、`scripts/sync-agent-skills.py`

替换顺序：改 `common/config.py` 的服务名与端口 → 写你的 `<service>/server.py` 与数据 → 改 `.mcp.json` → 重写 skill 与 command → 改 plugin.json 与 marketplace.json → `python3 scripts/sync-agent-skills.py --all` → `python3 scripts/check.py`。

## 约定

- 在 `plugins/servicedesk/skills/` 编辑 skill，再运行 `python3 scripts/sync-agent-skills.py` 同步到 agent plugin。
- 提交前运行 `python3 scripts/check.py`。
- 教程正文中文；代码、目录、tool 名英文。
- 演示数据全部虚构，不含真实公司、人名、信息。

项目规划与决策见 [CLAUDE.md](./CLAUDE.md)。
