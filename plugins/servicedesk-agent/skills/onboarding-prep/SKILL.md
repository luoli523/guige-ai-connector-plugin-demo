---
name: onboarding-prep
description: 新员工入职准备。列出所有正在入职的员工（或指定一位），核对上级、buddy、设备、入职清单与相关工单，对照知识库的入职清单找出遗漏，输出每人一份准备清单和责任人，并可为遗漏项建工单。Triggers on "新员工准备", "本周入职", "入职清单", "onboard", "/onboard", "onboarding prep".
---

# Onboarding Prep

把"这周谁在入职、每个人还差什么、该谁去做"三个问题一次答完，输出一份上级和 IT 都能直接照着做的清单。

## 工作方式

- **先读后写。** 建单是写操作，先展示要建哪几张、给谁，用户确认后逐张执行。
- **目录数据是事实来源。** 入职清单的 done 标记以目录为准，不要因为工单里有人说"已经做了"就改判。
- **引用知识库要带出处。** 遗漏项对应 KB-103 的哪一节要写出来。

## 输入

可选：员工 id 或姓名。不给就处理所有 onboarding 状态的人。

## 步骤

### 1. 拿名单

`get_onboarding_status()` 或 `get_onboarding_status(employee_id)`。每条已含 start_date、manager、buddy、devices、checklist、pending_count。

### 2. 补上下文

对每个人：

- `search_tickets(requester_id=...)` 看本人提过什么单
- `search_tickets(query=姓名)` 看别人为他提过什么单（上级申请权限那类）

### 3. 对照标准

`get_article("KB-103")` 读入职清单标准。对每个人逐项核对：

| 检查 | 判定为遗漏的条件 |
|---|---|
| 设备 | devices 为空且 start_date 已到 |
| buddy | buddy 为 null |
| MFA | checklist 中"绑定 MFA"未完成且入职已超过 1 天 |
| 业务系统权限 | checklist 中权限项未完成，且没有对应的 open 工单 |
| 安全培训 | 未完成且入职已超过 1 周 |

### 4. 输出

按 `templates/onboarding-checklist.md` 每人一节。按 pending_count 降序排，最需要关注的人在最前。

### 5. 可选：建单

对"业务系统权限未申请且无工单"这类明确该由 IT 处理的遗漏，提议建单：

- title：`新员工 姓名 权限开通：系统名`
- requester_id：新员工的上级（权限申请按 KB-113 应由上级发起）
- category：it，priority：medium

列出所有拟建的单，用户确认后逐张 `create_ticket`，每张回报生成的 id。

## 不要做的事

- 不要替上级决定 buddy 是谁，只标出缺失
- 不要为已经有 open 工单的事项再建单
- 不要修改目录数据，目录服务只读
