# 实战三配套代码：语音助手

对应教程：[实战三：把 EBO 改造成语音助手](../../docs/zh-CN/project-03-voice-assistant.md)。

三个脚本对应教程里的三个阶段：固定切段转写 → VAD 交互转写 → 语音闭环。

## 环境

- Python 3.13、pip 26.1.2
- 依赖见 `requirements.txt`：`faster-whisper==1.2.1`、`av==15.0.0`、`numpy==2.5.5`
- 系统依赖：ffmpeg 9.0.2 full build（需在 PATH）、curl
- 国内下载模型可设置 `HF_ENDPOINT=https://hf-mirror.com`

`av` 版本必须锁 15.0.0：14 没有 Python 3.13 的 wheel，19 与 faster-whisper 不兼容。

## 文件

| 文件 | 阶段 | 作用 |
| --- | --- | --- |
| `ebo_rtsp_asr.py` | 一 | 从 RTSP 音频轨固定切段转文字，输出终端或写入文件 |
| `ebo_voice_agent.py` | 二 | Silero VAD 检测语音起止，开口即录、停顿断句 |
| `voice_loop.py` | 三 | 完整闭环：唤醒 → TTS → 听指令 → 交给 Agent → TTS 回应 |
| `bridge_protocol.md` | 三 | 脚本与 Agent 之间 JSON 文件的约定 |
| `requirements.txt` | — | 精确依赖版本 |

## 用法

```bash
pip install -r requirements.txt

# 阶段一：实时转写
python ebo_rtsp_asr.py --url rtsp://<CAMERA_IP>:554/main0 --model small --language zh

# 阶段二：VAD 交互转写
python ebo_voice_agent.py --url rtsp://<CAMERA_IP>:554/main0 --model small --vad-debug

# 阶段三：语音闭环（token 通过参数传入，不要写进文件）
python voice_loop.py --url rtsp://<CAMERA_IP>:554/main0 --bridge ./bridge --wake-word "MAX过来" --model small
```

RTSP 地址从机器人 APP 开启视频流后获取，走局域网。

## 两点提醒

1. 机器人自己的 TTS 声音不会进入 RTSP 音频轨（回声消除），所以不能用它验证机器人有没有在说话。
2. 端到端闭环测试前要静音旁边的电视或视频，否则人声会被盖住，唤醒词识别不到。这是环境问题，不是代码问题。

## 隐私

脚本会拾取麦克风声音。开启前确保空间内人员知情同意，转写内容按当地法规妥善保管。
