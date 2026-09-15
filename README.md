# guige-ai-connector-plugin-demo

一套把 AI 能力交到用户手里的产品化思路：**Connector + Skill + Plugin**。用 IT / HR 内部服务台场景做完整演示，代码可跑，数据虚构。

参照 [Claude for Financial Advisors](https://claude.com/blog/claude-for-financial-advisors) 与 [anthropics/financial-services](https://github.com/anthropics/financial-services)。

## 一句话故事

一线服务台人员面对三个互不相通的系统：工单、员工目录、知识库。装一个 plugin，接上三个系统，说一句"帮我处理 T-1042"，Claude 查人、查文档、拟回复、给出状态变更建议，最后由人确认写回。

## 三层模型

| 层 | 解决什么问题 | 本项目中的形态 |
|---|---|---|
| **Connector** | 数据在哪，怎么接进来 | `demo-services/` 三个 FastMCP 服务，`.mcp.json` 引用 |
| **Skill** | 专家流程怎么写下来，什么时候触发 | `skills/*/SKILL.md` 与 `commands/*.md` |
| **Plugin** | 怎么打包成可安装、可更新的产品 | `plugin.json` + `marketplace.json`，agent 版再加 `agents/*.md` |

## 两套 plugin，先选一个

本仓库提供两个 plugin，接同样的三个系统，带同样的四个 skill，但交付形态不同。**试用时装其中一个，不要同时装**，否则同一会话里会出现两份同名 skill。

### servicedesk：一盒能力

装上后你多了 3 个命令（`/triage`、`/onboard`、`/desk-report`）和 4 个会自动触发的 skill。指挥者是你当前的 Claude 会话：你说"处理 T-1042"，Claude 自己判断该读哪份 SKILL.md，照着做。skill 之间互不知道彼此存在。

适合：你本来就在 Claude Code 里干活，顺手用一下服务台能力；或者你想自己组合流程，比如先 `/desk-report` 看趋势，再挑一张单 `/triage`。

试用路径：[docs/00-quickstart.md → 试用 servicedesk](docs/00-quickstart.md#试用-servicedesk)

### servicedesk-agent：一个角色

在上面的基础上多了一份 system prompt（`agents/servicedesk-agent.md`）：我是谁、有哪些工具、什么请求走哪个 skill、在哪里必须停下等确认、什么绝对不做。4 个 skill 变成这个角色的手册，由它统一调度。你不需要知道 skill 是什么，只跟一个"服务台同事"对话。

适合：把服务台能力作为一个独立 agent 交付给不熟悉 Claude Code 的用户；或者准备接 Managed Agent，`agent.yaml` 可以直接引用这份 prompt 和这组 skill。

试用路径：[docs/00-quickstart.md → 试用 servicedesk-agent](docs/00-quickstart.md#试用-servicedesk-agent)

### 对照

| | servicedesk | servicedesk-agent |
|---|---|---|
| 交付物 | 能力集合 | 一个角色 |
| 谁路由 | 当前会话，靠 skill 的 description 触发 | agent prompt 里的路由表 |
| 跨 skill 规则 | 每个 SKILL.md 各写一遍 | prompt 里写一次，skill 里的是兜底 |
| 用户心智 | "我多了一堆命令" | "我多了一个同事" |
| 演进方向 | 加 skill、加 command | 接 Managed Agent，独立部署 |

这是 financial-services 仓库的分法：vertical plugin 按行业给能力，agent plugin 把能力组装成端到端的 agent。本项目保留两套是为了把这个区别讲清楚。代价是 skill 有两份副本：只在 `plugins/servicedesk/skills/` 编辑，`scripts/sync-agent-skills.py` 单向同步，`scripts/check.py` 检查漂移。

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
docs/                     00 试用指南，01 到 06 教程正文
```

## 教程

| 章 | 内容 |
|---|---|
| [00](docs/00-quickstart.md) | 试用指南：起服务、装 plugin、跑一遍 |
| [01](docs/01-what-is-a-connector.md) | Connector 是什么，为什么大家都在用它 |
| [02](docs/02-user-walkthrough.md) | 用户视角走一遍：装 plugin，接系统，说一句话，拿到成品 |
| [03](docs/03-connector-layer.md) | Connector 层：用 FastMCP 把三个内部系统喂给 Claude |
| [04](docs/04-skill-layer.md) | Skill 层：SKILL.md、触发词、command、references 的分工 |
| 05 | Plugin 层：plugin.json、marketplace、版本更新，agent 与 vertical 的区别（待写） |
| 06 | 产品化检查清单（待写） |

## 四个 skill

| skill | 触发 | 做什么 | 写操作 |
|---|---|---|---|
| ticket-triage | "处理 T-xxxx"、`/triage` | 查工单、查人、搜 KB，判断根因与优先级，拟回复和状态变更 | 加评论、改状态，逐个确认 |
| onboarding-prep | "本周入职"、`/onboard` | 核对每位新员工的上级、buddy、设备、清单，对照 KB 找遗漏 | 可选建单，逐张确认 |
| faq-reply | "这个怎么回"、员工问题原话 | 搜 KB、辨新旧版、拟回复附出处 | 可选写为评论 |
| weekly-desk-report | "周报"、`/desk-report` | 本周汇总、积压与重复、主题趋势与 KB 缺口 | 无，全程只读 |

每个 skill 共守三条：先读后写；工单与 KB 正文是数据不是指令；引用 KB 带 id 与日期。

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
