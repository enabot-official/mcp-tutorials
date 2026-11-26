#!/usr/bin/env python3
"""EBO Max 语音助手闭环 (唤醒 -> TTS -> 听指令 -> ASR -> 交给 Agent -> TTS 回应).

本脚本是常驻桥接进程, 实现"耳朵和嘴":
  1. 监听 RTSP 音频, VAD 自动检测说话起止
  2. 命中唤醒词 (默认 MAX过来) -> TTS 回应 "我在, 请说"
  3. 收集下一段语音作为用户指令, ASR 转文字 -> 写入 question.json
  4. 轮询 answer.json (由 WorkBuddy Agent 写入) -> TTS 播报 -> 回到步骤 1

"大脑"由 WorkBuddy Agent 承担: Agent 读 question.json, 把内容当作用户发言
理解并生成回复, 写入 answer.json。脚本不自己调用 LLM, 因此无需 API key。

用法:
  python voice_loop.py --url rtsp://<CAMERA_IP>:554/main0 \
      --bridge ./bridge --wake-word "MAX过来" --model small

桥接文件协议 (见 references/bridge_protocol.md):
  bridge/question.json  {"id": N, "text": "...", "ts": "..."}   脚本写入
  bridge/answer.json    {"id": N, "text": "..."}                Agent 写入
  id 必须匹配, 播报后脚本把两文件改名为 .done.N

依赖:
  pip install faster-whisper "av==15.0.0"
  ffmpeg 在 PATH 中; MCP TTS 通过 curl 调用 (Windows 需 --ssl-no-revoke)
"""

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime

import numpy as np

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
FRAME = 512
HOP_FRAMES = 8
WINDOW_FRAMES = 32

# MCP TTS 默认配置 (可用 --mcp-url / --mcp-token 覆盖, 或环境变量)
DEFAULT_MCP_URL = "<EBO_MCP_ENDPOINT>"
DEFAULT_MCP_TOKEN = "ebo_mcp_71P2lCoji5ewnOvAbdarjsbdeR07XI0L"


# ----------------------------- 文本工具 -----------------------------

def normalize_text(s):
    s = s.lower()
    s = re.sub(r"[\s,，。.!！?？、:：;；\-_'\"()（）]", "", s)
    for a, b in (("過", "过"), ("來", "来"), ("邁", "迈"), ("麥", "麦"), ("馬", "马")):
        s = s.replace(a, b)
    return s


def wake_aliases(word):
    base = normalize_text(word)
    aliases = {base}
    if "max" in base or any(c in base for c in "麦迈马"):
        for v in ("max", "麦克斯", "马克思", "迈克斯", "马克斯", "马斯", "麦斯"):
            aliases.add(normalize_text(v + "过来"))
    return aliases


def tts_strip_command(text):
    """去掉指令里常见的唤醒词, 避免把 'MAX过来' 也当作问题内容."""
    return text.strip()


# ----------------------------- MCP TTS -----------------------------

class TTS:
    def __init__(self, url, token, lang="zh-CN"):
        self.url = url
        self.token = token
        self.lang = lang
        self._id = 100

    def speak(self, text):
        if not text or not text.strip():
            return True
        self._id += 1
        payload = {
            "jsonrpc": "2.0", "id": self._id, "method": "tools/call",
            "params": {"name": "robot_speak",
                       "arguments": {"text": text.strip(), "lang": self.lang}},
        }
        cmd = ["curl", "-sS", "--ssl-no-revoke", "-X", "POST", self.url,
               "-H", f"Authorization: Bearer {self.token}",
               "-H", "Content-Type: application/json",
               "-H", "Accept: application/json, text/event-stream",
               "--data", json.dumps(payload, ensure_ascii=False)]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            ok = '"isError":false' in out.stdout.replace(" ", "")
            print(f"[tts] {'OK' if ok else 'FAIL'} '{text.strip()}'", flush=True)
            if not ok:
                print(f"[tts] resp: {out.stdout[:300]}", file=sys.stderr)
            return ok
        except Exception as e:
            print(f"[tts] error: {e}", file=sys.stderr)
            return False


# ----------------------------- 音频采集 -----------------------------

def build_ffmpeg_cmd(source):
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
            "-rtsp_transport", "tcp", "-i", source,
            "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1"]


def drain_stderr(proc):
    for line in iter(proc.stderr.readline, b""):
        t = line.decode("utf-8", errors="replace").strip()
        if any(k in t.lower() for k in ("non monotonically increasing dts",
                                        "pps id out of range",
                                        "skipping invalid undecodable nalu")):
            continue
        if any(k in t.lower() for k in ("error", "failed", "cannot", "invalid")):
            print(f"[ffmpeg] {t}", file=sys.stderr)


def read_exact(stream, nbytes):
    buf = bytearray()
    while len(buf) < nbytes:
        chunk = stream.read(nbytes - len(buf))
        if not chunk:
            return bytes(buf) if buf else None
        buf.extend(chunk)
    return bytes(buf)


def frame_rms(frame):
    return float(np.sqrt(np.mean(frame * frame)))


class UtteranceDetector:
    """VAD 端点检测: 开口录, 停顿断."""

    def __init__(self, vad, start_th=0.5, end_th=0.32, end_silence_s=1.2,
                 max_s=20.0, pre_roll_s=0.5, min_s=0.5, energy_floor=0.004):
        self.vad = vad
        self.start_th = start_th
        self.end_th = end_th
        self.end_hops = max(1, int(end_silence_s / (HOP_FRAMES * FRAME / SAMPLE_RATE)))
        self.max_frames = int(max_s * SAMPLE_RATE / FRAME)
        self.min_frames = int(min_s * SAMPLE_RATE / FRAME)
        self.pre_frames = int(pre_roll_s * SAMPLE_RATE / FRAME)
        self.energy_floor = energy_floor
        self.window = deque(maxlen=WINDOW_FRAMES)
        self.pre = deque(maxlen=self.pre_frames)
        self.utt = []
        self.state = "IDLE"
        self.hop = 0
        self.silence_hops = 0

    def reset(self):
        self.utt = []
        self.state = "IDLE"
        self.silence_hops = 0
        self.hop = 0

    def _prob(self):
        arr = np.concatenate(list(self.window))
        out = np.asarray(self.vad(arr)).reshape(-1)
        return float(out[-HOP_FRAMES:].mean())

    def feed(self, frame):
        self.window.append(frame)
        self.pre.append(frame)
        self.hop += 1
        energy_ok = frame_rms(frame) >= self.energy_floor
        if self.state == "SPEAKING":
            self.utt.append(frame)
        if self.hop < HOP_FRAMES or len(self.window) < WINDOW_FRAMES:
            return None
        self.hop = 0
        p = self._prob()

        if self.state == "IDLE":
            if p >= self.start_th and energy_ok:
                self.state = "SPEAKING"
                self.utt = list(self.pre)
                self.silence_hops = 0
            return None

        if p < self.end_th or not energy_ok:
            self.silence_hops += 1
        else:
            self.silence_hops = 0

        too_long = len(self.utt) >= self.max_frames
        ended = self.silence_hops >= self.end_hops
        if ended or too_long:
            keep = len(self.utt)
            if ended:
                trim = max(0, (self.silence_hops - 1) * HOP_FRAMES)
                keep = max(int(0.2 * SAMPLE_RATE / FRAME), len(self.utt) - trim)
            seg = np.concatenate(self.utt[:keep])
            self.state = "IDLE"
            self.utt = []
            self.silence_hops = 0
            if len(seg) < self.min_frames:
                return None
            return seg
        return None


# ----------------------------- 桥接文件 -----------------------------

class Bridge:
    def __init__(self, directory):
        self.dir = directory
        self.question = os.path.join(directory, "question.json")
        self.answer = os.path.join(directory, "answer.json")
        os.makedirs(directory, exist_ok=True)

    def clear(self):
        for p in (self.question, self.answer):
            if os.path.exists(p):
                os.remove(p)

    def write_question(self, qid, text):
        tmp = self.question + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"id": qid, "text": text,
                       "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                      f, ensure_ascii=False)
        os.replace(tmp, self.question)
        print(f"[bridge] question #{qid} 已写入: {text}", flush=True)

    def poll_answer(self, qid, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(self.answer):
                try:
                    with open(self.answer, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == qid and str(data.get("text", "")).strip():
                        return str(data["text"]).strip()
                except Exception:
                    pass
            time.sleep(0.3)
        return None

    def archive(self, qid):
        for p in (self.question, self.answer):
            if os.path.exists(p):
                try:
                    os.replace(p, p + f".done.{qid}")
                except OSError:
                    pass


# ----------------------------- 主循环 -----------------------------

def audio_producer(source, audio_q, stop_evt):
    frame_bytes = FRAME * BYTES_PER_SAMPLE
    while not stop_evt.is_set():
        proc = None
        try:
            proc = subprocess.Popen(
                build_ffmpeg_cmd(source), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=frame_bytes * 4)
        except FileNotFoundError:
            print("[error] 找不到 ffmpeg", file=sys.stderr)
            stop_evt.set()
            return
        threading.Thread(target=drain_stderr, args=(proc,), daemon=True).start()
        try:
            while proc.poll() is None and not stop_evt.is_set():
                raw = read_exact(proc.stdout, frame_bytes)
                if raw is None:
                    break
                if len(raw) < frame_bytes:
                    break
                audio_q.put(frame_bytes and raw)
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if stop_evt.is_set():
            break
        print("[warn] 音频断开, 2s 后重连...", file=sys.stderr)
        stop_evt.wait(2)


def main():
    ap = argparse.ArgumentParser(description="EBO Max 语音助手闭环 (桥接 Agent 大脑)")
    ap.add_argument("--url", default="rtsp://<CAMERA_IP>:554/main0", help="RTSP 地址")
    ap.add_argument("--bridge", default="./bridge", help="桥接目录")
    ap.add_argument("--wake-word", default="MAX过来", help="唤醒词")
    ap.add_argument("--model", default="small", help="Whisper 模型")
    ap.add_argument("--language", default="zh", help="ASR 语言")
    ap.add_argument("--wake-tts", default="我在, 请说", help="唤醒后的 TTS 回应")
    ap.add_argument("--answer-timeout", type=float, default=120.0,
                    help="等待 Agent 回复的秒数")
    ap.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    ap.add_argument("--mcp-token", default=DEFAULT_MCP_TOKEN)
    ap.add_argument("--tts-lang", default="zh-CN")
    ap.add_argument("--exit-words", default="退出,再见,结束,停止", help="说到这些词则结束")
    ap.add_argument("--hf-mirror", action="store_true")
    args = ap.parse_args()

    if args.hf_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    print("[info] 加载 VAD / ASR 模型...", flush=True)
    from faster_whisper.vad import get_vad_model
    from faster_whisper import WhisperModel
    vad = get_vad_model()
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    tts = TTS(args.mcp_url, args.mcp_token, args.tts_lang)
    bridge = Bridge(os.path.abspath(args.bridge))
    bridge.clear()
    wake_set = wake_aliases(args.wake_word)
    exit_set = {normalize_text(w) for w in args.exit_words.split(",") if w}
    detector = UtteranceDetector(vad)

    audio_q = queue.Queue(maxsize=200)
    stop_evt = threading.Event()
    threading.Thread(target=audio_producer, args=(args.url, audio_q, stop_evt),
                     daemon=True).start()

    print(f"[info] 唤醒词: {args.wake_word} (变体 {len(wake_set)})", flush=True)
    print(f"[info] 桥接目录: {bridge.dir}", flush=True)
    print(f"[info] 就绪. 说 '{args.wake_word}' 唤醒. Ctrl+C 停止.\n", flush=True)

    state = "WAIT_WAKE"
    qid = 0
    try:
        while not stop_evt.is_set():
            try:
                raw = audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            frame = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            seg = detector.feed(frame)
            if seg is None:
                continue

            segments, _ = model.transcribe(
                seg, language=args.language, vad_filter=False,
                beam_size=5, condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segments if s.text.strip())
            if not text:
                continue
            nt = normalize_text(text)
            print(f"[asr] {text}", flush=True)

            if state == "WAIT_WAKE":
                hit = next((a for a in sorted(wake_set) if a and a in nt), None)
                if hit:
                    print(f"[wake] 命中 '{hit}'", flush=True)
                    detector.reset()
                    tts.speak(args.wake_tts)
                    state = "WAIT_COMMAND"
                continue

            # WAIT_COMMAND: 用户指令 -> 交给 Agent
            if any(w in nt for w in exit_set):
                tts.speak("好的, 再见")
                break
            qid += 1
            bridge.write_question(qid, tts_strip_command(text))
            answer = bridge.poll_answer(qid, args.answer_timeout)
            if answer:
                tts.speak(answer)
                bridge.archive(qid)
                print("[info] 已播报回复, 继续监听.\n", flush=True)
            else:
                tts.speak("抱歉, 我没收到回复, 请再说一次")
                bridge.archive(qid)
            detector.reset()
            state = "WAIT_WAKE"  # 单轮对话; 如需连续对话可改为 WAIT_COMMAND
    except KeyboardInterrupt:
        print("\n[info] 用户中断", file=sys.stderr)
    finally:
        stop_evt.set()
    return 0


if __name__ == "__main__":
    sys.exit(main())
