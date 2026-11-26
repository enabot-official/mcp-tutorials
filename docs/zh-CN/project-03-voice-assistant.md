# 实战三：把 EBO 改造成语音助手

> 第三个项目把 EBO 接成一条语音流程：唤醒 → TTS 回应 → 听指令 → ASR 转文字 → 交给 WorkBuddy Agent 理解 → TTS 播报回复。
>
> 内容来自 2026-11-24 到 11-26 的实际操作和实测。重点记录哪些环节跑通了、哪些没跑通、为什么。测试机型为 EBO MAX。

## 现状

| 环节 | 状态 |
| --- | --- |
| RTSP 音频 + ASR 转写 | ✅ 完全跑通并实测成功（真人说话能转成文字） |
| VAD 交互脚本 | ✅ 已写好并验证核心模块（开口即录、停顿断句） |
| 语音助手技能（含 TTS 桥接） | ✅ 已写好、校验通过 |
| 端到端对话 | ❌ 至今未在真实环境跑通 |

没跑通的原因不在代码：测试时旁边的视频一直在放声音，盖住了人声，唤醒词始终没被识别到。关掉视频后成功唤醒过 2 次。遇到这种情况先查环境，再查代码。

## 设计原则

脚本只负责听和说，理解指令的是 WorkBuddy Agent。两边通过两个 JSON 文件传递消息，不需要额外的 LLM API key。

和前两个项目的架构区别在于：

- 实战一（早间播报）：定时触发 + AI 编排
- 实战二（开门迎宾）：事件触发 + 纯 Python 常驻程序
- 实战三（语音助手）：语音触发 + 脚本与 Agent 分工协作

## 先分清两个无关的接口

早期把这两个接口混为一谈，导致连续误判。区别如下：

| 接口 | 地址 | 是否带音频 |
| --- | --- | --- |
| 设备本地 RTSP 流 | `rtsp://<LAN_IP>:554/main0`（内网、无认证） | ✅ 带音频轨 |
| 云端 MCP 接口 | `<EBO_MCP_ENDPOINT>`（Bearer token） | ❌ 15 个工具里没有任何音视频/RTSP 工具 |

RTSP 实测轨道（`ffprobe`）：

```
Stream #0:0: Video: hevc (Main), 2560x1440, 25fps   # 有 "PPS id out of range" 警告，无害
Stream #0:1: Audio: pcm_alaw, 8000 Hz, mono, 64 kb/s # G.711 a-law，电话音质
```

曾犯的错误（不要重犯）：一开始断言"RTSP 不带音频"，依据是第三方项目 `ha-enabot` 转发时默认加了 `-an`。那是它自己的转发配置，不是设备属性。开发说的"带音频"是对的。

另外，试探过 `robot_get_rtsp` / `robot_rtsp` / `get_rtsp` 等隐藏工具名，全部返回 `unknown tool`。官方 MCP 当前没有视频流 API——要音视频只能走 RTSP。

## 环境与依赖

| 项目 | 要求 |
| --- | --- |
| Python | 3.13，pip 26.1.2 |
| `av` | 必须锁 `av==15.0.0`（唯一可用档位） |
| 模型下载 | `HF_ENDPOINT=https://hf-mirror.com`（huggingface 直连不通），base / small 已下载 |
| Windows curl | 必须加 `--ssl-no-revoke`，否则报 `CRYPT_E_REVOCATION_OFFLINE` |
| ffmpeg | 9.0.2-full_build（gyan.dev），已在 PATH |

`av` 版本必须锁死，原因如下：

- `av 19.x`：`av.open()` 不接受 `metadata_errors` 参数 → faster-whisper 直接报错
- `av 14.x`：没有 Python 3.13 预编译 wheel，源码编译失败
- `av 15.0.0`：有 cp313 wheel 且兼容 ✅

安装命令：

```bash
pip install faster-whisper "av==15.0.0"
```

ffmpeg 的 stderr 会刷 `non monotonically increasing dts` / `PPS id out of range` / `skipping invalid undecodable nalu` 等无害警告，脚本里已过滤；不处理会淹没真正的输出。

精确依赖版本（`examples/03-voice-assistant/requirements.txt`）：

```text
faster-whisper==1.2.1
av==15.0.0
numpy==2.5.5
```

## 配套代码

[`examples/03-voice-assistant/`](../../examples/03-voice-assistant/README.md) 提供三个阶段的完整脚本：`ebo_rtsp_asr.py`（固定切段转写）、`ebo_voice_agent.py`（VAD 交互转写）、`voice_loop.py`（语音闭环），以及脚本与 Agent 之间的文件协议说明。

## 三个阶段的实现

### 阶段一：`ebo_rtsp_asr.py` — 固定切段转写（已交付、实测成功）

从 RTSP 音频轨持续抽 PCM，按固定 `--chunk` 秒切段喂 faster-whisper。

关键做法：ffmpeg 输出 `s16le / 16kHz / mono` 到 stdout（`-vn -ac 1 -ar 16000 -f s16le pipe:1`），Python 读满指定字节数再转 float32 喂模型——绕开 `av` 解码路径，比让 faster-whisper 自己解码更稳。

其他设计：RTSP 偶发断连（error -10054）自动重连；残段（不足一半）直接丢弃，不拿去转写。实测出过文字，例如 `[10:51:48] 这就是节奈网上的节奈`。

```bash
HF_ENDPOINT=https://hf-mirror.com python ebo_rtsp_asr.py \
  --url rtsp://<LAN_IP>:554/main0 --model small --language zh \
  --no-vad --prompt "Einstein EBO 普通话对话" --output transcript.txt
```

### 阶段二：`ebo_voice_agent.py` — VAD 驱动的交互转写（已交付、实测成功）

把"固定切段"升级为"开口即录、停顿断句"，更接近自然对话。

VAD 组件：faster-whisper 自带 Silero VAD（`faster_whisper.vad.get_vad_model()`），ONNX 模型随包，无需额外安装。

需要注意的点：逐帧（512 样本 / 32ms）直接调用 VAD，概率偏低不可靠；必须用滑动窗口批量调用——窗口 32 帧（1.024s），取最近 8 帧概率均值。实测静音 prob≈0.01–0.1，说话 0.6–0.95。

状态机：

```
IDLE →(prob≥0.5 且能量达标)→ SPEAKING →(prob<0.32 持续 1.2s 或超 20s)→ 输出整段
```

稳定性设计：

- pre-roll 0.5s 防吞开头字
- 滞回阈值 0.5 / 0.32 防抖
- `min_s` 0.6s 过滤咳嗽单字
- 有界队列 `maxsize=8`，转写跟不上时丢最旧段保延迟
- 采集线程与转写线程解耦；RTSP 自动重连；`--vad-debug` 打印端点事件

断句调参实测：文件模式下 45s 新闻朗读，初始切成 11 段过碎；把 `end_silence` 从 0.9 调到 1.2s 并加 `min_s` 过滤后，变成 5 个完整语义段。

```bash
python ebo_voice_agent.py --url rtsp://<LAN_IP>:554/main0 \
  --model small --language zh --vad-debug
# --file xxx.wav 可离线验证端点检测
```

### 阶段三：`ebo-voice-chat` 技能 — 串起整条流程（已写好、校验通过）

用户级 skill，包含 `SKILL.md` / `scripts/voice_loop.py` / `references/bridge_protocol.md`，`agent_created: true`，`quick_validate` 通过。

状态机：

```
WAIT_WAKE →(命中唤醒词)→ TTS"我在请说" → WAIT_COMMAND
  →(收到指令)→ 写 question.json → 轮询 answer.json → TTS 播报 → 回 WAIT_WAKE（默认单轮）
```

TTS 实现：curl POST 调 MCP `robot_speak`，参数 `text` + BCP-47 `lang`（如 `zh-CN`）；Windows 下 `--ssl-no-revoke` 必需。

```bash
HF_ENDPOINT=https://hf-mirror.com python <skill>/scripts/voice_loop.py \
  --url rtsp://<LAN_IP>:554/main0 --bridge ./bridge \
  --wake-word "MAX过来" --model small
```

Agent 侧驱动流程（关键，必须常驻轮询，不能发完就走）：

1. 后台启动脚本
2. 轮询 `bridge/question.json` 出现（阻塞 180 秒，覆盖用户走到机器人的时间）
3. 把 `text` 当作用户对我说的话来回答
4. 写 `bridge/answer.json`（`id` 必须与 question 一致）
5. 脚本自动播报，并归档为 `.done.N`；answer 超时默认 120s

回复要求：简洁、口语化、适合朗读，避免长句和难念符号。

## ASR 识别质量的注意事项

| 问题 | 结论 |
| --- | --- |
| 模型选择 | `base` 会出现重复幻觉（`对话对话对话`、`货物的货物`）；`small` 明显更准，CPU 上每句约 2–5s，模型加载 5–10s。默认已设为 small |
| 上下文串联 | 必设 `condition_on_previous_text=False`，否则上下文会放大幻觉 |
| 内置 VAD | `--no-vad`（faster-whisper 内置 VAD）在切好的短段上反而可能把有效语音过滤掉；VAD 交给 Silero 层做更合适 |
| 提示词 | `initial_prompt` 只放领域词（如 "Einstein EBO 普通话"），不要放期望识别出的整句——否则会把提示词幻觉成识别结果 |
| 音质硬瓶颈 | 8kHz 电话音质导致谐音错字（"致贺电"→"制鹤店"）和远场识别率下降，不是脚本 bug。要根治需绕开 RTSP、走底层 Agora 16kHz PCM |
| 延迟 | 当前是"说完一句再转写"，约 1–2s 延迟。要"边说边出字"需换流式 ASR（本地 whisper-streaming / faster-whisper-server，或云服务流式识别） |

做过对照实验：完全不带 prompt 也能识别出目标句，说明识别到的是真人声，不是提示词幻觉。

## 唤醒词匹配的注意事项

用户说"MAX过来"，Whisper 实际识别成"马克斯过来"和"馬克思過來"（繁体），字面 `in` 匹配会 100% 失败。做了两件事来解决：

- `normalize_text()` 做小写化 + 去空格标点 + 简繁统一（過→过、來→来、邁→迈、麥→麦、馬→马）
- `wake_aliases()` 生成 7 种谐音变体：`max / 麦克斯 / 马克思 / 迈克斯 / 马克斯 / 马斯 / 麦斯` + "过来"
- 只匹配"XX过来"完整组合，绝不能把裸 `max` 单独当别名——否则"这个 max 值很大"之类会误触发
- 繁简混合输入（如"过來"，简体过 + 繁体来）要补单字 `來→来` 替换，否则归一化后匹配不上

实测结果：成功唤醒 2 次，`[WAKE]` 命中记录正常；同时确认环境杂音（"但是过来""那过来"）不会误触发。唤醒词默认已改为 "MAX过来"（早期是 "Einstein"）。

## 现场环境带来的问题

RTSP 音频轨 = 机器人麦克风拾音，不是扬声器播放：

- 近距离（1 米内）说话拾取清楚，实测 RMS 1800–3600，远高于环境噪声 300–600
- 机器人自己的 TTS 播报不进这条轨（前 8 秒应为 TTS，转写为空）——扬声器声音被回声消除。好处是无自干扰；坏处是不能用 RTSP 验证机器人有没有在说话

视频/电视声音是最大的干扰：最近两轮完整测试，ASR 抓到的全是视频音频（字幕、配乐台词等），22 条转写里没有一条是用户说的"MAX过来"，导致 `question.json` 从未生成。之前唤醒成功那次，是用户关掉了视频。

> 结论：测试完整流程前必须关掉/彻底静音旁边的视频，用户走到机器人 1 米内说话。 这是当前唯一未打通的环节，与代码无关。

> 隐私提醒：涉及麦克风拾音，开启前确保空间内人员知情同意。

## 尚未完成 / 待办

- 端到端对话（唤醒 → TTS → 指令 ASR → Agent 回答 → TTS 播报）未在真实环境跑通，只验证了各模块单独工作；需在安静环境重测
- 未接任何云端流式 ASR / 关键词唤醒（KWS）；当前唤醒依赖 ASR 文本匹配，抗噪能力弱
- 早期"EBO RTSP 基本是纯视频"的说法已经作废，不要再引用

## 接手时需要注意的几点

1. 不要再推断 RTSP 是否带音频——带，`pcm_alaw` 8kHz mono，已实测
2. 需要识别人声时，用 VAD 版脚本（`ebo_voice_agent.py`）而不是固定切段版；模型用 `small`，关 `condition_on_previous_text`
3. 遇到 `av` 相关报错，先确认 `av==15.0.0`；模型下载失败确认 `HF_ENDPOINT`；curl 证书错加 `--ssl-no-revoke`
4. 驱动语音助手技能时，必须在同一轮对话里后台启动 + 轮询文件 + 读写 answer.json，不能启动完就结束回合
5. 如果用户报告"没成功 / 没唤醒"，先查 `voice_loop.log` 的 `[asr]` 行和 `[wake]` 行：若 ASR 全是视频声音，就是环境问题，让用户关视频重来，不要改代码

排查日志命令：

```bash
grep -E '\[wake\]|\[tts\]|\[bridge\]' voice_loop.log
grep '\[asr\]' voice_loop.log | tail -15
ls -la bridge/
```

## 与另两个项目的对照

| 维度 | 实战一：早间播报 | 实战二：开门迎宾 | 实战三：语音助手 |
| --- | --- | --- | --- |
| 触发方式 | 定时（每天 08:00） | 事件（门窗传感器） | 语音（唤醒词） |
| 编排方式 | AI 编排 | 纯 Python 常驻 | 脚本 + Agent 分工 |
| MCP 通道 | EBO HTTP | EBO HTTP + 米家 stdio | EBO HTTP + RTSP 音频 |
| 主要难点 | 状态轮询复核 | 状态残留、脏数据 | 音质、抗噪、环境 |
| 成熟度 | 长期线上运行 | 展会稳定运行 | 模块验证通过，端到端待安静环境复测 |
