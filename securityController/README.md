# Ring Security Controller

Playwright-based service that arms/disarms Ring Alarm via HTTP API.

## Setup

1. Copy `.env.example` to `.env` and fill in Ring credentials.
2. Install dependencies: `npm install`
3. Build: `npm run build`
4. Start: `npm run start`

Or from the repo root: `./run.sh`

## Twilio OTP (optional)

When Ring requires a one-time code at login, the server can text your phone and wait for your reply instead of prompting on stdin.

### Twilio account setup

1. Create a [Twilio account](https://www.twilio.com/try-twilio) (trial credit available).
2. Buy a US local phone number (~$1.15/month).
3. On trial accounts, [verify your personal cell number](https://www.twilio.com/docs/messaging/guides/how-to-use-your-free-trial-account) so it can receive texts.
4. Complete [10DLC registration](https://www.twilio.com/docs/messaging/compliance/a2p-10dlc) (brand + low-volume campaign) for US SMS on long codes.
5. Add credentials to `.env`:

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...   # your Twilio number
OTP_PHONE_NUMBER=+1...      # your personal cell (E.164)
```

Optional tuning:

```
OTP_POLL_INTERVAL_MS=2000   # how often to check for SMS reply
OTP_TIMEOUT_MS=300000         # max wait for reply (5 min default)
```

### How it works

1. Login reaches the one-time code screen.
2. Server sends SMS: *"Ring login needs your one-time code. Reply with the 6-digit code."*
3. Server polls the Twilio Messages API for an inbound reply from `OTP_PHONE_NUMBER`.
4. Playwright fills the code and completes login.
5. Fresh cookies are saved to `session.json`.

If Twilio env vars are missing, login falls back to stdin prompt.

### Cost (approximate)

| Item | Cost |
|------|------|
| Phone number | ~$1.15/month |
| Per OTP exchange (out + in) | ~$0.02–0.03 |
| 10DLC campaign | ~$1.50–10/month |

OTP is only needed when `session.json` expires, not on every arm/disarm.

### Testing OTP flow

Use `--force-test-otp` to skip loading `session.json` without deleting it:

```bash
./run.sh --force-test-otp
```

This starts Chromium with a fresh context, forces the login flow, and refreshes `session.json` after success. If login fails, restart without the flag to use the previous session.

Reply to the Twilio text with a 6-digit code (e.g. `123456`).

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/arm-security-away` | Arm away mode |
| POST | `/disarm-security` | Disarm |
| POST | `/arm-security-home` | Arm home mode |
| POST | `/restart-browser` | Restart Playwright browser |

All endpoints return JSON: `{ "success": true|false, "message": "..." }`.

## CLI flags

| Flag | Description |
|------|-------------|
| `--force-test-otp` | Skip loading `session.json` on startup (test login/OTP) |

Pass via `./run.sh --force-test-otp` or `npm run start -- --force-test-otp`.
