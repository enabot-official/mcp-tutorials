# Prompt Template Collection

Once MCP is configured, *how you ask* directly determines how well the robot performs. This collection has field-tested prompt templates you can copy directly or adapt.

> Core principle: **state the goal + emphasize verification + set boundaries**. The robot has no per-step completion report, so for complex tasks explicitly tell the AI to "verify with `robot_status` before continuing".

## 1. Simple single-step commands

No need for complex prompts in daily use — plain language works:

- "Check the robot's battery level and what it's doing."
- "Make the robot say: Welcome home!"
- "Take a photo of the current view for me."
- "Record a 10-second video."
- "Set the volume to 50."
- "Make the robot go back to charge."

## 2. Navigate + photo (sequential execution)

```
Go to the living room and check the current situation. Requirements:
1. First use robot_list_locations to confirm "Living Room" exists in the map; if not, tell me — don't guess
2. Navigate with robot_navigate, then use robot_status to confirm the task started/arrived
3. Only after confirmation, call robot_take_photo and send me the photo
4. Confirm each step completed before the next; don't issue commands back-to-back
```

## 3. Wake-up / person detection (bounded loop)

```
Go to the living room and loop a wake-up until a person is detected:
1. First robot_list_locations to confirm "Living Room" exists
2. Loop: robot_speak "Time to wake up", wait 25s, robot_status checks "people detected" and view
3. count>0 or a person in view → stop loop; otherwise repeat up to 10 rounds
4. Still no one after 10 rounds → don't continue, just return to dock and tell me "10 rounds, no one detected"
5. Verify with robot_status every round; don't judge by an OK return
```

## 4. Schedule broadcast (sequence + state verification)

```
Broadcast today's schedule for me:
1. Read today's schedule (all items, no filtering)
2. Confirm location with robot_list_locations, then navigate to the living room
3. robot_status to confirm navigation started
4. Broadcast item by item with robot_speak, format: "Item X, subject, at TIME"
5. Say a closing line when done
6. Verify each step with robot_status before continuing
Omit missing fields; never fabricate content.
```

## 5. Stop following (important)

Following is a special state that `robot_stop_patrol` can't stop. Say it explicitly:

```
Make the robot stop all movement. Use robot_move with moveId=5 (full stop),
not robot_stop_patrol (it can't stop AI follow).
After stopping, verify with robot_status that it has stopped.
```

## 6. Return to dock (correct order after following)

```
Make the robot return to the dock to charge. Order matters:
1. If following, first robot_stop_patrol to stop the follow task
2. Then robot_go_home(startUp=true)
3. Poll robot_status every 30s until charging at dock and task idle, max 6 times
4. At full battery the charging state may be unclear — tell me honestly, don't force a success verdict
```

## 7. Multiple robots with roles

```
The living-room EBO takes a photo in the living room; the bedroom EBO says "Time for bed".
Distinguish them by different server names in config and verify each robot's status separately.
```

## 8. Smart-home integration (cross-MCP)

```
When someone enters (door sensor state changes):
1. EBO navigates to the living room, verify with robot_status
2. Detect person — greet by name if recognized, otherwise generic welcome
3. Turn on the living room light (retry 3 times on failure)
4. robot_follow to start following
5. After broadcasting, robot_play_music for light music
6. On program exit: stop music (controlType=4) + full stop (moveId=5) + turn off light
```

---

## Four lessons for writing good prompts

1. **Confirm location before navigating**: nearly every real project starts with `robot_list_locations` to avoid guessing names
2. **Verify every step**: explicitly require the AI to confirm with `robot_status`, not to judge by an OK return
3. **Bound loops and waits**: wake-up 10 rounds, dock polling 6 times, navigation 120 s — prevent hangs
4. **Give failures an explicit fallback**: tell the AI "if no one is detected, skip the rest and dock directly" rather than retrying forever

These lessons come from real pitfalls in [both projects](project-01-morning-briefing.md); read them alongside the [Troubleshooting guide](ebo-mcp-troubleshooting.md).
