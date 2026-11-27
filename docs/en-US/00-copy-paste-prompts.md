# Absolute beginner: copy one prompt, let the AI walk you through it

This page is for people who have never touched MCP. You don't need to understand the tech, and you don't even need to tell an "AI model" apart from an "AI Agent" — the first prompt below does that for you.

**The only skill you need is: open an AI assistant, paste text, and answer its questions.**

There are just three steps:

1. Open an AI assistant (this repo was tested with WorkBuddy — see [Which AI assistant](#which-ai-assistant))
2. Copy the **entire prompt** from one of the sections below (use the copy button at the top-right of the code block), paste it into the chat, and send
3. It will ask you questions one at a time and tell you what to do. Just answer and follow along

> These prompts do the work that normally means reading docs, editing config files, and memorizing tool names. You don't need to read those docs; if anything is missing, the AI will ask you instead of making you guess.

## Which AI assistant

| What you want to do | Which assistant works |
| --- | --- |
| Connect the robot, send commands, build the three projects | Most AI assistants work; this repo was tested with WorkBuddy |
| See live video and audio from the robot (RTSP) | **Must be an assistant running on your own computer** (e.g. WorkBuddy). A web/cloud assistant runs on someone else's server and can't reach your home Wi-Fi, so it cannot see the robot |

If you don't have one installed yet, start with WorkBuddy — everything in this repo was verified on it. The AI assistant will handle the "config file" and "check script" mentioned in the prompts; you don't need to touch them.

## 30-second primer: models, Agents, and MCP

Copy the whole block below to your AI assistant. It will explain everything in plain language:

```
Give me a 30-second intro course. I'm a complete beginner with no technical background, so:
- Use plain language only. Avoid abbreviations; if you must use one, explain it with an everyday example right away
- No more than three sentences per term
- After explaining, ask what I didn't understand, and if anything is unclear, explain it again with a better analogy

Explain these three things:
1. AI model (the "brain" behind AI like ChatGPT or Doubao)
2. AI Agent (the AI assistant I actually chat with and give instructions to)
3. MCP (a way for an AI assistant to operate real devices)

Finally, in one sentence, explain how these relate to "controlling my EBO robot at home just by talking".
```

## Prompt 1: Connect your robot

**What you need**: the token and endpoint from the "MCP Interface Access" page in the "Yibao Robot" app. That's all — nothing else.

Copy the whole block below to your AI assistant:

```
You are now my "EBO Robot Setup Guide". I'm a complete beginner, so follow three rules:
- Plain language only. No jargon; if you must use a term, explain it in one sentence
- Ask me one thing at a time, and wait for my answer before asking the next
- If any information is missing, ask me. Never guess, and never invent an endpoint or token

Your job is to connect my EBO robot and confirm it really works. Walk me through it in this order:

Step 1 · Get the token and endpoint
Tell me which page in the "Yibao Robot" app (called "MCP Interface Access") has the token and endpoint, and ask me to copy them and send them to you. The token is a string starting with ebo_mcp_.

Step 2 · Write the config
My AI assistant is WorkBuddy. Please write the connection info into ~/.workbuddy/mcp.json on this machine:
- Use ebo-robot as the server name
- Append /api/v1/mcp to the endpoint
- Put the token in the Authorization header as Bearer <token>
- If the file already has other MCP servers, add this one only — don't delete anything else
- Never print the token to screen, logs, or any reply

Step 3 · Actually verify
After writing it, do two things directly: list the currently available MCP tools, then call the read-only robot_status to see if the robot really responds.
- Tools list fine and robot_status returns data: tell me in plain language that it's connected and what I can now do
- Any failure: give me one concrete thing to check based on the failure type (network unreachable / bad token / tools not loaded / robot offline), one thing at a time
- If I already have this tutorial repo locally, you can also run examples/00-connection-check/check_connection.py for a fuller self-check

Confirm each step in one sentence before moving to the next. End with a three-sentence summary: what I did, what I can do now, and what to try next.
Start with Step 1 now.
```

## Prompt 2: See live video and audio

**What you need**: confirm your computer and the robot are on the same Wi-Fi, and turn on RTSP in the app to get the LAN address.

> This is the step people most often get stuck on: if you're using a web-based AI, it runs on someone else's server and can't reach your home Wi-Fi. Switch to a locally running assistant like WorkBuddy first.

Copy the whole block below to your AI assistant:

```
You are now my "EBO Audio/Video Guide". I'm a complete beginner — use plain language, ask me one thing at a time, ask when information is missing, and never guess an address or IP.

Your job is to let me see live video from my EBO robot and hear its audio in the AI assistant. Walk me through this in order:

Step 1 · Check where the AI assistant runs
Ask me: is the AI assistant I'm using installed on my own computer, or is it a web/mobile cloud service?
- If it runs on my computer (e.g. WorkBuddy), continue
- If it's a web-based cloud service, tell me clearly: a cloud service runs on someone else's server and cannot reach my home LAN, so it can't see the robot. I need to switch to a locally running assistant first

Step 2 · Same Wi-Fi
Ask whether the computer running the AI assistant and the EBO are on the same Wi-Fi. If not, tell me how to put them on the same network.

Step 3 · Get the RTSP address
Tell me where in the app to enable the RTSP / LAN video stream switch. Once on, it shows a LAN address like rtsp://<robot-IP>:554/main0. Ask me to send you that address.

Step 4 · Verify
Once you have the address, use a local tool (such as ffprobe) to confirm it connects and carries both video and audio tracks.
- If it works: tell me in plain language that I can now see and hear the robot, and show me the simplest way to watch/use it
- If it fails: give me one troubleshooting action at a time (not on the same Wi-Fi / RTSP switch off / wrong IP / blocked by firewall)

Important: the RTSP address contains my device's LAN IP, which is private information. Use and verify it only locally; never write it into a public page, logs, or send it to a third party.

Confirm each step in one sentence before moving on. Start with Step 1 now.
```

## Prompt 3: Build one of the three projects

**What you need**: nothing. Just decide which project you want. The AI assistant will ask you for anything else it needs.

Copy the whole block below to your AI assistant:

```
You are now my "EBO Project Guide". I'm a complete beginner — use plain language, ask me one thing at a time, ask whenever information is missing, and never guess or invent anything.

First ask me which of these three projects I want:
A. Morning briefing — the robot reads my schedule and wakes me up every morning
B. Door welcome — when someone enters, the robot goes over to greet them, turns on a light, and plays music
C. Voice assistant — let the robot hear me and respond (currently it can only hear and transcribe speech; a full voice loop is not working yet, so tell me that honestly)

Once I choose, walk me through the matching flow below step by step, confirming each step in one sentence before moving on. If any step needs information I haven't given (where the schedule comes from, location names, Mijia account, Wi-Fi details), ask me first — don't assume.

[A · Morning briefing]
1. Ask where my schedule lives (calendar app / spreadsheet / typed manually) and how to read it if needed
2. Ask which location in my home I want the announcement in (e.g. "living room"), and remind me this name must match the one in the app's map exactly
3. Have me send one simple command to confirm the robot understands (e.g. make it say something)
4. Guide me through this order: read schedule → confirm the location exists (robot_list_locations) → navigate there (robot_navigate) → confirm arrival with robot_status → read each item aloud (robot_speak)
5. Remind me: the robot doesn't report "done" after every step, so I must verify with robot_status before continuing; cap the wake-up loop at 10 rounds and return to the dock if no one is found
6. Ask if I want it to run on a daily schedule; if so, tell me how to set that up in WorkBuddy

[B · Door welcome]
1. First ask whether I have a Mijia account and a door/window sensor; if not, tell me what I need to prepare
2. Ask whether the robot and sensor are on the same LAN, and what the announcement location is called (must match the app's map)
3. Guide me to connect EBO and Mijia as two separate MCP servers
4. Trigger flow in order: door sensor changes → robot navigates to the door/living room and confirms with robot_status → detect person and greet by name if recognized → turn on the light → follow → play light music
5. Key warning: stopping a follow requires robot_move with moveId=5; robot_stop_patrol cannot stop it. On exit: stop music, full stop, turn off the light
6. Tell me honestly which parts require real hardware to test

[C · Voice assistant]
1. First get RTSP working (local assistant, same Wi-Fi, RTSP address) — you can have me use Prompt 2
2. Tell me what is actually verified so far: audio can be transcribed; the end-to-end voice loop is not working yet due to 8kHz audio quality and far-field noise
3. Guide me to run the scripts in examples/03-voice-assistant/; if I don't have those scripts, write them for me onto this machine, and prompt me to install any missing dependencies
4. Verify each step with real output, not just a command returning OK

End with a three-sentence summary: what I did, what works now, and what still needs work. Start by asking me to choose A / B / C.
```

## Prompt 4: When something goes wrong

**What you need**: describe the problem in your own words at the end of the prompt, then send it.

```
You are now my "EBO Troubleshooting Guide". I'm a complete beginner — use plain language and ask me one thing at a time.

I'll tell you what's happening. Go through the following in order: for each item, first tell me how to check it, then narrow things down based on my answer until we find the cause:
1. Does the config file exist, is the server name ebo-robot, and does the endpoint end with /api/v1/mcp
2. Can the network reach the endpoint
3. Is the token correct and unexpired (don't ask me to print the token)
4. Did the tool list load, and how many tools are there
5. Is the robot online, and what are its battery and current status
6. A specific action failed: navigation didn't arrive, no photo, follow won't stop, no speech, etc.

When you find a problem, give me one clear fix that does one thing at a time; after I fix it, I'll come back and continue. If all checks pass and it's still broken, tell me honestly and write up the symptoms as a short report I can send to official support.

Now tell me: what's happening?
```

## Know these before you start

- **A token is like a house key**: only give it to an AI assistant you trust, running on your own device. Don't paste it into unfamiliar websites or random AI services. The assistant should write it into your local config, not display it in the chat.
- **The robot actually moves**: navigation, following, and lights are real actions. Clear the area of people and fragile objects before you let it go.
- **Different assistants and models behave differently**: config entry points, phrasing, and whether it can edit local files all vary. The technical approach in these prompts is the same; if one assistant can't do it, switch to WorkBuddy or ask it to try another way.
- **"Command accepted" is not "action completed"**: good prompts make the AI verify with `robot_status`. Don't skip that.
- **Every project in this repo was tested on the EBO MAX**: MCP is currently available only on the EBO MAX and EBO Air2 Plus — see [Supported models](../../README_EN.md#supported-models).

## Go deeper

- [Quick start: your first command in 5 minutes](02-quickstart.md) — read this when you want to see the config details yourself
- [EBO MCP getting started](ebo-mcp-getting-started.md) — the full guide to tokens, config, commands, and FAQ
- [Prompt template collection](ebo-mcp-prompts.md) — prompts for commanding the robot once you're connected
- [Project 1: morning briefing](project-01-morning-briefing.md) · [Project 2: smart-home integration](project-02-smart-home.md) · [Project 3: voice assistant](project-03-voice-assistant.md)
