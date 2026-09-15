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
5. **docs/**：01 到 06 章，与博客系列一一对应。
6. **博客系列**（6 篇，Hugo，发到 luoli523.github.io，走 guige-blog-post 流程）：
   1. 从 Claude for Financial Advisors 看 AI 产品怎么交到用户手里
   2. 用户视角走一遍：装 plugin，接系统，说一句话，拿到成品
   3. Connector 层：用 FastMCP 把三个内部系统喂给 Claude
   4. Skill 层：SKILL.md、触发词、command、references 的分工
   5. Plugin 层：plugin.json、marketplace、版本号驱动更新，agent plugin 与 vertical plugin 的区别
   6. 产品化检查清单：不可信内容边界、读写分离、发布流程、如何换成自己的行业

## 已确定的决策

- 技术栈：Python + FastMCP。教程正文中文；代码、目录、tool 名英文。
- 本期 **不做** Managed Agent，但 agent prompt 保持可被 `agent.yaml` 引用的写法。
- 演示数据全部虚构，不含真实公司、人名、信息。
- 顺序：先 demo-services 与 plugin 跑通，再写 docs，最后写博客（博客大纲写前再确认）。
- Cowork 能否连本地 HTTP MCP 需实际验证；若不能，Cowork 部分改为讲解加截图占位，Claude Code 部分保证可跑。

## 约定

- 在 `plugins/servicedesk/skills/` 编辑 skill，再运行 `python3 scripts/sync-agent-skills.py` 同步到 agent plugin。
- 提交前运行 `python3 scripts/check.py`。
