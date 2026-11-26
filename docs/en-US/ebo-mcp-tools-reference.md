# EBO MCP Tool Reference

EBO robots expose a set of tools through MCP that AI Agents call to control the robot. This document lists all tools and their parameters for development, debugging, and troubleshooting.

> Note: The number of supported tools differs by model (EBO MAX / EBO Air2 Plus); EBO MAX supports the full set. This document assumes EBO MAX.
>
> Every tool has an optional `lang` parameter (BCP-47 language tag such as `zh-CN` or `en`) that controls the language of the robot's spoken confirmation. If omitted, the robot's configured language is used. This parameter is not repeated in the tables below.

## 1. Status and Map Queries

### `robot_status`

Query the robot's current status. This is the **most-used tool for sequential task execution** (see the polling section in [Troubleshooting and Best Practices](ebo-mcp-troubleshooting.md)).

No parameters. Returns:

- Battery level and charging state
- Device current time
- Device task (idle / navigating / patrolling / etc.) — the key field for determining whether the previous step finished
- Patrol routes and family members
- People detected in the camera view (name + coordinates in the visual frame)
- Music state, detected people count, location, screen brightness, IP address, WiFi signal, and volume

### `robot_list_locations`

List all navigable location names on the robot's built map.

No parameters. Returns the list of navigable places, or a notice if no map has been built yet.

> **Call this before `robot_navigate` whenever you are not certain of the exact location name.** The name must match the map exactly.

## 2. Movement and Navigation

### `robot_navigate`

Navigate along the built map to a specific location.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `locationName` | string | Yes | Exact target location; must be an existing waypoint or route name on the map |
| `findTarget` | string | No | Name of a target to visually search for after arrival; empty string means none |
| `objId` | string | No | Target to auto-detect after arrival: a family member's userId, `2`=cat, `3`=dog, `4`=generic pet; empty string means none |
| `needReturn` | boolean | No | Whether to return to the starting position before announcing the result; default `false` |

### `robot_patrol`

Start a whole-house patrol. Paths are injected automatically by the server from the map.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `duration` | integer | No | Patrol duration in seconds; `0` means no limit |
| `travelTimes` | integer | No | Number of loops; default decided by server/device |
| `objId` | string | No | Target to detect during patrol, same as `robot_navigate` |
| `targetName` | string | No | Name of the search target; empty string means none |

### `robot_move`

Perform a movement or skill action (forward, backward, turn, spin, figure-eight, snake, etc.).

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `moveId` | integer | Yes | Action type, see table below |
| `targetDistance` | number | No | For `moveId` 1/2: distance in meters (max 5); for 3/4: angle in degrees; otherwise 0 |
| `angleSpeed` | integer | No | Turning speed: `1`=default, `3`=small radius; default 1 |
| `playTime` | integer | No | Number of times to execute the action; default 1 |
| `voiceId` | integer | No | Sound effect id; `0` means none |

`moveId` values:

| Value | Action | Value | Action |
| --- | --- | --- | --- |
| 0 | No action | 8 | Circle |
| 1 | Move forward by distance | 9 | Backward skill |
| 2 | Move backward by distance | 10 | Snake wander |
| 3 | Turn left by angle | 11 | Zigzag |
| 4 | Turn right by angle | 12 | Spin |
| 5 | **Full stop** | 13 | Break free |
| 6 | Forward skill | 14 | Roam |
| 7 | Figure-eight | 15 | Sway |

> **`moveId=5` (full stop) is critical**: it is the only reliable way to stop AI follow mode. `robot_stop_patrol` cannot stop following (see [Troubleshooting](ebo-mcp-troubleshooting.md)).

### `robot_stop_patrol`

Immediately stop an ongoing patrol, cruise, or navigation task.

No parameters (except `lang`).

> Note: this tool **cannot** stop recharging / returning to dock (use `robot_go_home` with `startUp=false`), and **cannot** stop AI follow mode (use `robot_move` with `moveId=5`).

### `robot_go_home`

Send the robot back to the charging dock, or cancel the return.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `startUp` | boolean | No | `true` (default) = start returning and recharging; `false` = stop/cancel the return |

## 3. Follow and Search

### `robot_follow`

Start AI tracking so the robot follows a person or pet, or locks onto a target in view.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `mode` | integer | No | `0`=follow (keep following), `1`=lock (keep target in view) |
| `trackTarget` | integer | No | Target to track: `4`=person (default), `3`=pet |

> **Stop follow mode with `robot_move` using `moveId=5` (full stop)** — a pitfall found in real-world testing.

### `robot_search_360`

Rotate 360 degrees in place to search for a person or pet. **This call blocks** until the robot finishes and reports the result (or a short timeout).

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `objId` | string | No | Target: `1`=person, `2`=cat, `3`=dog, `4`=generic pet, or a family member's userId; empty string = general look-around |
| `angleSpeed` | integer | No | Rotation speed: `1`=default, `3`=slower and finer |

Returns the number detected and whether the requested target was found.

## 4. Voice and Music

### `robot_speak`

Make the robot announce text aloud via TTS.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `text` | string | Yes | Exact text to speak. Keep it short and natural; avoid personal pronouns |

### `robot_set_volume`

Adjust the speaker volume: set an exact level, or step up/down.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `direction` | integer | Yes | `0`=set exact level (also provide `volume`), `1`=increase one step, `2`=decrease one step |
| `volume` | integer | No | Target level 0–100; only used when `direction=0` |

### `robot_play_music`

Play music. Specify a song/artist/album, or a general category (e.g. "nursery rhymes", "light music").

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `song` | string | No | Song name |
| `singer` | string | No | Artist name |
| `album` | string | No | Album name |
| `text` | string | No | Category/style/scene description |

### `robot_music_control`

Control music that is already playing. To start new music, use `robot_play_music`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `controlType` | integer | Yes | `1`=replay, `2`=pause, `3`=resume, `4`=stop (clears queue), `5`=next, `6`=previous |

## 5. Capture

### `robot_take_photo`

Take a photo of the current view. No parameters (except `lang`).

### `robot_record_video`

Record a video clip.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `recordSeconds` | integer | No | Duration in seconds; default 10 |

## 6. Calling Conventions

- **Call interval**: do not call tools at high frequency back-to-back; leave roughly one second or more between calls (see [Troubleshooting](ebo-mcp-troubleshooting.md)).
- **Sequential execution**: the robot does not report "step completed" for each action. To chain actions, call `robot_status` after each step and poll the "device task" field until the previous step is finished before issuing the next one.
- **Error feedback**: the robot currently has no active error reporting. Failures usually show up as "state didn't change" or "task stuck", so diagnose via status queries and on-site observation.
