# 工具、资源与提示词

MCP 定义了三个核心原语：tools（工具）、resources（资源）、prompts（提示词）。理解它们，你就知道一个 MCP Server 到底能向 AI 提供什么。

## 本文目标

掌握 MCP 的三个核心原语，并用 EBO 的实际能力举例。

## Tools：让模型调用外部能力

Tool 是"可执行的动作"——AI 决定调用它，产生副作用或返回结果。EBO 暴露的 15 个工具都是 tools：

| 类型 | 例子 | 特点 |
| --- | --- | --- |
| 查询类 | `robot_status`、`robot_list_locations` | 无副作用，读状态 |
| 动作类 | `robot_navigate`、`robot_speak`、`robot_take_photo` | 有副作用，改变机器人/现实世界 |
| 控制类 | `robot_stop_patrol`、`robot_move`、`robot_go_home` | 改变当前任务状态 |

每个 tool 有名字、描述和参数 schema（见[工具参考](ebo-mcp-tools-reference.md)）。AI 根据描述判断何时调用、填什么参数。

关键认知：tool 返回 "OK" 通常只代表"命令已下发"，不代表动作物理完成。EBO 的动作类工具尤其如此，要靠 `robot_status` 轮询复核——这是[排错文档](ebo-mcp-troubleshooting.md)的核心话题。

## Resources：暴露可读的上下文数据

Resource 是"可读的数据"，类似文件，由 AI 按需读取作为上下文。它通常是静态或半静态的信息，没有副作用。

EBO 目前的 MCP 接口主要以 tools 形式提供能力（状态查询也是一个 tool 而非 resource），所以本教程对 resources 着墨不多。但在很多 MCP Server 里，resources 用于暴露文档、配置、数据库内容等。例如一个日历 Server 可能把"今天的日程"作为 resource 暴露，让 AI 读取。

## Prompts：可复用的提示词模板

Prompt 是 Server 预先定义好的提示词模板，用户/Agent 可以按需取用。它把"怎么更好地使用这些工具"固化下来。

对这一场景，最实用的 prompt 是任务模板，例如"叫早并播报日程""开门迎宾"这类完整指令。本教程整理了一份[常用提示词模板集](ebo-mcp-prompts.md)，你可以直接复制使用，或作为参考改写成自己的。

## 三者如何组合

以[实战一](project-01-morning-briefing.md)的早间播报为例：

- Prompt：用户说"每天早上叫我起床并播报日程"（定义任务意图）
- Tool：AI 依次调用 `robot_navigate`、`robot_speak`、`robot_follow`、`robot_status`、`robot_go_home` 完成任务
- Resource：若有日历 resource，AI 可读取当天日程作为播报内容（本项目用另一个 MCP 读日程）

三者配合，AI 就能把一句自然语言变成一个跨系统的自动化流程。

## 设计建议与常见坑

1. 工具描述要写清楚：AI 全靠描述判断何时调用。EBO 工具里 `moveId=5`（完全停止）这种特殊值，写进描述能显著减少 AI 用错
2. 动作类工具要配状态查询：没有完成回报的硬件，务必提供查询工具，让 AI 能流程确认——这正是 EBO 的设计
3. 参数名保持一致：地点名这类参数必须和真实数据（地图命名）完全一致，最好提供 list 工具让 AI 先取准确值
4. 不要假设返回即成功：在 tool 描述或文档里明确"返回 OK 只代表下发"，避免 AI 误判

延伸阅读：[MCP 规范：tools / resources / prompts](https://modelcontextprotocol.io/docs/concepts/tools)。
