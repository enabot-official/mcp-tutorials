#!/usr/bin/env python3
"""EBO RTSP -> VAD 驱动的交互式语音转写 (自然对话式端点检测).

相比固定切段 ebo_rtsp_asr.py, 本脚本用 Silero VAD 做语音活动检测:
  - 开口自动开始录音 (带 pre-roll, 不吞开头字)
  - 停顿自动断句并转写 (滞回阈值 + 静音超时, 不切半句)
  - 采集与转写双线程解耦, 转写慢时不丢失采集、不无限堆积
  - RTSP 断线自动重连; 支持唤醒词检测回调 (预留给 Einstein 场景)

用法:
  # 实时 RTSP
  python ebo_voice_agent.py --url rtsp://<CAMERA_IP>:554/main0

  # 离线文件 (验证端点检测效果)
  python ebo_voice_agent.py --file ebo_random_test.wav

  # 带唤醒词 + 输出文件
  python ebo_voice_agent.py --url ... --wake-word Einstein --output transcript.txt

依赖:
  pip install faster-whisper "av==15.0.0"     # av 19 与 faster-whisper 不兼容
  Silero VAD 模型随 faster-whisper 自带, 无需额外安装
  系统需有 ffmpeg 且在 PATH 中
"""

import argparse
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
FRAME = 512                 # 32ms/帧 (Silero VAD 要求 512 倍数)
HOP_FRAMES = 8              # 每 8 帧(0.256s)做一次 VAD 判定
WINDOW_FRAMES = 32          # 判定窗口 1.024s (批量调用 VAD, 概率更准)


def build_ffmpeg_cmd(source, is_url):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"]
    if is_url:
        cmd += ["-rtsp_transport", "tcp", "-i", source]
    else:
        cmd += ["-i", source]
    cmd += ["-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1"]
    return cmd


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


def bytes_to_float(b):
    return np.frombuffer(b, dtype=np.int16).astype(np.float32) / 32768.0


def frame_rms(frame):
    return float(np.sqrt(np.mean(frame * frame)))


def normalize_text(s):
    """归一化文本用于唤醒词匹配: 去空格标点、简繁统一、英文小写."""
    s = s.lower()
    s = re.sub(r"[\s,，。.!！?？、:：;；\-_'\"()（）]", "", s)
    for a, b in (("過", "过"), ("來", "来"), ("邁", "迈"),
                 ("麥", "麦"), ("馬", "马"), ("斯", "斯")):
        s = s.replace(a, b)
    return s


def wake_aliases(word):
    """给唤醒词生成常见谐音/变体别名 (针对 ASR 误识).

    只保留 "XX过来" 完整组合, 不放单别名 (如裸 'max' 太宽泛易误触发).
    """
    base = normalize_text(word)
    aliases = {base}
    if "max" in base or any(c in base for c in "麦迈马"):
        for v in ("max", "麦克斯", "马克思", "迈克斯", "马克斯", "马斯", "麦斯"):
            aliases.add(normalize_text(v + "过来"))
    return aliases


class UtteranceDetector:
    """基于 Silero VAD 的语音端点检测状态机.

    状态: IDLE (等待开口) -> SPEAKING (收集中) -> 静音超时 -> 输出整段.
    """

    def __init__(self, vad, start_th=0.5, end_th=0.32,
                 end_silence_s=1.2, max_s=20.0, pre_roll_s=0.5,
                 min_s=0.6, energy_floor=0.004, verbose=False):
        self.vad = vad
        self.start_th = start_th
        self.end_th = end_th
        self.end_hops = max(1, int(end_silence_s / (HOP_FRAMES * FRAME / SAMPLE_RATE)))
        self.max_frames = int(max_s * SAMPLE_RATE / FRAME)
        self.min_frames = int(min_s * SAMPLE_RATE / FRAME)
        self.pre_frames = int(pre_roll_s * SAMPLE_RATE / FRAME)
        self.energy_floor = energy_floor
        self.verbose = verbose

        self.window = deque(maxlen=WINDOW_FRAMES)   # VAD 判定窗口 (float32 frames)
        self.pre = deque(maxlen=self.pre_frames)    # pre-roll 环形缓存
        self.utt = []                               # 当前语音段的帧列表
        self.state = "IDLE"
        self.hop = 0
        self.silence_hops = 0

    def _prob(self):
        arr = np.concatenate(list(self.window))
        out = np.asarray(self.vad(arr)).reshape(-1)
        return float(out[-HOP_FRAMES:].mean())

    def feed(self, frame):
        """喂入一帧 (float32, len=FRAME). 返回完成的声音段 np.array 或 None."""
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
        if self.verbose and self.hop == 0:
            pass

        if self.state == "IDLE":
            if p >= self.start_th and energy_ok:
                self.state = "SPEAKING"
                self.utt = list(self.pre)   # 带上 pre-roll, 不吞开头
                self.silence_hops = 0
                if self.verbose:
                    print(f"[vad] START prob={p:.2f}", file=sys.stderr)
            return None

        # SPEAKING: 判定是否结束
        if p < self.end_th or not energy_ok:
            self.silence_hops += 1
        else:
            self.silence_hops = 0

        too_long = len(self.utt) >= self.max_frames
        ended_by_silence = self.silence_hops >= self.end_hops

        if ended_by_silence or too_long:
            # 裁掉尾部静音帧, 但保留 ~0.2s padding
            keep = len(self.utt)
            if ended_by_silence:
                trim = max(0, (self.silence_hops - 1) * HOP_FRAMES)
                keep = max(int(0.2 * SAMPLE_RATE / FRAME), len(self.utt) - trim)
            seg = np.concatenate(self.utt[:keep])
            why = "timeout" if too_long else "silence"
            self.state = "IDLE"
            self.utt = []
            self.silence_hops = 0
            # 太短的段多半是咳嗽/单字噪声, 直接丢弃, 不触发转写
            if len(seg) < self.min_frames:
                if self.verbose:
                    print(f"[vad] END ({why}) dur={len(seg)/SAMPLE_RATE:.1f}s "
                          f"-> 丢弃(过短)", file=sys.stderr)
                return None
            if self.verbose:
                print(f"[vad] END ({why}) dur={len(seg)/SAMPLE_RATE:.1f}s "
                      f"prob={p:.2f}", file=sys.stderr)
            return seg
        return None


def producer_loop(args, vad, out_q, stop_evt):
    """采集线程: 读音频 -> VAD 端点检测 -> 完整语音段入队."""
    det = UtteranceDetector(
        vad,
        start_th=args.start_th, end_th=args.end_th,
        end_silence_s=args.end_silence, max_s=args.max_s,
        pre_roll_s=args.pre_roll, min_s=args.min_s, verbose=args.vad_debug,
    )
    source = args.url if args.url else args.file
    is_url = source.lower().startswith(("rtsp://", "http://", "https://"))
    frame_bytes = FRAME * BYTES_PER_SAMPLE
    retry = 0
    seg_count = 0

    while not stop_evt.is_set():
        cmd = build_ffmpeg_cmd(source, is_url)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=frame_bytes * 4,
            )
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
                    if is_url:
                        break  # 断连残段, 触发重连
                    if len(raw) == 0:
                        break
                    raw = raw + b"\x00" * (frame_bytes - len(raw))  # 文件尾部补零
                frame = bytes_to_float(raw)
                seg = det.feed(frame)
                if seg is not None:
                    seg_count += 1
                    # 队列有界: 转写慢时丢最旧的段, 保证延迟不累积
                    try:
                        out_q.put_nowait((seg_count, seg))
                    except queue.Full:
                        try:
                            out_q.get_nowait()
                        except queue.Empty:
                            pass
                        out_q.put_nowait((seg_count, seg))
                        print("[warn] 转写跟不上, 丢弃一个旧语音段", file=sys.stderr)
                    retry = 0
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

        if not is_url:
            break  # 文件模式读完即结束
        if stop_evt.is_set():
            break
        retry += 1
        print(f"[warn] 音频断开 (第 {retry} 次), 2s 后重连...", file=sys.stderr)
        stop_evt.wait(2)

    out_q.put(None)  # 结束哨兵


def main():
    ap = argparse.ArgumentParser(description="EBO RTSP -> VAD 交互式语音转写")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="RTSP 地址")
    src.add_argument("--file", help="本地音频文件 (验证端点检测)")
    ap.add_argument("--model", default="small", help="Whisper 模型 (默认 small)")
    ap.add_argument("--language", default="zh", help="语言代码, 空为自动检测")
    ap.add_argument("--output", help="转写结果输出文件 (追加)")
    ap.add_argument("--prompt", default="", help="初始提示词 (领域词, 可选)")
    ap.add_argument("--wake-word", default="MAX过来", help="唤醒词, 命中时输出 [WAKE] 标记 (默认 MAX过来)")
    ap.add_argument("--start-th", type=float, default=0.5, help="VAD 起点概率阈值")
    ap.add_argument("--end-th", type=float, default=0.32, help="VAD 终点概率阈值")
    ap.add_argument("--end-silence", type=float, default=1.2, help="静音断句时长(秒)")
    ap.add_argument("--max-s", type=float, default=20.0, help="单段最长(秒)")
    ap.add_argument("--min-s", type=float, default=0.6, help="最短有效段(秒), 更短丢弃")
    ap.add_argument("--pre-roll", type=float, default=0.5, help="起始回看(秒)")
    ap.add_argument("--energy-floor", type=float, default=0.004, help="最低能量阈值")
    ap.add_argument("--vad-debug", action="store_true", help="打印 VAD 起止事件")
    ap.add_argument("--hf-mirror", action="store_true", help="用 hf-mirror 下载模型")
    args = ap.parse_args()

    if args.hf_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    print("[info] 加载 VAD 模型...", flush=True)
    from faster_whisper.vad import get_vad_model
    vad = get_vad_model()

    print(f"[info] 加载 ASR 模型 {args.model}...", flush=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    wake_set = wake_aliases(args.wake_word) if args.wake_word else set()
    if wake_set:
        print(f"[info] 唤醒词 '{args.wake_word}', 匹配变体: {sorted(wake_set)}", flush=True)
    print("[info] 模型就绪. 开口说话, 停顿自动断句转写. Ctrl+C 停止.\n", flush=True)

    out_q = queue.Queue(maxsize=8)
    stop_evt = threading.Event()
    t = threading.Thread(target=producer_loop, args=(args, vad, out_q, stop_evt), daemon=True)
    t.start()

    try:
        while not stop_evt.is_set():
            try:
                item = out_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            seg_id, seg = item
            kw = dict(language=args.language, vad_filter=False, beam_size=5,
                      condition_on_previous_text=False)
            if args.prompt:
                kw["initial_prompt"] = args.prompt
            try:
                segments, _ = model.transcribe(seg, **kw)
                text = " ".join(s.text.strip() for s in segments if s.text.strip())
            except Exception as e:
                print(f"[error] 转写失败: {e}", file=sys.stderr)
                continue

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dur = len(seg) / SAMPLE_RATE
            if text:
                line = f"[{ts}] ({dur:.1f}s) {text}"
                print(line, flush=True)
                if args.output:
                    with open(args.output, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                if wake_set:
                    nt = normalize_text(text)
                    hit = next((a for a in wake_set if a and a in nt), None)
                    if hit:
                        print(f"  >>> [WAKE] 命中唤醒词 (匹配 '{hit}')", flush=True)
            else:
                print(f"[{ts}] ({dur:.1f}s) (无语音)", flush=True)
    except KeyboardInterrupt:
        print("\n[info] 用户中断", file=sys.stderr)
    finally:
        stop_evt.set()
        t.join(timeout=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
