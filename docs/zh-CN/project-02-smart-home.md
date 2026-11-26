# 实战二：智能家居联动（开门迎宾）

> 这是另一个真实落地的项目：把 EBO 机器人和米家设备通过两个 MCP 通道连起来。它展示了 MCP 教程里两种典型用法——**HTTP 传输的机器人控制** 和 **stdio 传输的本地设备集成**——以及一个长期常驻程序如何处理状态残留、脏数据和硬件不完美。

## 最终效果

当小米门窗传感器检测到门由关→开时：

1. EBO 机器人自动导航到客厅
2. 视觉检测到人（识别到具体人名则带名字欢迎）
3. 播报欢迎语并打开米家灯泡
4. 启动人跟随
5. 播报并播放用户喜欢的音乐
6. 程序停止时自动清理现场（停音乐、停跟随、关灯）

## 设计原则

**纯 Python 独立程序 + 两个 MCP 通道，不依赖 AI 实时编排**，适合展会/演示场景长时间稳定运行。

这与实战一（定时自动化 + AI 编排）形成对比：
- 实战一适合「每天一次、逻辑复杂、需要大模型判断」的场景
- 实战二适合「事件触发、需要 7×24 稳定、逻辑固定」的场景

## 硬件清单

| 设备 | 说明 |
| --- | --- |
| EBO 机器人 | 需已建图并标注导航地点 |
| 小米门窗传感器 | Xiaomi Door and Window Sensor 3 |
| 米家智能灯泡 | BLE Mesh 设备 |
| 小米中枢网关 | BLE Mesh 子设备需要 |

网络：EBO 与运行脚本的电脑在同一局域网。米家中枢网关通过 BLE Mesh 与子设备通信，自身 WiFi 只用于上联互联网；中枢支持本地自动化，断网时仍可执行本地场景。

## 两个 MCP 服务器

### 1. EBO Robot MCP（HTTP / streamable HTTP）

```json
{
  "mcpServers": {
    "ebo-robot": {
      "type": "http",
      "url": "<EBO_MCP_ENDPOINT>",
      "headers": { "Authorization": "Bearer <YOUR_TOKEN>" }
    }
  }
}
```

> Token 从 APP 的「AI 联动编程」页获取，每个机器人绑定一个。地址同样在该页查看，本教程不公开。
> 环境区分：正式环境与测试环境地址不同，**不同环境的地图数据也不同**，导航地点名以实际环境 `robot_list_locations` 返回为准。

### 2. Mijia MCP（stdio 传输）

```json
{
  "mcpServers": {
    "mijia": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--python", "3.11", "mijia.py"],
      "cwd": "<米家 MCP 项目目录>"
    }
  }
}
```

底层用 `mijiaAPI` 库，首次启动需扫码登录，凭证保存在本地配置目录，后续自动刷新 Token。

## 系统架构

```
                    door_welcome.py  (独立 Python 常驻程序)
                          |          |
            mijiaAPI (stdio)              EBO Robot MCP (HTTP)
            米家账号 / 中枢 BLE Mesh        Bearer Token
                          |                     |
                    +-----+-----+               |
                    |           |               |
                门窗传感器    米家灯泡        EBO 机器人
                contact-state   on        导航/播报/识别/跟随/音乐
```

## 完整执行流程（8 步）

1. **门边沿检测**：主循环每 3 秒轮询；上一轮 `contact-state=True`（关门）且本轮 `False`（开门），且距上次触发 > 30 秒，才触发
2. **导航到客厅**：`robot_navigate(locationName='客厅')`，随后轮询 `robot_status` 等到达（5 秒一次，最长 120 秒）
3. **检测人**：三级探测——先查 `robot_status`；无人则等 10 秒再查；仍无人则调 `robot_search_360(objId='1')` 主动环顾；还无人则整段跳过
4. **播报欢迎语**：识别到人名 →「{名字}，欢迎回家，为您打开客厅的灯」；只识别到人未返回人名 →「欢迎回家，为您打开客厅的灯」。**必须等完整播完**再进入下一步
5. **开灯**：`light.set('on', True)`，最多 3 次重试（间隔 2 秒）
6. **启动人跟随**：`robot_follow(mode=0, trackTarget=4)`
7. **播报 + 播放音乐**：先播报「为您播放您最喜欢的音乐」，再 `robot_play_music(text='轻音乐')`；音乐与跟随并行持续
8. **停止时清理现场**：`robot_music_control(controlType=4)` 停音乐 + `robot_move(moveId=5)` 完全停止跟随 + 关灯。用 `try/finally` 覆盖所有退出路径

### 人名三态语义

| `detect_person` 返回值 | 含义 | 处理 |
| --- | --- | --- |
| `None` | 完全无人 | 跳过整个迎宾流程 |
| 人名字符串 | 识别到具体人名 | 播报带名字版本 |
| `''`（空串） | 检测到人但未返回人名 | 播报不带名字版本 |

> 注意：不要用「主人」之类的占位符。

## 核心实现要点

### EboClient：MCP HTTP 会话封装

用官方 SDK 的 streamable HTTP 客户端建立会话，`ClientSession` 必须 `async with` 进入以启动内部 dispatcher，然后 `initialize()`。

> **踩坑**：SDK v2.3 不能用 `StreamableHTTPTransport(url, http_client)`；`ClientSession` 不能直接构造后调用；工具 schema 属性是 `input_schema`（非 `inputSchema`）；SDK 内部用 httpx2，别传 `timeout`。

### TTS 等待（speak_and_wait）

实测 `robot_speak` 返回 `OK` 只代表"消息已发送"，`robot_status` 在播报期间**没有任何字段反映播放状态**（设备任务恒"空闲"、音乐"已停止"），且有约 20 秒缓存。所以只能按字数估算：

```python
wait = max(2.0, len(text) / 4.0) + 1.5   # 4字/秒 + 缓冲
await ebo.call('robot_speak', {'text': text, 'lang': 'zh-CN'})
await asyncio.sleep(wait)
```

`robot_search_360` 是阻塞调用。导航超时 120 秒兜底，超时也继续后续流程。

### 人名解析

设备真实返回格式：

```
Users currently detected in the camera view (...): DAVID {"leftTopX":0.382812, "leftTopY":0.1, ...}
当前检测到人数：1
```

也要兼容圆括号格式 `张三 (0.42, 0.31)` 和多人逗号分隔。**解析顺序关键：先去坐标，再去分隔符**——否则 JSON 坐标里的逗号会把名字切断。

```python
count = int(re.search(r'当前检测到人数[：:]\s*(\d+)', text).group(1))
m = re.search(r'Users currently detected[^\n]*?[：:]\s*(.+)', text)
val = m.group(1).strip()
name = re.sub(r'\s*\{.*?\}\s*', '', val)          # 去 JSON 坐标
name = re.sub(r'\s*\(.*?\)\s*', '', name)         # 去圆括号坐标
name = re.split(r'[,，;；]', name)[0].strip()       # 多人取第一个
```

### 英文人名 TTS 规范化

设备返回全大写 `DAVID`，中文 TTS 会当缩写逐字母念成 D-A-V-I-D。`robot_speak` 无发音控制参数，规避方法是转首字母大写：

```python
def normalize_name_for_tts(name):
    if name and re.fullmatch(r"[A-Za-z][A-Za-z\s.'-]*", name):
        return name.title()   # DAVID -> David
    return name               # 中文名保持原样
```

### 米家设备交互

```python
from mijiaAPI import mijiaAPI, mijiaDevice
api = mijiaAPI()
api.login()   # 自动刷新 Token 或扫码
door = mijiaDevice(api, dev_name='<门窗传感器名称>')
light = mijiaDevice(api, dev_name='<灯泡名称>')

state = door.get('contact-state')   # True=关门, False=开门
light.set('on', True)
```

### 停止与清理

用标志文件控制常驻进程：启动时创建 `door_welcome.run` 写入 `running`，删除后下个轮询周期退出；`__main__` 的 `finally` 兜底删除标志文件。清理函数覆盖所有退出路径。

## 踩坑汇总（复刻时务必避免）

### 环境与配置

- **Token 失效**：旧测试环境 Token 返回 `invalid or missing access key`（HTTP 401），改用正式环境的配置
- **环境地图差异**：测试环境有「门口」，正式环境最初没有。写死地点名会导航失败。换环境先 `robot_list_locations` 核对，地点名必须原样传，不能猜

### 时序与协议

- **SDK API 变更**：用 `streamable_http_client`；`ClientSession` 必须 `async with`；schema 属性是 `input_schema`；不传 `timeout`
- **TTS 返回 ≠ 播完**：接口无播放状态反馈，status 有 20s 缓存，靠状态轮询判断播完不可行，只能按字数估算等待
- **停止跟随的正确姿势**：`robot_stop_patrol` 停不掉 AI 跟随，必须用 `robot_move(moveId=5)` 完全停止；音乐用 `robot_music_control(controlType=4)`
- **连接关闭噪音**：短生命周期测试脚本退出时偶发 anyio `cancel scope in a different task`。判断为测试脚本生命周期问题，常驻主程序不受影响

### 设备与硬件

- **灯泡间歇性离线**：BLE Mesh 经中枢下发偶发错误码，实测重试第 3 次成功，故做 3 次重试。日志中「网关已接收指令，无法判断是否设置成功」是正常提示，不代表失败
- **传感器读取抖动**：偶发 base64 解密失败，主循环 try/except 跳过本轮即可，不是状态判断错误
- **现场遗留**：迎宾结束后跟随/音乐/灯会持续，退出必须统一清理，否则机器人一直处于跟随放音乐状态

### 数据与文本解析

- **坐标混进人名**：真实格式是 JSON 坐标而非圆括号；必须先去花括号再去逗号分割，顺序错了就会播报乱码
- **英文名字逐字母念**：全大写英文串被中文 TTS 当缩写，转首字母大写解决
- **无人名分支不能用占位**：用三态语义，没人名就播不带名字的版本

## 关键配置参数

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `EBO_URL` | `<EBO_MCP_ENDPOINT>` | 可用环境变量覆盖 |
| `EBO_TOKEN` | 运行时读取 | 不硬编码，可用环境变量覆盖 |
| `DOOR_SENSOR` | 传感器设备名 | 门窗传感器 |
| `LIGHT_NAME` | 灯泡 | 灯泡名称 |
| `DOOR_LOCATION` | 客厅 | 导航目标（必须匹配地图） |
| `GREETING_TPL` | `{name}，欢迎回家，为您打开客厅的灯` | 带名字欢迎语 |
| `GREETING_NO_NAME` | `欢迎回家，为您打开客厅的灯` | 不带名字欢迎语 |
| `POLL_INTERVAL` / `COOLDOWN` | 3 / 30 | 轮询间隔 / 触发冷却（秒） |
| `STATUS_POLL` / `NAV_TIMEOUT` | 5 / 120 | 导航状态轮询 / 超时（秒） |
| `LIGHT_RETRIES` / `LIGHT_RETRY_WAIT` | 3 / 2 | 开灯重试次数 / 间隔 |
| `TTS_CHARS_PER_SEC` / `TTS_MIN_WAIT` / `TTS_BUFFER` | 4.0 / 2.0 / 1.5 | TTS 时长估算 |

## 运行与运维

```bash
# 运行
cd <米家 MCP 项目目录>
uv run --python 3.11 door_welcome.py

# 停止：删除 door_welcome.run 标志文件（或 Ctrl+C）
```

> **触发注意**：程序启动时若门已是「开门」状态，需先关门再开门（产生 True→False 边沿）才触发。

**诊断脚本**：`verify_setup.py`（只读自检）、`smoke_test.py`（全链路冒烟，支持注入假名测试三态分支）、`cleanup_test.py`（清理现场）、`probe_ebo.py`（查状态）、`probe_tts.py`（探测 TTS 期间状态）、`list_tools.py`（列出全部工具与参数 schema）。

**依赖**：python-dotenv, websockets, mcp>=1.20.0, pydantic, mcp-proxy, fastmcp, mijiaAPI>=3.0.0（Python 3.11 + uv）。

## 遗留风险

- `robot_status` 约 20 秒服务端缓存，导航等待有延迟，但超时兜底可覆盖
- 短生命周期脚本退出期偶发 anyio cancel scope 警告，常驻主程序未复现
- 真人名字的真实返回格式已实测确认（JSON 坐标 + 全大写），解析与规范化逻辑已用真实文本样例验证

> **一句话总结**：难点不在流程编排本身，而在适配真实硬件/协议的不完美——环境差异、SDK 变更、TTS 时序、脏数据格式、间歇性离线、状态残留。每一处加固都是被真机实测"打"出来的。
