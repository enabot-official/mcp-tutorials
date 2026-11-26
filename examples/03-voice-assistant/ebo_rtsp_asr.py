#!/usr/bin/env python3
"""EBO RTSP -> ASR 实时转写工具.

从 EBO 的 RTSP 音频轨 (pcm_alaw 8kHz mono) 持续抽取音频,
用 faster-whisper 转成文字,输出到终端并可选写入文件.

用法:
  # 实时转写 RTSP
  python ebo_rtsp_asr.py --url rtsp://<CAMERA_IP>:554/main0

  # 只转写一个 wav 文件
  python ebo_rtsp_asr.py --file ebo_audio_30s.wav

  # 实测最佳组合 (small 模型 + 领域提示词 + 关闭 VAD)
  python ebo_rtsp_asr.py --url ... --model small --no-vad --prompt "今天天气很好 Einstein 过来 普通话对话"

依赖:
  pip install faster-whisper "av==15.0.0"   # av 19 与 faster-whisper 不兼容
  系统需有 ffmpeg 且在 PATH 中

实测结论 (2026-11-24):
  - RTSP 音频轨 = 机器人麦克风拾音 (pcm_alaw 8kHz mono), 能抓到近距离人声;
    机器人自身 TTS 从扬声器播放, 不出现在该音频轨里 (回声消除).
  - base 模型会出现重复幻觉 (如 "对话对话对话"), small 模型 + initial_prompt
    + condition_on_previous_text=False 可正确识别整句.
"""

import argparse
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

import numpy as np

# 中文网络环境下可选镜像; 用 --hf-mirror 开启
# os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2  # s16le mono


def build_ffmpeg_cmd(source, is_url):
    """构造 ffmpeg 命令: 输入 -> 16kHz 单声道 s16le PCM 输出到 stdout."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"]
    if is_url:
        cmd += ["-rtsp_transport", "tcp", "-i", source]
    else:
        cmd += ["-i", source]
    cmd += ["-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1"]
    return cmd


def drain_stderr(proc, quiet=True):
    """持续读取 stderr 防止管道阻塞; 只打印可疑错误."""
    for line in iter(proc.stderr.readline, b""):
        text = line.decode("utf-8", errors="replace").strip()
        # 忽略已知的无害警告
        if any(k in text.lower() for k in ("non monotonically increasing dts", "pps id out of range", "skipping invalid undecodable nalu")):
            continue
        if not quiet or any(k in text.lower() for k in ("error", "failed", "cannot", "invalid")):
            print(f"[ffmpeg] {text}", file=sys.stderr)


def read_exact(stream, nbytes):
    """从管道读满 nbytes 才返回; 流提前结束则返回已读到的部分(或 None)."""
    buf = bytearray()
    while len(buf) < nbytes:
        chunk = stream.read(nbytes - len(buf))
        if not chunk:
            return bytes(buf) if buf else None
        buf.extend(chunk)
    return bytes(buf)


def pcm_to_float(pcm_bytes):
    """s16le bytes -> float32 numpy array (faster-whisper 输入格式)."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return arr


def transcribe_chunk(model, pcm_bytes, language, vad, initial_prompt=""):
    """转写一段 PCM, 返回拼接后的文本."""
    audio = pcm_to_float(pcm_bytes)
    kwargs = dict(
        language=language,
        vad_filter=vad,
        beam_size=5,
        condition_on_previous_text=False,
    )
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt
    segments, _info = model.transcribe(audio, **kwargs)
    parts = [s.text.strip() for s in segments if s.text.strip()]
    return " ".join(parts)


def write_transcript(path, timestamp, text):
    line = f"[{timestamp}] {text}"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return line


def run_live(args, model):
    """实时模式: 持续从 RTSP 读音频, 按 chunk 秒转写."""
    chunk_bytes = int(args.chunk * SAMPLE_RATE * BYTES_PER_SAMPLE)
    is_url = args.url.lower().startswith(("rtsp://", "http://", "https://"))
    source = args.url
    reconnect_delay = 2

    print(f"[info] 源: {source}")
    print(f"[info] 每段 {args.chunk}s, 模型 {args.model}, 语言 {args.language or 'auto'}")
    if args.output:
        print(f"[info] 转写结果写入: {args.output}")
    print("[info] Ctrl+C 停止\n")

    retry = 0
    while True:
        cmd = build_ffmpeg_cmd(source, is_url)
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=chunk_bytes * 2
            )
        except FileNotFoundError:
            print("[error] 找不到 ffmpeg, 请先安装并加入 PATH", file=sys.stderr)
            return 1

        t = threading.Thread(target=drain_stderr, args=(proc, True), daemon=True)
        t.start()

        try:
            while proc.poll() is None:
                pcm = read_exact(proc.stdout, chunk_bytes)
                if pcm is None:
                    break
                if len(pcm) < chunk_bytes * 0.5:
                    # 断连时只拿到残段, 跳出内层循环触发重连, 不要用残段去转写
                    print(f"[warn] 读到不完整音频段 ({len(pcm)}/{chunk_bytes} 字节), 重连...", file=sys.stderr)
                    break

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    text = transcribe_chunk(model, pcm, args.language, not args.no_vad, args.prompt)
                except Exception as e:
                    print(f"[error] 转写失败: {e}", file=sys.stderr)
                    continue

                if not text:
                    print(f"[{ts}] (无语音)")
                    continue

                line = f"[{ts}] {text}"
                print(line, flush=True)
                if args.output:
                    write_transcript(args.output, ts, text)
                retry = 0  # 成功读到数据, 重置重连计数

        except KeyboardInterrupt:
            print("\n[info] 用户中断, 停止中...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return 0
        finally:
            if proc.poll() is None:
                proc.terminate()

        retry += 1
        print(f"[warn] ffmpeg 断开 (第 {retry} 次), {reconnect_delay}s 后重连...", file=sys.stderr)
        time.sleep(reconnect_delay)


def run_file(args, model):
    """单文件模式: 转写一个音频文件."""
    cmd = build_ffmpeg_cmd(args.file, False)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t = threading.Thread(target=drain_stderr, args=(proc, True), daemon=True)
    t.start()

    all_pcm = bytearray()
    while True:
        chunk = proc.stdout.read(65536)
        if not chunk:
            break
        all_pcm.extend(chunk)
    proc.wait()

    if not all_pcm:
        print("[error] 未读到音频数据", file=sys.stderr)
        return 1

    duration = len(all_pcm) / (SAMPLE_RATE * BYTES_PER_SAMPLE)
    print(f"[info] 音频时长 {duration:.1f}s")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = transcribe_chunk(model, bytes(all_pcm), args.language, not args.no_vad, args.prompt)
    line = f"[{ts}] {text if text else '(无语音)'}"
    print(line)
    if args.output:
        write_transcript(args.output, ts, text)
    return 0


def main():
    parser = argparse.ArgumentParser(description="EBO RTSP 音频 -> ASR 文字")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="RTSP 地址, 如 rtsp://<CAMERA_IP>:554/main0")
    src.add_argument("--file", help="单个音频文件路径 (wav/mp3 等)")
    parser.add_argument("--chunk", type=float, default=10.0, help="实时模式每段秒数 (默认 10)")
    parser.add_argument("--model", default="small", help="Whisper 模型: tiny/base/small/medium (默认 small, 识别更准)")
    parser.add_argument("--language", default="zh", help="语言代码, 如 zh/en/da; 空字符串为自动检测 (默认 zh)")
    parser.add_argument("--output", help="转写结果输出文件 (追加写入)")
    parser.add_argument("--no-vad", action="store_true", help="关闭 VAD 静音过滤(默认开启)")
    parser.add_argument("--prompt", default="", help="初始提示词, 可提升专有名词识别率, 如 'Einstein, EBO'")
    parser.add_argument("--hf-mirror", action="store_true", help="使用 hf-mirror.com 下载模型")
    args = parser.parse_args()

    if args.hf_mirror:
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    print(f"[info] 加载模型 {args.model} ...", flush=True)
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device="cpu", compute_type="int8")
    except Exception as e:
        print(f"[error] 模型加载失败: {e}", file=sys.stderr)
        return 1
    print("[info] 模型就绪\n", flush=True)

    if args.file:
        return run_file(args, model)
    return run_live(args, model)


if __name__ == "__main__":
    sys.exit(main())
