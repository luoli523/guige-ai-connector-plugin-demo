# guige-ai-connector-plugin-demo

给 AI 编码助手（Claude Code、Codex 等）看的项目说明。人读的介绍在 [README](./README.md)，教程在 `docs/`。

教程项目：以 IT / HR 内部服务台为场景，演示 **connector + skill + plugin** 这套产品化思路如何把 AI 能力交到用户手里。
参照物：[Claude for Financial Advisors](https://claude.com/blog/claude-for-financial-advisors) 与 [anthropics/financial-services](https://github.com/anthropics/financial-services)，本项目照它精简。

## 三层模型

| 层 | 本项目中的形态 | 交付的价值 |
|---|---|---|
| Connector | `demo-services/` 下三个 FastMCP 服务，各 plugin 的 `.mcp.json` 引用 | 把内部系统的数据接进来 |
| Skill | `plugins/servicedesk/skills/*/SKILL.md` + `commands/*.md` | 把专家流程写下来，自动触发或 `/命令` 调用 |
| Plugin | Claude：`.claude-plugin/`；Codex：`.agents/plugins/` 与 `.codex-plugin/`；agent 版再加 `agents/*.md` | 打包成可安装、可版本更新的产品 |

## 场景与故事线

一线服务台支持人员面对三个互不相通的系统：工单、员工目录、知识库。
装一个 plugin，接上三个系统，说一句"帮我处理 T-1042"，AI 查人、查文档、拟回复、给出状态变更，最后由人确认写回。

## 组成

1. **demo-services/**：三个 Python + FastMCP 服务，HTTP 监听本地端口，`run_all.py` 一条命令全部启动，数据为 `data/*.json`，`smoke_test.py` 调一遍全部 tool 并还原数据。
   - `ticketing`（类 Jira Service Desk）：搜索、读取、建单、改状态、加评论
   - `directory`（类 Workday / AD）：查员工、上级、团队、设备分配、入职状态，只读
   - `knowledge-base`（类 Confluence）：搜索文章、读取文章，只读
2. **plugins/servicedesk/**（vertical plugin）：`.mcp.json`、三个 command（`/triage`、`/onboard`、`/desk-report`）、四个 skill（ticket-triage、onboarding-prep、faq-reply、weekly-desk-report）。
3. **plugins/servicedesk-agent/**（agent plugin）：`agents/servicedesk-agent.md` system prompt，捆绑上面四个 skill 的副本。
4. **scripts/**：`check.py`（校验两套 manifest、引用、skill 副本无漂移、端口一致、agent tools 前缀）、`sync-agent-skills.py`、`test_check.py`。
5. **docs/**：00 试用指南，01 到 03 教程正文。

## 已确定的决策

- 技术栈：Python 3.11+、FastMCP、uv。教程正文中文；代码、目录、tool 名英文。
- Claude 与 Codex 使用独立的 marketplace / plugin manifest，共用同一组 skill 和 `.mcp.json`。两个平台的 plugin 名称、版本保持一致，`check.py` 第 9 项校验。
- Codex 端推荐 `servicedesk`；`servicedesk-agent` 在 Codex 端只提供相同的四个 skill，不迁移 Claude 的 commands、agent 角色或子代理行为。不增加平台专用 skill，不做 ChatGPT 网页端或远程部署。
- 不做 Managed Agent，但 agent prompt 保持可被 `agent.yaml` 引用的写法。
- 演示数据全部虚构，不含真实公司、人名、信息。截图发布前遮掉真实域名、组织名。
- 只在 Claude Code 里实测过完整流程。Codex 端已做 manifest 校验，实跑待补；Cowork 能否连本地 HTTP MCP 未验证。

## 教程写法

读者是有 AI 感和业务视角、非深度开发的人。先讲故事再讲技术，用业务语言。每章动笔前写一行"读者是谁、带什么问题来、带走什么"，开头 300 字内不出现技术名词。演示章跟着业务场景走，不对截图逐段拆解。

## 实跑中发现的坑

- **agent 的 tools 前缀**：plugin 安装后 MCP server 被登记为 `plugin_<plugin名>_<server名>`，工具名是 `mcp__plugin_servicedesk-agent_ticketing__get_ticket` 这种形式。agent frontmatter 里写 `mcp__ticketing__*` 一个都匹配不上，子代理以零工具拒绝启动。`check.py` 第 8 项校验，第 03 章有讲。
- **装的是副本**：`claude plugin install` 复制目录到缓存，改仓库文件后会话里仍是旧的。开发期用 `claude --plugin-dir plugins/servicedesk`，或 `claude plugin update`。
- **有 shell 权限的模型会绕过 connector**：MCP 没连上时模型直接起 FastMCP client 连端口。给一线用户部署时要在客户端权限里限制 Bash 等工具。

## 约定

- 在 `plugins/servicedesk/skills/` 编辑 skill，再运行 `python3 scripts/sync-agent-skills.py` 同步到 agent plugin；不要直接改副本。
- 改端口只改 `demo-services/common/config.py`，`.mcp.json` 由 `check.py` 第 7 项核对。
- 发版同步更新每个 plugin 的 Claude / Codex 两份 manifest 的 version。
- 提交前运行 `python3 scripts/check.py`（需 pyyaml；已建演示环境时可用 `demo-services/.venv/bin/python`）。改了 check.py 再跑 `scripts/test_check.py`。
- 改了 tool 或数据先跑 `uv run smoke_test.py`，再进客户端实测。
