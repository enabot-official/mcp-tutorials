# Project 2: Smart Home Integration (Door Welcome)

> Connects an EBO robot to Mijia devices through two MCP channels: HTTP transport controls the robot, stdio transport integrates local devices. It also records how a long-running daemon handles stale state, dirty data, and imperfect hardware. Tested on the EBO MAX.

## Final Result

When a Xiaomi door/window sensor detects the door changing from closed to open:

1. The EBO robot automatically navigates to the living room
2. Visually detects a person (greets by name if a specific person is recognized)
3. Broadcasts a welcome message and turns on the Mijia light
4. Starts person following
5. Broadcasts and plays the user's favorite music
6. On program stop, auto-cleans the scene (stop music, stop following, turn off light)

## Design Principle

Pure Python standalone program + two MCP channels, no AI real-time orchestration — suitable for long-term stable operation in exhibition/demo scenarios.

This contrasts with Project 1 (scheduled automation + AI orchestration):
- Project 1 suits "once a day, complex logic, needs LLM judgment" scenarios
- Project 2 suits "event-triggered, 24/7 stable, fixed logic" scenarios

## Hardware List

| Device | Notes |
| --- | --- |
| EBO robot | Map built and navigation locations labeled |
| Xiaomi door/window sensor | Xiaomi Door and Window Sensor 3 |
| Mijia smart light | BLE Mesh device |
| Xiaomi hub gateway | Required for BLE Mesh sub-devices |

Network: the EBO robot and the machine running the script are on the same LAN. The Mijia hub communicates with sub-devices over BLE Mesh; its WiFi is only for upstream internet. The hub supports local automation, so scenes still run when offline.

## Two MCP Servers

### 1. EBO Robot MCP (HTTP / streamable HTTP)

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

> Get the token from the "MCP Interface Access" page in the app; one per robot. The endpoint is also shown there and is not published in this tutorial.
> Environment note: production and test endpoints differ, and their map data differs too — navigation location names must follow what `robot_list_locations` returns in the actual environment.

### 2. Mijia MCP (stdio transport)

```json
{
  "mcpServers": {
    "mijia": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--python", "3.11", "mijia.py"],
      "cwd": "<mijia MCP project directory>"
    }
  }
}
```

Uses the `mijiaAPI` library; first launch requires QR-code login, credentials are saved locally and the token auto-refreshes afterward.

## System Architecture

```
                    door_welcome.py  (standalone Python daemon)
                          |          |
            mijiaAPI (stdio)              EBO Robot MCP (HTTP)
            Mijia account / hub BLE Mesh   Bearer token
                          |                     |
                    +-----+-----+               |
                    |           |               |
                door sensor   light          EBO robot
                contact-state   on      navigate/speak/detect/follow/music
```

## Full Execution Flow (8 steps)

1. Door edge detection: main loop polls every 3 s; triggers only when previous `contact-state=True` (closed) and current `False` (opened), and >30 s since last trigger
2. Navigate to living room: `robot_navigate(locationName='Living Room')`, then poll `robot_status` for arrival (every 5 s, max 120 s)
3. Detect person: three-tier probe — first `robot_status`; none → wait 10 s and check again; still none → `robot_search_360(objId='1')`; still none → skip this whole segment
4. Welcome broadcast: name recognized → "[Name], welcome home, turning on the living room light for you"; person detected without a name → "Welcome home, turning on the living room light for you". Must finish speaking completely before the next step
5. Turn on light: `light.set('on', True)`, max 3 retries (2 s apart)
6. Start person following: `robot_follow(mode=0, trackTarget=4)`
7. Broadcast + play music: first speak "Playing your favorite music", then `robot_play_music(text='light music')`; music and following run in parallel
8. Cleanup on stop: `robot_music_control(controlType=4)` stop music + `robot_move(moveId=5)` full stop of following + turn off light. Use `try/finally` to cover all exit paths

### Person Name Tri-State Semantics

| `detect_person` return | Meaning | Handling |
| --- | --- | --- |
| `None` | No one at all | Skip the entire welcome flow |
| Name string | Specific person recognized | Broadcast named version |
| `''` (empty string) | Person detected but no name returned | Broadcast unnamed version |

> Note: don't use placeholders like "master".

## Core Implementation Points

### EboClient: MCP HTTP session wrapper

Use the official SDK's streamable HTTP client; `ClientSession` must be entered with `async with` to start its internal dispatcher, then call `initialize()`.

> Pitfall: SDK v2.3 doesn't accept `StreamableHTTPTransport(url, http_client)`; `ClientSession` can't be constructed and called directly; the tool schema attribute is `input_schema` (not `inputSchema`); the SDK uses httpx2 internally — don't pass `timeout`.

### TTS waiting (speak_and_wait)

In testing, `robot_speak` returning `OK` only means "message sent"; `robot_status` has no field reflecting playback state (device task is always "idle", music "stopped") and has ~20 s caching. So waiting must be estimated by character count:

```python
wait = max(2.0, len(text) / 4.0) + 1.5   # 4 chars/sec + buffer
await ebo.call('robot_speak', {'text': text, 'lang': 'en'})
await asyncio.sleep(wait)
```

`robot_search_360` is a blocking call. Navigation has a 120 s timeout fallback and continues the flow even on timeout.

### Person name parsing

The real device format:

```
Users currently detected in the camera view (...): DAVID {"leftTopX":0.382812, "leftTopY":0.1, ...}
当前检测到人数：1
```

Also handle parenthesized `David (0.42, 0.31)` and comma-separated multiple people. Parsing order is critical: strip coordinates first, then split on separators — otherwise commas inside the JSON coordinates cut the name apart.

```python
count = int(re.search(r'当前检测到人数[：:]\s*(\d+)', text).group(1))
m = re.search(r'Users currently detected[^\n]*?[：:]\s*(.+)', text)
val = m.group(1).strip()
name = re.sub(r'\s*\{.*?\}\s*', '', val)          # strip JSON coords
name = re.sub(r'\s*\(.*?\)\s*', '', name)         # strip paren coords
name = re.split(r'[,，;；]', name)[0].strip()       # take first person
```

### English name TTS normalization

The device returns all-caps `DAVID`, which Chinese TTS reads letter-by-letter as D-A-V-I-D. `robot_speak` has no pronunciation control, so convert to title case:

```python
def normalize_name_for_tts(name):
    if name and re.fullmatch(r"[A-Za-z][A-Za-z\s.'-]*", name):
        return name.title()   # DAVID -> David
    return name               # keep Chinese names as-is
```

### Mijia device interaction

```python
from mijiaAPI import mijiaAPI, mijiaDevice
api = mijiaAPI()
api.login()   # auto-refresh token or QR-code login
door = mijiaDevice(api, dev_name='<door sensor name>')
light = mijiaDevice(api, dev_name='<light name>')

state = door.get('contact-state')   # True=closed, False=opened
light.set('on', True)
```

### Stop and cleanup

Control the daemon with a flag file: create `door_welcome.run` with `running` at startup, delete it to exit on the next polling cycle; `__main__`'s `finally` removes it as a fallback. The cleanup function covers all exit paths.

## Dependencies and Environment

Python 3.11+ with uv, on Windows / macOS / Linux. These versions are the tested minimums:

```text
python-dotenv>=1.2.1
websockets>=15.0.1
mcp>=1.20.0
pydantic>=2.12.3
mcp-proxy>=0.10.0
fastmcp>=2.13.0.2
mijiaAPI>=3.0.0
```

`mcp` is the core EBO dependency; `mijiaAPI` is the core Mijia dependency. First use requires scanning a QR code to log in to Mijia; credentials are stored in `~/.config/mijia-api`. Inject the EBO token through the `EBO_TOKEN` environment variable.

## Companion Code

[`examples/02-smart-home/`](../../examples/02-smart-home/README.md) contains the complete runnable `door_welcome.py`, plus `requirements.txt` and run commands. Device names, navigation locations, speech text, and timeout/retry values are all in the config block at the top of the file.

## Known Issues

### Environment & config

- Token expiry: an old test-environment token returned `invalid or missing access key` (HTTP 401); switch to the production config
- Environment map differences: test env has "Doorway", production initially didn't. Hardcoded location names fail navigation. Call `robot_list_locations` after switching environments; names must be passed verbatim, never guessed

### Timing & protocol

- SDK API changes: use `streamable_http_client`; `ClientSession` must be `async with`; schema attribute is `input_schema`; don't pass `timeout`
- TTS return ≠ finished speaking: no playback-state feedback, status has 20 s caching, so polling status to detect completion doesn't work — estimate by character count
- Correct way to stop following: `robot_stop_patrol` can't stop AI following; use `robot_move(moveId=5)` for a full stop; music uses `robot_music_control(controlType=4)`
- Connection-close noise: short-lived test scripts occasionally throw anyio `cancel scope in a different task` on exit — judged a test-script lifecycle issue; the resident main program is unaffected

### Device & hardware

- Light intermittently offline: BLE Mesh delivery via hub occasionally returns an error code; the 3rd retry succeeded in testing, hence 3 retries. The log line "gateway received command, cannot determine whether set succeeded" is a normal notice, not a failure
- Sensor read jitter: occasional base64 decode failures; skip the round with try/except in the main loop — not a state-judgment error
- Scene residue: after welcoming, following/music/light persist; cleanup on exit is mandatory or the robot stays in follow+music state

### Data & text parsing

- Coordinates mixed into names: the real format is JSON coordinates, not parentheses; strip braces before splitting on commas, or the broadcast becomes garbled
- English names read letter-by-letter: all-caps strings treated as abbreviations by Chinese TTS; title-case conversion fixes it
- No-name branch can't use a placeholder: use tri-state semantics; broadcast the unnamed version when there's no name

## Key Config Parameters

| Variable | Default | Notes |
| --- | --- | --- |
| `EBO_URL` | `<EBO_MCP_ENDPOINT>` | Overridable via env var |
| `EBO_TOKEN` | read at runtime | Not hardcoded, overridable via env var |
| `DOOR_SENSOR` | sensor device name | Door/window sensor |
| `LIGHT_NAME` | light | Light name |
| `DOOR_LOCATION` | Living Room | Navigation target (must match map) |
| `GREETING_TPL` | `{name}, welcome home, turning on the living room light for you` | Named greeting |
| `GREETING_NO_NAME` | `Welcome home, turning on the living room light for you` | Unnamed greeting |
| `POLL_INTERVAL` / `COOLDOWN` | 3 / 30 | Poll interval / trigger cooldown (s) |
| `STATUS_POLL` / `NAV_TIMEOUT` | 5 / 120 | Nav status poll / timeout (s) |
| `LIGHT_RETRIES` / `LIGHT_RETRY_WAIT` | 3 / 2 | Light retries / interval |
| `TTS_CHARS_PER_SEC` / `TTS_MIN_WAIT` / `TTS_BUFFER` | 4.0 / 2.0 / 1.5 | TTS duration estimate |

## Run & Operations

```bash
# Run
cd <mijia MCP project directory>
uv run --python 3.11 door_welcome.py

# Stop: delete the door_welcome.run flag file (or Ctrl+C)
```

> Trigger note: if the door is already open when the program starts, close then open it (producing a True→False edge) to trigger.

Diagnostic scripts: `verify_setup.py` (read-only self-check), `smoke_test.py` (full-flow smoke test with injectable fake names for tri-state branches), `cleanup_test.py` (clean scene), `probe_ebo.py` (query status), `probe_tts.py` (probe status during TTS), `list_tools.py` (list all tools and parameter schemas).

Dependencies: python-dotenv, websockets, mcp>=1.20.0, pydantic, mcp-proxy, fastmcp, mijiaAPI>=3.0.0 (Python 3.11 + uv).

## Residual Risks

- `robot_status` has ~20 s server-side caching; navigation waiting lags, but the timeout fallback covers it
- Short-lived scripts occasionally emit anyio cancel-scope warnings on exit; the resident main program hasn't reproduced it
- The real person-name format has been confirmed by testing (JSON coordinates + all-caps); parsing and normalization logic validated with real text samples

> In one sentence: the difficulty isn't flow orchestration itself, but adapting to the imperfection of real hardware/protocols — environment differences, SDK changes, TTS timing, dirty data formats, intermittent offline, state residue. Every hardening was beaten out by real-device testing.
