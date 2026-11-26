# EBO Robot Control Demo: From Natural Language to Action

This ties the earlier concepts together, showing how a natural-language instruction becomes a robot action, with safety notes and troubleshooting. For specific tool parameters see the [Tool Reference](ebo-mcp-tools-reference.md); for complete real projects see the [two projects](project-01-morning-briefing.md).

## What you'll learn

Understand the full chain "natural language → AI decision → tool call → physical action" and the key safety and failure-handling points.

## Scenario and safety notes

Scenario: say "go check the living room" and the AI navigates the robot to the living room and takes a photo for you.

Safety notes:

- The robot is a physical device; actions affect the real environment. Observe on-site during first tests
- The token effectively grants robot control — don't share it or post it publicly
- Redact home environments and faces in screenshots/videos before publishing (all images in this tutorial are processed)
- Don't leave follow modes running unattended; confirm the task is stopped before finishing

## Required interfaces and permissions

- EBO robot powered on, online, bound in the app, with a map built
- AI Agent configured with MCP (see [Quickstart](02-quickstart.md))
- 15 tools available (15/15 shown when connected)

## From instruction to action: what happens

For "go check the living room", the AI roughly decides:

1. Understand intent: user wants to go to the living room and look → needs "navigate" + "photo", in order
2. Confirm location: call `robot_list_locations` to get the exact name (avoid confusing "Living Room" and "Living Room 1")
3. Issue navigation: call `robot_navigate(locationName="Living Room")`
4. Verify navigation: call `robot_status` to see if the task started/arrived; no infinite waiting if unclear
5. Issue photo: after confirmation, call `robot_take_photo`
6. Return result: present the photo to the user

Note step 4 — this is the biggest difference between hardware control and pure software calls. Sent ≠ executed (see the sequential-execution chapter in [Troubleshooting](ebo-mcp-troubleshooting.md)).

## Correct pattern for sequential execution

The robot has no "per-step completion report" but has queryable state. When chaining actions:

1. Issue one action
2. Estimate execution time and wait (at least ~1 s between calls)
3. `robot_status` checks "device task" to confirm the previous step ended
4. Then issue the next step

Don't call at high frequency; leave margin for polling when the network jitters.

## Failure handling and on-site diagnosis

The robot currently has no active error reporting — failures show as "state didn't change" or "task stuck". Five steps:

1. Confirm connection: send a simple command (check battery) to see if it works
2. Confirm state: `robot_status` shows device task, battery, detected people count, location
3. Narrow down: split a complex command into single steps and find which one fails
4. Check the model's understanding: ask the AI to restate what it's about to do (especially location names)
5. Record symptoms: save the failing command, status snapshot, and actual robot behavior

### A typical pitfall: follow won't stop

`robot_stop_patrol` can't stop AI follow mode. To stop following, say "stop all actions" — corresponding to `robot_move(moveId=5)` (full stop). This pitfall was really hit in [both projects](project-01-morning-briefing.md).

## Next steps

Apply this chain to real projects:

- [Project 1: Morning Schedule Briefing](project-01-morning-briefing.md) — scheduled task + state polling + full pitfall library
- [Project 2: Smart Home Integration](project-02-smart-home.md) — dual MCP channels + resident program + imperfect-hardware adaptation
