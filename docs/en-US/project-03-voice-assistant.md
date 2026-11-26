# Project 3: Turning EBO into a Voice Assistant

> The third project wires EBO into a voice pipeline: wake word → TTS acknowledgement → listen for a command → ASR transcription → the WorkBuddy Agent interprets it → TTS reply.
>
> Based on hands-on work and testing between 2026-11-24 and 11-26. It records what worked, what didn't, and why.

## Current Status

| Stage | Status |
| --- | --- |
| RTSP audio + ASR transcription | ✅ Fully working and field-tested (real speech transcribed to text) |
| VAD interaction script | ✅ Written and core modules verified (start on speech, break on pause) |
| Voice assistant skill (with TTS bridge) | ✅ Written and validated |
| Full end-to-end conversation | ❌ Not yet run successfully in the real environment |

The cause was not in the code: during testing, a TV or video nearby played continuously and drowned out the user's voice, so the wake word was never recognized. After the video was turned off, wake-up succeeded twice. Check the environment before changing code.

## Design Principle

The script only handles listening and speaking; the WorkBuddy Agent understands commands. The two exchange messages through two JSON files, so no LLM API key is needed.

Compared with the other two projects:

- Project 1 (morning briefing): scheduled trigger + AI orchestration
- Project 2 (door welcome): event trigger + standalone Python daemon
- Project 3 (voice assistant): voice trigger + script/Agent division of labor

## First, Separate Two Unrelated Interfaces

These two interfaces were confused early on, causing a string of misdiagnoses. The difference:

| Interface | Address | Has audio? |
| --- | --- | --- |
| Device-local RTSP stream | `rtsp://<LAN_IP>:554/main0` (LAN, no auth) | ✅ Has an audio track |
| Cloud MCP endpoint | `<EBO_MCP_ENDPOINT>` (Bearer token) | ❌ None of the 15 tools expose A/V or RTSP |

Measured RTSP tracks (`ffprobe`):

```
Stream #0:0: Video: hevc (Main), 2560x1440, 25fps   # "PPS id out of range" warning is harmless
Stream #0:1: Audio: pcm_alaw, 8000 Hz, mono, 64 kb/s # G.711 a-law, telephone quality
```

A mistake already made (don't repeat it): we initially claimed "RTSP has no audio", based on a third-party project (`ha-enabot`) adding `-an` when forwarding. That was its own forwarding config, not a device property. The developer was right — it does carry audio.

We also probed hidden tool names like `robot_get_rtsp` / `robot_rtsp` / `get_rtsp` — all returned `unknown tool`. The official MCP has no video-stream API — for A/V you must use RTSP.

## Environment and Dependencies

| Item | Requirement |
| --- | --- |
| Python | 3.13, pip 26.1.2 |
| `av` | Pin `av==15.0.0` (the only working version) |
| Model download | `HF_ENDPOINT=https://hf-mirror.com` (direct huggingface unreachable); base and small downloaded |
| Windows curl | Add `--ssl-no-revoke`, otherwise `CRYPT_E_REVOCATION_OFFLINE` |
| ffmpeg | 9.0.2-full_build (gyan.dev), already on PATH |

The `av` version is locked for these reasons:

- `av 19.x`: `av.open()` no longer accepts `metadata_errors` → faster-whisper errors out
- `av 14.x`: no cp313 prebuilt wheel, source build fails
- `av 15.0.0`: has a cp313 wheel and is compatible ✅

Install command:

```bash
pip install faster-whisper "av==15.0.0"
```

ffmpeg's stderr floods with harmless warnings (`non monotonically increasing dts`, `PPS id out of range`, `skipping invalid undecodable nalu`). The scripts filter them; otherwise they drown out real output.

## Three Stages of Implementation

### Stage 1: `ebo_rtsp_asr.py` — Fixed-chunk transcription (delivered, tested successfully)

Continuously pulls PCM from the RTSP audio track and feeds fixed `--chunk`-second segments into faster-whisper.

Key technique: ffmpeg writes `s16le / 16kHz / mono` to stdout (`-vn -ac 1 -ar 16000 -f s16le pipe:1`), Python reads the exact byte count, converts to float32, and feeds the model — bypassing the `av` decode path, more stable than letting faster-whisper decode itself.

Also: automatic reconnect on intermittent RTSP drops (error -10054); partial segments (less than half) are discarded. Real output observed, e.g. `[10:51:48] ...`.

```bash
HF_ENDPOINT=https://hf-mirror.com python ebo_rtsp_asr.py \
  --url rtsp://<LAN_IP>:554/main0 --model small --language zh \
  --no-vad --prompt "Einstein EBO Mandarin dialogue" --output transcript.txt
```

### Stage 2: `ebo_voice_agent.py` — VAD-driven interactive transcription (delivered, tested successfully)

Upgrades "fixed chunks" to "start on speech, break on pause", much closer to natural conversation.

VAD component: Silero VAD bundled with faster-whisper (`faster_whisper.vad.get_vad_model()`), ONNX model ships with the package — no extra install.

Pitfall to avoid: calling VAD frame by frame (512 samples / 32ms) gives low, unreliable probabilities; use a sliding window in batches — 32-frame window (1.024s), averaging the most recent 8 frame probabilities. Measured: silence prob ≈ 0.01–0.1, speech 0.6–0.95.

State machine:

```
IDLE →(prob≥0.5 and energy OK)→ SPEAKING →(prob<0.32 for 1.2s or >20s)→ emit segment
```

Stability design:

- pre-roll 0.5s to avoid clipping the first syllable
- hysteresis thresholds 0.5 / 0.32 to prevent flapping
- `min_s` 0.6s filters coughs and single syllables
- bounded queue `maxsize=8`: drops the oldest segment when transcription lags, preserving latency
- decoupled capture and transcription threads; RTSP auto-reconnect; `--vad-debug` prints endpoint events

Segmentation tuning: in file mode with a 45s news reading, the initial setting produced 11 over-fragmented segments; raising `end_silence` from 0.9 to 1.2s and adding `min_s` filtering produced 5 complete semantic segments.

```bash
python ebo_voice_agent.py --url rtsp://<LAN_IP>:554/main0 \
  --model small --language zh --vad-debug
# --file xxx.wav validates endpoint detection offline
```

### Stage 3: `ebo-voice-chat` skill — tying it together (written, validated)

A user-level skill with `SKILL.md` / `scripts/voice_loop.py` / `references/bridge_protocol.md`; `agent_created: true`, `quick_validate` passed.

State machine:

```
WAIT_WAKE →(wake word hit)→ TTS "I'm here, go ahead" → WAIT_COMMAND
  →(command received)→ write question.json → poll answer.json → TTS reply → back to WAIT_WAKE (single turn by default)
```

TTS implementation: curl POST to MCP `robot_speak` with `text` and a BCP-47 `lang` (e.g. `zh-CN`); `--ssl-no-revoke` is required on Windows.

```bash
HF_ENDPOINT=https://hf-mirror.com python <skill>/scripts/voice_loop.py \
  --url rtsp://<LAN_IP>:554/main0 --bridge ./bridge \
  --wake-word "MAX过来" --model small
```

Agent-side driver (critical: stay resident and poll — never end the turn after launch):

1. Start the script in the background
2. Poll for `bridge/question.json` to appear (block up to 180 seconds, covering the time the user walks to the robot)
3. Treat `text` as something the user just said to you and answer it
4. Write `bridge/answer.json` (`id` must match the question's)
5. The script speaks the reply automatically and archives it as `.done.N`; answer timeout defaults to 120s

Reply style: concise, conversational, easy to read aloud — avoid long sentences and hard-to-pronounce symbols.

## ASR Pitfalls (Recognition Quality)

| Pitfall | Conclusion |
| --- | --- |
| Model choice | `base` produces repetition hallucinations (`dialogue dialogue dialogue`); `small` is clearly more accurate — about 2–5s per sentence on CPU, 5–10s model load. Default is now small |
| Context chaining | Always set `condition_on_previous_text=False`, otherwise context amplifies hallucinations |
| Built-in VAD | `--no-vad` (faster-whisper's own VAD) can filter out valid speech on already-cut short segments; leave VAD to the Silero layer |
| Prompt | `initial_prompt` should contain domain terms only (e.g. "Einstein EBO Mandarin") — never the full expected sentence, or it will hallucinate the prompt as recognition output |
| Audio ceiling | 8kHz telephone audio causes homophone errors and poor far-field recognition — not a script bug. Fixing it requires bypassing RTSP and using low-level Agora 16kHz PCM |
| Latency | Current flow is "finish speaking, then transcribe", ~1–2s delay. True streaming needs a streaming ASR engine (local whisper-streaming / faster-whisper-server, or a cloud streaming API) |

A control experiment recognized the target sentence with no prompt at all, which suggests the recognition came from a real voice rather than prompt hallucination.

## Wake Word Pitfalls (Learned the Hard Way)

The user said "MAX过来", but Whisper transcribed it as "马克斯过来" or "馬克思過來" (traditional characters), so literal `in` matching failed every time. Two fixes:

- `normalize_text()`: lowercase, strip spaces/punctuation, unify traditional → simplified (過→过, 來→来, 邁→迈, 麥→麦, 馬→马)
- `wake_aliases()`: generate 7 phonetic variants — `max / 麦克斯 / 马克思 / 迈克斯 / 马克斯 / 马斯 / 麦斯` + "过来"
- Match only the full "XX过来" combination — never treat bare `max` as an alias, or phrases like "this max value is large" will trigger false wake-ups
- Mixed traditional/simplified input (e.g. "过來") needs a single-character `來→来` replacement, or it won't match after normalization

Result: 2 successful wake-ups, normal `[WAKE]` log entries; background phrases ("但是过来", "那过来") did not trigger false positives. The default wake word is now "MAX过来" (originally "Einstein").

## Environment Issues

The RTSP audio track is the robot's microphone pickup, not its speaker output:

- Speech within 1 meter is captured clearly — measured RMS 1800–3600 vs ambient noise 300–600
- The robot's own TTS playback does not enter this track (the first 8 seconds should be TTS but transcribed empty) — speaker audio is echo-cancelled. Good: no self-interference. Bad: you cannot use RTSP to verify whether the robot is speaking

TV/video audio is the number-one killer: in the last two full tests, ASR captured only video audio (subtitles, soundtrack dialogue); none of the 22 transcripts contained the user's "MAX过来", so `question.json` was never generated. The successful wake-up earlier happened after the user turned the video off.

> Conclusion: before testing the full flow, turn off or fully mute nearby video and have the user speak within 1 meter of the robot. This is the only link not yet closed — and it has nothing to do with the code.

> Privacy note: microphone capture is involved — make sure everyone in the space is informed and consents before enabling it.

## Outstanding / TODO

- Full end-to-end conversation (wake → TTS → command ASR → Agent reply → TTS) not yet run successfully in a real environment; only individual modules verified. Retest in a quiet room
- No cloud streaming ASR or keyword spotting (KWS) integrated; wake-up currently relies on ASR text matching, which is noise-sensitive
- The earlier statement "EBO RTSP is basically video-only" is obsolete — do not quote it externally

## Notes for Anyone Picking This Up

1. Stop speculating about whether RTSP has audio — it does: `pcm_alaw`, 8kHz mono, measured
2. For speech recognition use the VAD script (`ebo_voice_agent.py`), not fixed-chunk transcription; model `small`, `condition_on_previous_text` off
3. For `av` errors check `av==15.0.0` first; for model download failures check `HF_ENDPOINT`; for curl certificate errors add `--ssl-no-revoke`
4. When driving the voice-assistant skill, launch in the background, poll the files, and read/write answer.json in the same conversation turn — never end the turn after launching
5. If the user reports "no success / no wake-up", check `voice_loop.log` `[asr]` and `[wake]` lines first: if ASR is all video audio it's an environment problem — ask the user to turn off the video and retry, don't change code

Log inspection commands:

```bash
grep -E '\[wake\]|\[tts\]|\[bridge\]' voice_loop.log
grep '\[asr\]' voice_loop.log | tail -15
ls -la bridge/
```

## Comparison with the Other Projects

| Dimension | Project 1: Morning Briefing | Project 2: Door Welcome | Project 3: Voice Assistant |
| --- | --- | --- | --- |
| Trigger | Scheduled (08:00 daily) | Event (door sensor) | Voice (wake word) |
| Orchestration | AI-driven | Standalone Python daemon | Script + Agent split |
| MCP channels | EBO HTTP | EBO HTTP + Mijia stdio | EBO HTTP + RTSP audio |
| Main difficulty | State verification polling | Stale state, dirty data | Audio quality, noise, environment |
| Maturity | Long-running in production | Stable at exhibitions | Modules verified; E2E pending quiet-environment retest |
