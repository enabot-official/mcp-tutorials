# EBO MCP Troubleshooting and Best Practices

This guide covers common pitfalls when configuring and using EBO MCP, and how to diagnose them. For the basics, see the [EBO Robot MCP Getting Started](ebo-mcp-getting-started.md).

## 1. Configuration

### 1.1 Invalid JSON

The config file must be valid JSON. The three most common mistakes:

- **Full-width punctuation**: quotes, commas, and colons must be half-width ASCII. Chinese quotes `“ ”` will break parsing.
- **Extra or missing commas**: no comma after the last field; commas required between fields.
- **Unreplaced placeholders**: `<YOUR_TOKEN>` and `<EBO_MAX_MCP_ENDPOINT>` are placeholders — replace them with your own values.

Validate the JSON with any JSON checker before launching the client.

### 1.2 Endpoint substitution

The endpoints in the tutorial are placeholders. When replacing them:

- Keep the `/api/v1/mcp` path — don't use the bare domain only
- If the address from the app/support already includes a path, don't append it twice
- EBO MAX and Air2 Plus use different endpoints — don't mix them up

### 1.3 Restart is required

After saving the config, **fully quit and restart** the AI client. Refreshing the window or minimizing/restoring usually does not apply the change.

## 2. Connection

### 2.1 Can't connect to the robot

Check in order:

1. Token expired (one month) — renew it in the app
2. Token was regenerated — all old tokens become invalid
3. Robot is powered on, online, and bound in the app
4. AI client was restarted
5. The endpoint matches the correct model

### 2.2 Token safety

- The token effectively grants control of your robot. Don't paste it into public repos, chats, or screenshots.
- If you suspect a leak, tap **Regenerate** in the app to invalidate the old token
- Use a separate token per robot so they can be managed and revoked independently

## 3. Usage

### 3.1 Navigation fails: "location not found"

- Build a map in the app and name the locations first
- Use the **exact name** from the map in your command (if the map says "living room", don't say "the sitting room")
- Keep location names short, unique, and unambiguous

### 3.2 Running multiple actions in order

A common use case, but note:

- **One command at a time**: don't cram all actions into a single sentence; issue them one by one and confirm each
- **Wait for the previous step**: make sure the last action finished before sending the next command
- **Be specific**: state the target, location, and action clearly — avoid vague phrasing like "do something"
- **Stop on failure**: if a step fails, diagnose it before piling on more commands, otherwise the state is hard to trace

### 3.3 On-site diagnosis when an action fails

Locate the problem in this order rather than blindly retrying:

1. Confirm connection: send a simple command (e.g. check battery) to see if it works
2. Confirm state: what is the robot doing now, is the battery sufficient, is it stuck
3. Narrow down: split a complex command into single steps and find which one fails
4. Check the model's understanding: ask the AI to restate what it's about to do
5. Record the symptoms: save the failing command, error message, and robot state for review

> The above is general guidance. The meaning of specific errors and tool return structures need to be added based on the actual MCP capabilities (see "To be added" below).

### 3.4 Stopping follow mode

"Stop patrol" cannot end follow mode. Follow is a special state — say "stop all actions" or "make the robot stop".

### 3.5 Multiple robots

Each robot has its own token and endpoint. Use different server names in the config (e.g. `ebo`, `ebo-plus`) and specify which robot you mean in the command.

### 3.6 Audio/video limits

MCP currently only supports making the robot "speak" (text-to-speech); it does not stream microphone audio in real time. For two-way communication, use RTSP LAN video streaming.

## 4. To be added (requires actual MCP details)

The following cannot be written without knowing the real MCP implementation:

- The list of available tools and their parameters
- Specific error codes and return messages
- Whether multi-step sequential actions require waiting for a completion signal from each step
- Actual behavior of concurrent control and multi-robot control
- Rate limits or quotas
