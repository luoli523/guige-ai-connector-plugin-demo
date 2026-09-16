# guige-ai-connector-plugin-demo

教程项目：以 IT / HR 内部服务台为场景，演示 **connector + skill + plugin** 这套产品化思路如何把 AI 能力交到用户手里。
参照物：Claude for Financial Advisors（https://claude.com/blog/claude-for-financial-advisors）与 anthropics/financial-services 仓库（本机 `../financial-services`）。

## 三层模型

| 层 | 本项目中的形态 | 交付的价值 |
|---|---|---|
| Connector | `demo-services/` 下三个 FastMCP 服务，`plugins/servicedesk/.mcp.json` 引用 | 把内部系统的数据接进来 |
| Skill | `plugins/servicedesk/skills/*/SKILL.md` + `commands/*.md` | 把专家流程写下来，自动触发或 `/命令` 调用 |
| Plugin | `plugin.json` + `.claude-plugin/marketplace.json`，agent 版再加 `agents/*.md` | 打包成可安装、可版本更新的产品 |

## 场景与故事线

一线服务台支持人员面对三个互不相通的系统：工单、员工目录、知识库。
装一个 plugin，接上三个系统，说一句"帮我处理 T-1042"，Claude 查人、查文档、拟回复、更新工单状态，最后由人确认发送。

## 交付物

1. **demo-services/**：三个 Python + FastMCP 服务，HTTP 监听本地端口，一条命令全部启动，数据为 `data/*.json`。
   - `ticketing`（类 Jira Service Desk）：搜索、读取、建单、改状态、加评论
   - `directory`（类 Workday / AD）：查员工、上级、团队、设备分配、入职状态
   - `knowledge-base`（类 Confluence）：搜索文章、读取文章
2. **plugins/servicedesk/**（vertical plugin）：`.mcp.json`、三个 command（`/triage`、`/onboard`、`/desk-report`）、四个 skill（ticket-triage、onboarding-prep、faq-reply、weekly-desk-report）。
3. **plugins/servicedesk-agent/**（agent plugin）：`agents/servicedesk-agent.md` system prompt，捆绑上面四个 skill 的副本。
4. **scripts/**：从 financial-services 精简的 `check.py`（校验 manifest、引用、skill 副本无漂移）和 `sync-agent-skills.py`。
5. **docs/**：01 到 03 章，教程正文，GitHub 直接阅读。写法：先讲故事再讲技术，读者是有 AI 感和业务视角、非深度开发的人；每章动笔前写一行"读者是谁、带什么问题来、带走什么"，开头 300 字内不出现技术名词。
6. **博客**：一篇总结文（Hugo，发到 luoli523.github.io，走 guige-blog-post 流程），docs 三章写完后再整理，大纲写前确认。

## 已确定的决策

- Claude 与 OpenAI 使用独立 marketplace / manifest，共用现有 skills 和本地 `.mcp.json`。OpenAI 清单位于 `.agents/plugins/marketplace.json` 与各 plugin 的 `.codex-plugin/plugin.json`。两个平台的插件名称、版本保持一致。
- OpenAI 端推荐 `servicedesk`；`servicedesk-agent` 仅提供相同的四个 skill，不迁移 Claude 的 commands、agent 角色或子代理行为。不增加 `openai-skills/`，不做 ChatGPT 网页端或远程部署。
- 技术栈：Python + FastMCP。教程正文中文；代码、目录、tool 名英文。
- 本期 **不做** Managed Agent，但 agent prompt 保持可被 `agent.yaml` 引用的写法。
- 演示数据全部虚构，不含真实公司、人名、信息。
- 顺序：先 demo-services 与 plugin 跑通，再写 docs 三章（2026-09-16 由六章合为三章：01 为什么、02 演示、03 拆开看），最后把博客整理成一篇（2026-09-15 由六篇改为一篇）。
- Cowork 能否连本地 HTTP MCP 需实际验证；若不能，Cowork 部分改为讲解加截图占位，Claude Code 部分保证可跑。

## 实跑中发现的坑（写博客时要讲）

- **agent 的 tools 前缀**：plugin 安装后 MCP server 被登记为 `plugin_<plugin名>_<server名>`，工具名是 `mcp__plugin_servicedesk-agent_ticketing__get_ticket` 这种形式。agent frontmatter 里写 `mcp__ticketing__*` 一个都匹配不上，子代理以零工具拒绝启动。放第 03 章。`check.py` 第 8 项已校验。

## 约定

- 在 `plugins/servicedesk/skills/` 编辑 skill，再运行 `python3 scripts/sync-agent-skills.py` 同步到 agent plugin。
- 提交前运行 `python3 scripts/check.py`。
