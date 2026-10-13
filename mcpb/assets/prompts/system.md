# telephony-mcp — MCP Server Capabilities

**Server:** Telephony Bridge v0.2.0
**Description:** FastMCP 3.2 Telephony Bridge for outbound phone calls and SMS via Asterisk/ARI (with speechops TTS) or Twilio. Includes a JSON-backed contact store, SQLite audit database, and MCP Bridge federation support. Eight MCP tools covering the full telephony lifecycle: contact management, call origination, SMS messaging, dispatch testing, and status monitoring.

---

## Architecture Overview

telephony-mcp provides two operational modes selected via `TELEPHONY_PROVIDER`.

### Asterisk Mode (Default)

Uses the Asterisk REST Interface (ARI) for the complete outbound call lifecycle. The `AsteriskProvider` class orchestrates five stages:

1. **Audio Synthesis (`audio.py`):** The `synthesize_wav()` function sends the message text to the speechops REST API at `{SPEECHOPS_BASE_URL}/api/v1/tts/wav` with provider and voice parameters. The returned WAV bytes are written to the `TELEPHONY_AUDIO_SHARE` directory. If speechops is unreachable (after `SPEECHOPS_TIMEOUT_S` seconds), a pre-recorded fallback WAV from `audio/fallback/{script_type}.wav` is used. If no fallback exists, the call connects silently with no audio.

2. **ARI Origination (`ari_client.py`):** The `ARIClient` class opens an authenticated HTTP session with the ARI server. It POSTs to `{ari_url}/channels` with `endpoint`, `app`, and `callerId` to originate the call through the configured PJSIP endpoint. The endpoint string is built by `_build_endpoint()` — E.164 numbers use `PJSIP/{endpoint}/sip:{number}` while SIP URIs use `PJSIP/{uri}` directly.

3. **Answer Detection:** After origination, the client opens an ARI events WebSocket (`ws://{ari_url}/events?app={app}&api_key={user}:{pass}`) and waits for a `StasisStart` event matching the channel ID. The wait is bounded by `ARI_ANSWER_TIMEOUT_S` (default 30s). If the channel is destroyed before answer, the call is marked as failed.

4. **Playback:** Once answered, the channel is answered via POST to `{ari_url}/channels/{id}/answer`. A playback is started via POST to `{ari_url}/channels/{id}/play` with `media: "sound:telephony_tts/{filename}"`. The tool polls `{ari_url}/playbacks/{id}` until state is `"done"` or returns 404, or until `ARI_PLAYBACK_TIMEOUT_S` (default 60s).

5. **Hangup:** The channel is deleted via DELETE to `{ari_url}/channels/{id}`.

### Twilio Mode

Uses the Twilio REST API. The `TwilioProvider` class:
- For voice: constructs TwiML with `<Say language="de-AT" voice="Polly.Marlene-Neural">{message}</Say>` and calls `client.calls.create()`.
- For SMS: calls `client.messages.create()` with body and recipient.
- Falls back to mock mode (synthetic IDs with `mode: "mock"`) if credentials are missing.

### Contact Store (`contacts.py`)

A JSON file at `data/contacts.json` (configurable via `TELEPHONY_CONTACTS_PATH`). Key features:
- **E.164 validation:** Numbers must match `^\+[1-9]\d{6,14}$`.
- **Case-insensitive lookup:** Names are stored lowercased. Supports exact match and partial substring match.
- **Raw number passthrough:** E.164 strings are returned as-is with the number as display name.
- **Auto-creation:** The file is created on first `add_contact` call.

### Audit Database (`db.py`)

A SQLite database at `data/calls.db` (configurable via `TELEPHONY_DB_PATH`). Table `calls`:
- Columns: `id`, `ts` (ISO-8601 UTC), `op` (make_call, send_sms, dispatch_test), `contact_name`, `to_number`, `message`, `script_type`, `provider`, `success`, `call_id`, `error`, `audio_played`, `duration_ms`.
- Auto-migration adds `contact_name` column if missing from legacy DBs.
- Indexed by `ts DESC` for fast recent-call queries.
- Provides `get_stats()`, `get_calls()` (paginated, filterable), `get_call()` by ID.

### MCP Bridge Federation

`MCP_BRIDGE_URLS` accepts a comma-separated list of remote MCP server URLs. Each is registered as a `ProxyProvider` via FastMCP's `create_proxy()`, enabling cross-server tool routing through telephony-mcp.

---

## Tool Reference

### 1. make_call

**Purpose:** Place an outbound phone call and speak a message via TTS. Accepts a contact name or raw E.164 number.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `contact` | `str` | Yes | — | Contact name or E.164 number (+43664...). |
| `message` | `str` | Yes | — | Text to speak. German/English supported. |
| `script_type` | `str` | No | `"general"` | Audio cache & fallback key: `"general"`, `"emergency"`, `"test"`. |
| `ctx` | `Context` | Auto | — | Injected by FastMCP. |

**Return Format (Asterisk):**
```json
{"success": true, "call_id": "1532467890.42", "audio_played": true, "mode": "asterisk", "contact_name": "Steve", "to_number": "+436641234567"}
```

**Return Format (Twilio):**
```json
{"success": true, "call_id": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "mode": "twilio", "contact_name": "Marion", "to_number": "+436649876543"}
```

**Error (contact not found):** `{"success": false, "error": "Contact 'Nobody' not found. Add via add_contact or use E.164."}`

### 2. make_emergency_call

**Purpose:** Emergency call wrapper. Calls `make_call` with `script_type="emergency"`.

**Parameters:** `to_number` (str), `message` (str), `ctx` (auto).

**Return:** Same format as `make_call`.

### 3. send_sms

**Purpose:** Send SMS to a contact or E.164 number. Requires Twilio provider.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `contact` | `str` | Yes | — | Contact name or E.164 number. |
| `text` | `str` | Yes | — | SMS body text. |
| `ctx` | `Context` | Auto | — | Injected by FastMCP. |

**Return (Twilio):** `{"success": true, "sms_id": "SMxxxxxxxxxxxxx", "mode": "twilio", "contact_name": "Steve", "to_number": "+436641234567"}`

**Return (Asterisk):** `{"success": false, "error": "SIP SMS is trunk-dependent and not implemented. Set TELEPHONY_PROVIDER=twilio for SMS support."}`

### 4. telephony_dispatch_test

**Purpose:** Dry-run test call to a SIP URI with a fixed German test message: "Achtung. Dies ist ein Test der RoboFang Rettungskette. Bitte bestaetigen Sie den Empfang."

**Parameters:** `sip_uri` (str, e.g. `"sip:linphone@localhost"`), `ctx` (auto).

**Return:** `{"success": true, "call_id": "1532467890.43", "audio_played": true, "mode": "asterisk"}`

### 5. add_contact

**Purpose:** Add or update a contact. Number must be E.164.

**Parameters:** `name` (str), `number` (str, E.164 format), `notes` (str, default ""), `ctx` (auto).

**Return (success):** `{"success": true, "contact": {"name": "Steve", "number": "+436641234567", "notes": "Emergency"}}`

**Return (invalid):** `{"success": false, "error": "Number must be E.164 format (+43...), got: 0664..."}`

### 6. list_contacts

**Purpose:** List all contacts.

**Parameters:** `ctx` (auto).

**Return:** `{"contacts": [{"name": "Steve", "number": "+436641234567", "notes": ""}], "count": 1}`

### 7. remove_contact

**Purpose:** Remove a contact by name.

**Parameters:** `name` (str, case-insensitive), `ctx` (auto).

**Return (found):** `{"success": true, "removed": "Steve"}`

**Return (not found):** `{"success": false, "error": "Contact 'Steve' not found"}`

### 8. telephony_status

**Purpose:** Return provider readiness and call statistics.

**Parameters:** `ctx` (auto).

**Return (Asterisk):**
```json
{
  "provider": "asterisk",
  "ready": true,
  "config": {"ASTERISK_ARI_URL": "http://localhost:8088/ari", "ASTERISK_ARI_USER": "robofang", "ASTERISK_ARI_PASS": "set", "SPEECHOPS_BASE_URL": "http://localhost:10918"},
  "stats": {"total_calls": 42, "successful": 38, "failed": 4, "last_call": null},
  "contact_count": 3
}
```

**Return (Twilio incomplete):**
```json
{
  "provider": "twilio",
  "ready": false,
  "config": {"TWILIO_ACCOUNT_SID": "set", "TWILIO_AUTH_TOKEN": "missing", "TWILIO_FROM_NUMBER": "missing"},
  "stats": {"total_calls": 0, "successful": 0, "failed": 0, "last_call": null},
  "contact_count": 0
}
```

---

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `TELEPHONY_PROVIDER` | `"asterisk"` | No | `"asterisk"` or `"twilio"` |
| `ASTERISK_ARI_URL` | `"http://localhost:8088/ari"` | No | ARI base URL |
| `ASTERISK_ARI_USER` | `"robofang"` | No | ARI username |
| `ASTERISK_ARI_PASS` | `"robofang_pass"` | No | ARI password |
| `ARI_ANSWER_TIMEOUT_S` | `"30"` | No | Call answer timeout (seconds) |
| `ARI_PLAYBACK_TIMEOUT_S` | `"60"` | No | Audio playback timeout (seconds) |
| `SPEECHOPS_BASE_URL` | `"http://localhost:10918"` | No | TTS service URL |
| `SPEECHOPS_TTS_PROVIDER` | `"gemini"` | No | TTS provider |
| `SPEECHOPS_TTS_VOICE` | `"Kore"` | No | Voice ID |
| `TWILIO_ACCOUNT_SID` | — | For Twilio | Twilio SID |
| `TWILIO_AUTH_TOKEN` | — | For Twilio | Twilio token |
| `TWILIO_FROM_NUMBER` | — | For Twilio | Originating E.164 |
| `TELEPHONY_DB_PATH` | `./data/calls.db` | No | Audit DB path |
| `TELEPHONY_CONTACTS_PATH` | `./data/contacts.json` | No | Contacts path |
| `TELEPHONY_AUDIO_SHARE` | `./audio/tts` | No | TTS WAV output dir |

## Complete Tool Specification

### make_call Deep Dive

The `make_call` tool is the primary voice call interface. It accepts a `contact` parameter that can be either a name from the contact store or a raw E.164 phone number. The contact resolution logic in `contacts.py` first checks if the input matches the E.164 regex pattern `^\+[1-9]\d{6,14}$`. If matched, the number is used directly with itself as the display name. If not matched, the store is queried by lowercased exact match first, then by partial substring match on name. If no match is found, the tool returns an error suggesting the caller add the contact or use E.164 format.

The `message` parameter is the text to be synthesized as speech. In Asterisk mode, this text is sent to the speechops service at `{SPEECHOPS_BASE_URL}/api/v1/tts/wav` with query parameters `text`, `provider` (default `"gemini"`), and `voice_id` (default `"Kore"`). The speechops service returns raw WAV bytes on success. These bytes are written to `{TELEPHONY_AUDIO_SHARE}/{script_type}.wav`. The filename is sanitized to contain only alphanumeric characters and underscores to prevent Asterisk filename parsing issues. In Twilio mode, the message is embedded in TwiML: `<Response><Say language="de-AT" voice="Polly.Marlene-Neural">{message}</Say></Response>`. The Twilio API then calls the recipient and plays the synthesized speech.

The `script_type` parameter influences two things: the fallback WAV selection and the cache key for synthesized audio. Available values are `"general"`, `"emergency"`, and `"test"`. Each value maps to a pre-recorded fallback WAV at `audio/fallback/{script_type}.wav`. These fallbacks are used when the speechops TTS service is unreachable. If both speechops and the fallback are unavailable, the call connects silently — the recipient hears a ring, answer, then silence for a few seconds, then hangup. The `script_type` is logged in the audit database for post-call analysis.

The `ctx` parameter is automatically injected by FastMCP's Context injection system. It provides `ctx.info()` for logging, `ctx.report_progress()` for task progress tracking, and access to the connected client's sampling capabilities. The tool calls `ctx.info()` before and after the call to provide real-time status to the MCP client.

### make_emergency_call Complete Specification

`make_emergency_call` is a backward-compatible wrapper that delegates to `make_call` with `script_type` forced to `"emergency"`. This ensures emergency calls use the emergency fallback WAV and are clearly marked in the audit log. The `to_number` parameter is an alias for `contact` in the underlying call. Emergency calls receive priority handling in the audit log and have a distinct `op` code for filtering.

### send_sms Complete Specification

The `send_sms` tool sends a text message to a contact or E.164 number. In Twilio mode, the tool calls `client.messages.create()` with `body`, `from_` (the Twilio originating number), and `to` (the resolved recipient number). The Twilio API returns a message SID which is logged as `sms_id` in the response and audit database. In Twilio mock mode (when credentials are missing), the tool returns `{"success": true, "sms_id": "MOCK_TWILIO_SMS", "mode": "mock"}`. In Asterisk mode, SMS is not supported because SIP MESSAGE (SMS over SIP) is trunk-dependent and most Austrian SIP trunks do not implement it. The Asterisk provider returns a descriptive error with a clear recommendation to switch to Twilio. The SMS body text is limited only by the Twilio API's 1600-character limit for concatenated messages.

### telephony_dispatch_test Complete Specification

The `telephony_dispatch_test` tool sends a fixed German test message to a local SIP URI. The message is: "Achtung. Dies ist ein Test der RoboFang Rettungskette. Bitte bestaetigen Sie den Empfang." This message is hardcoded in the server source and cannot be customized. The `sip_uri` parameter should be a full SIP URI like `"sip:linphone@localhost"` or `"sip:testphone@192.168.1.100"`. The tool calls `make_call` internally with `script_type="test"`. The call is logged with `op="dispatch_test"` in the audit database. This is the recommended first test after configuring Asterisk and ARI, as it does not require a real SIP trunk — just a local SIP client on the same network.

### Contact Management Tools Complete Specification

The `add_contact` tool validates the phone number against the E.164 regex before saving. If validation fails, the tool returns an error with the invalid input included for debugging. On success, the contact is merged into the contacts dict (lowercased key) and the file is written atomically using `Path.write_text()`. Concurrent writes are not protected — only one MCP session should manage contacts at a time.

The `list_contacts` tool reads the entire contacts file and returns all entries as an array. The `count` field is derived from the array length. If the contacts file does not exist (no contacts added yet), the tool returns an empty array.

The `remove_contact` tool looks up the name in the contacts dict by lowercased key. If found, the entry is deleted and the file is saved. If not found, an error is returned. The lookup is case-insensitive, so "Steve", "steve", and "STEVE" all match.

### telephony_status Complete Specification

The `telephony_status` tool checks provider readiness by inspecting environment variables. In Asterisk mode, the provider is always considered ready (`ready: true`) because there is no reliable way to probe ARI availability without making a test call. The config section shows the ARI URL and username but redacts the password. In Twilio mode, readiness requires all three Twilio env vars to be present and non-empty. The config section shows which variables are set and which are missing. The stats section queries the SQLite audit database for total calls, successful calls, failed calls, and the most recent call record. The contact count is derived from `list_contacts()`.

### Audio Synthesis Pipeline

The audio synthesis in `audio.py` follows a two-tier strategy:
1. **Primary: speechops REST API.** The tool sends a GET request to `{SPEECHOPS_BASE}/api/v1/tts/wav` with `text`, `provider`, and `voice_id` query parameters. The request has a configurable timeout (`SPEECHOPS_TIMEOUT_S`, default 10s). On HTTP 200, the response body (WAV bytes) is written to `{TELEPHONY_AUDIO_SHARE}/{safe_type}.wav`.
2. **Fallback: pre-recorded WAV.** If speechops returns non-200 or the request times out or raises a connection error, the fallback WAV at `audio/fallback/{safe_type}.wav` is copied to the audio share directory.
3. **Silent call:** If both speechops and fallback are unavailable, the function returns `None` and the call proceeds without audio.

### ARI Call Lifecycle

The `ARIClient` class manages the complete ARI call lifecycle:
1. HTTP session creation with basic auth credentials
2. Channel origination via POST to `/channels` with `endpoint`, `app`, and `callerId`
3. WebSocket connection to `/events?app={app}&api_key={user}:{pass}` for real-time event monitoring
4. StasisStart event matching on channel ID
5. Channel answer via POST to `/channels/{id}/answer`
6. Playback via POST to `/channels/{id}/play` with `media: "sound:telephony_tts/{filename}"`
7. Playback completion polling via GET `/playbacks/{id}` (checks for 404 or state "done")
8. Channel hangup via DELETE `/channels/{id}`
9. HTTP session cleanup

The entire lifecycle runs within an `async with ARIClient(...)` context manager that ensures proper cleanup even on errors.

### Environment Variable - Detailed Configuration

The `TELEPHONY_PROVIDER` variable accepts `"asterisk"` (lowercase) or `"twilio"` (lowercase). The value is read in `get_provider()` which instantiates the appropriate provider class. All Asterisk-related env vars are read in `AsteriskProvider.__init__()` and `audio.py`. All Twilio-related env vars are read in `TwilioProvider.__init__()`. The `MCP_BRIDGE_URLS` variable is read at module import time in `server.py` and will not reflect changes until the server is restarted.

### Audit Database Schema

The `calls` table schema:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `ts`: TEXT NOT NULL (ISO-8601 UTC timestamp)
- `op`: TEXT NOT NULL (one of: `"make_call"`, `"send_sms"`, `"dispatch_test"`)
- `contact_name`: TEXT (nullable, the resolved display name)
- `to_number`: TEXT NOT NULL (the dialed E.164 number or SIP URI)
- `message`: TEXT NOT NULL (the spoken message or SMS body)
- `script_type`: TEXT NOT NULL DEFAULT `"general"` (one of: `"general"`, `"emergency"`, `"test"`, `"sms"`)
- `provider`: TEXT NOT NULL (one of: `"asterisk"`, `"twilio"`, `"mock"`)
- `success`: INTEGER NOT NULL (boolean: 1 for success, 0 for failure)
- `call_id`: TEXT (nullable, provider-specific call/SMS identifier)
- `error`: TEXT (nullable, error message on failure)
- `audio_played`: INTEGER NOT NULL DEFAULT 0 (boolean: 1 if audio was played)
- `duration_ms`: INTEGER NOT NULL DEFAULT 0 (wall-clock duration of the operation)

### Contact Storage Detailed Format

The contact store JSON file has this structure:
```json
{
  "steve": {"name": "Steve", "number": "+436649876543", "notes": "Brother"},
  "marion": {"name": "Marion", "number": "+436641234567", "notes": "Sister"},
  "+436644556677": {"name": "+436644556677", "number": "+436644556677", "notes": ""}
}
```

Keys are lowercased names. Values contain the original name (preserving capitalization), the validated E.164 number, and optional notes. When resolving, the tool first checks for exact key match, then falls back to partial substring matching on both the key and the stored name.

## Error Recovery in Detail

### Contact Resolution Errors
When `make_call` or `send_sms` receive a contact string that is neither a valid E.164 number nor a known contact name, they return `{ "success": false, "error": "Contact '{input}' not found. Add via add_contact or use E.164." }`. The error response includes the exact input string to help the caller identify the problem. Recovery steps: (1) check the spelling of the contact name, (2) run list_contacts to verify the contact exists, (3) use a raw E.164 number as a temporary workaround, (4) add the missing contact with add_contact.

### ARI Pipeline Errors
ARI errors can occur at any stage of the call lifecycle:
- **Origination fails** (HTTP non-200/201 from POST /channels): The ARI server rejected the request. Common causes: invalid endpoint string, ARI user lacks permissions, Asterisk is not running. The error includes the HTTP status code and response body for diagnosis.
- **StasisStart timeout** (no event within ANSWER_TIMEOUT_S): The call was originated but the callee did not answer. The channel is cleaned up automatically. Recovery: check the phone number, increase the answer timeout, or verify the SIP trunk is functional.
- **Playback fails** (HTTP non-200/201 from POST /channels/{id}/play): The sound file was not found in the Asterisk sounds directory. Recovery: verify the audio share directory is mounted correctly and the WAV file exists.
- **Playback timeout** (no completion within PLAYBACK_TIMEOUT_S): The audio message was too long or the channel dropped. Recovery: check the message length, increase the playback timeout.

### Twilio API Errors
Twilio errors return the Twilio exception message directly. Common Twilio error codes:
- 21211: Invalid 'To' phone number. Recovery: verify E.164 format.
- 21214: 'To' phone number is not a valid number. Recovery: check country code and digit count.
- 21408: Permission to send an SMS has not been enabled for the region. Recovery: enable SMS in Twilio console.
- 21608: The 'From' phone number is not a valid number or is not owned by your account. Recovery: verify TWILIO_FROM_NUMBER.

## E.164 Number Validation

The E.164 regex `^\+[1-9]\d{6,14}$` accepts:
- A leading `+` character (required)
- A country code digit (1-9, not 0)
- 6 to 14 additional digits
- Total: 8-15 digits including the country code

Examples of valid numbers: `+436641234567` (Austria mobile), `+49123456789` (Germany), `+447911123456` (UK).
Examples of invalid numbers: `06641234567` (missing +), `+06641234567` (0 after +), `+12345` (too short), `+1234567890123456` (too long).

## Integration with speechops-mcp

The speechops service is a separate MCP server (`speechops-mcp`) that provides TTS (text-to-speech) synthesis. It supports multiple backends: Google Gemini (primary, with the "Kore" voice), Windows SAPI5 (local, no API key needed), and ElevenLabs. The REST endpoint at `/api/v1/tts/wav` accepts query parameters for text, provider, and voice_id, and returns raw WAV audio bytes suitable for Asterisk playback. The audio share directory must be accessible to both telephony-mcp (for writing) and the Asterisk container (for reading via the mounted volume).

## Security & Privacy

- Credentials are redacted in `telephony_status` output (shown as `"set"` or `"missing"`).
- Contact store and audit DB are local files — no external sync.
- ARI uses HTTP basic auth (HTTPS recommended for production).
- Twilio uses HTTPS for all API calls.
- Passwords and tokens are never logged.
## Detailed Asterisk ARI Integration

Asterisk REST Interface (ARI) provides a RESTful API for controlling Asterisk PBX. telephony-mcp uses ARI version 2.x (compatible with Asterisk 16+). The ARI module must be enabled in Asterisk configuration. The connection uses HTTP Basic Authentication. For production deployments, configure ARI to use HTTPS and strong passwords.

### ARI Configuration Requirements

In ri.conf:
`
[general]
enabled = yes
; Bind to localhost only for security
bindaddr = 127.0.0.1

[robofang]
type = user
read_only = no
password = your_secure_password
; Optionally restrict to specific IP ranges
; permitted_ips = 127.0.0.1/32
`

### PJSIP Endpoint Configuration

In pjsip.conf for the outbound trunk:
`
[provider-endpoint]
type = endpoint
context = from_external
disallow = all
allow = ulaw
allow = alaw
outbound_auth = provider-auth
aors = provider-aor

[provider-auth]
type = auth
auth_type = userpass
password = trunk_password
username = trunk_username

[provider-aor]
type = aor
contact = sip:trunk.provider.example.com
`

## Twilio Detailed Setup

Twilio provides a cloud telephony API. telephony-mcp uses the Twilio REST API (version 2010-04-01) via the official 	wilio Python package. The Twilio SDK handles authentication and request signing automatically.

### Twilio Configuration Steps

1. Sign up at https://twilio.com (free trial includes credits)
2. Verify your personal phone number for trial mode
3. Purchase a phone number: go to Phone Numbers > Buy a Number, select a number with voice and SMS capabilities
4. Get credentials: go to Console Dashboard, copy Account SID and Auth Token
5. Set environment variables as described in the configuration section
6. Test with send_sms to your verified number

### Twilio Trial Mode Limitations

In trial mode:
- Calls can only be made to verified phone numbers
- SMS can only be sent to verified phone numbers
- A prompt message is prepended to outgoing calls
- Upgrade to a paid account to remove these restrictions

## E.164 Number Validation Examples

Valid E.164 numbers (accepted by add_contact):
- +436641234567 (Austria mobile)
- +4312345678 (Austria landline)
- +49301234567 (Germany Berlin)
- +447911123456 (UK mobile)
- +14155551234 (US)
- +81312345678 (Japan Tokyo)

Invalid numbers (rejected by add_contact):
- 06641234567 (missing + prefix)
- +06641234567 (contains 0 after +)
- +12345 (too few digits)
- +1234567890123456 (too many digits)
- +abc123456 (non-digit characters)

## Performance Troubleshooting

### Call Setup Time Analysis

When a call fails or takes too long, analyze the timing:
1. Audio synthesis: the speechops call should complete in 1-3 seconds
2. ARI origination: POST to /channels takes 1-2 seconds
3. Call ringing: 5-30 seconds depending on the recipient answering
4. Audio playback: 1-60 seconds depending on message length
5. Total for answered call: typically 10-45 seconds

### Common Performance Issues

- Slow speechops: Check network connectivity to speechops server. Consider pre-caching WAV files for frequently used messages.
- Slow origination: Check SIP trunk registration status. Unregistered trunks cause timeouts.
- No answer: Verify phone number is correct and reachable. Consider leaving a callback number in the message.

## Call Record Analysis

The audit database in data/calls.db records every operation. Query it directly for analysis:

`sql
-- Get success rate
SELECT op, COUNT(*) as total, SUM(success) as successful, ROUND(100.0 * SUM(success) / COUNT(*), 1) as pct
FROM calls GROUP BY op;

-- Get recent failures
SELECT ts, op, to_number, error FROM calls WHERE success = 0 ORDER BY ts DESC LIMIT 10;

-- Get average duration by operation
SELECT op, AVG(duration_ms) as avg_ms FROM calls GROUP BY op;

-- Get calls by provider
SELECT provider, COUNT(*) FROM calls GROUP BY provider;
`

## Voice Message Scripting Guidelines

For best TTS results with speechops (Gemini):

- Keep messages under 30 seconds of speech (approximately 75 words in German, 100 words in English)
- Use clear, simple sentence structures
- Avoid homophones and words with ambiguous pronunciation
- For German, use standard Hochdeutsch pronunciation
- Test messages with telephony_dispatch_test before using in production
- For emergency messages, keep the critical information in the first sentence

Example good message: "Achtung. Dies ist ein automatisierter Notruf. Bitte ueberpruefen Sie den Status des Servers und kontaktieren Sie den Administrator."

Example message to avoid: "The IPsec tunnel's MTU (which is 1500 bytes by default for Ethernet) needs to be reconfigured to 1400 bytes to accommodate the additional encapsulation overhead." (Too technical, likely to be mispronounced.)
