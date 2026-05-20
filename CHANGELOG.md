# Changelog

All notable changes to Telephony-MCP are documented here.

## [0.2.0] — 2026-05-01 "General Dispatch"

### Fixed
- **FastMCP 3.2 compliance**: corrected import from `mcp.server.fastmcp` → `from fastmcp import FastMCP, Context`.
- Added missing `src/telephony_mcp/__init__.py` and `__main__.py` — package was not importable as a module.
- Added missing `src/telephony_mcp/providers/__init__.py`.
- Added `main()` function referenced in `pyproject.toml` scripts entry but absent.
- Twilio `client.calls.create()` and `client.messages.create()` wrapped in `asyncio.to_thread()` — were blocking the event loop.
- Fixed variable shadowing bug in `twilio_provider.py` (`message` param overwritten by SDK return value).
- Added `aiohttp>=3.9.0` to `pyproject.toml` (used by asterisk_provider but was missing from deps).

### Added
- **`src/telephony_mcp/audio.py`**: speechops TTS bridge. Calls `GET /api/v1/tts/wav` (Gemini by default), writes WAV to `audio/tts/`. Falls back to pre-recorded WAV from `audio/fallback/{script_type}.wav` if speechops is unreachable.
- **`src/telephony_mcp/ari_client.py`**: full ARI call lifecycle — originate, WebSocket wait for `StasisStart`, answer, play WAV via `sound:` URI, poll for `PlaybackFinished`, hangup. The actual audio playback path that was previously missing.
- **`src/telephony_mcp/contacts.py`**: JSON-backed contact store. Resolves names ("Steve", "Marion") to E.164 numbers. Partial name matching. E.164 pass-through.
- **`src/telephony_mcp/db.py`**: SQLite audit log. All call/SMS operations write a record (timestamp, op, contact_name, to_number, message, provider, success, call_id, error, audio_played, duration_ms). Schema migration on startup.
- **`make_call(contact, message, script_type)`**: generalised outbound call tool accepting contact name or raw E.164.
- **`add_contact` / `list_contacts` / `remove_contact`** MCP tools.
- **`send_sms(contact, text)`**: replaces `send_emergency_sms`, accepts contact names.
- **`telephony_status`** tool: provider config, readiness, audit stats, contact count.
- **`make_emergency_call`** kept as backward-compatible wrapper over `make_call`.
- **`data/contacts.json`**: contact store seeded with Steve and Marion placeholders.
- **`audio/tts/`** and **`audio/fallback/`** directories with README.
- **Audit dashboard webapp** (ports 10952/10953): Starlette 1.0 backend + Vite/React frontend. Call log table with contact name, op, provider, duration, status. Click-to-expand detail panel. Status page with Asterisk + speechops connectivity probes.
- **`start.ps1` / `start.bat`**: clears ports, creates data/audio dirs, installs npm deps if missing, starts backend + frontend, opens browser.
- `docker-compose.yml`: mounts `audio/tts` and `audio/fallback` into Asterisk container at `sounds/telephony_tts` and `sounds/telephony_fallback`.
- Starlette backend deps (`starlette>=1.0.0`, `uvicorn[standard]>=0.34.0`) added to `pyproject.toml`.
- Ports 10952/10953 registered in `mcp-central-docs/operations/WEBAPP_PORTS.md`.
- `TODO.md`: phased roadmap to full AI phone chatbot (Phase 1 complete, Phases 2–4 documented).

### Changed
- `server.py` tools now accept `ctx: Context` and log via `ctx.info()`.
- `server.py` tools time all operations and write audit records on every call including failures.
- `asterisk_provider.py` fully rewritten to use `audio.py` + `ari_client.py` instead of fire-and-forget originate.
- `pyproject.toml`: author email corrected, version bumped to 0.2.0, description updated.
- Claude Desktop config updated: entry point changed to `python -m telephony_mcp`, all env vars explicit.

---

## [1.0.0-alpha.1] — 2026-04-19 "Bridge Inception"

### Added
- **Alpha Launch**: Inception of the modular Telephony-MCP gateway.
- **Provider Factory**: Modular architecture supporting both local **Asterisk/SIP** and legacy **Twilio** backends.
- **Asterisk ARI Engine**: Native implementation of the Asterisk REST Interface for "Clean Bridge" digital audio injection.
- **AudioSocket Support**: Low-latency PCM audio streaming capabilities.
- **Sovereign Security Trinity**: Integrated **Ruff**, **Biome**, and **Semgrep** as pre-flight quality standards.
- **AED Support**: Purpose-built endpoints for Level 4 Autonomous Emergency Dispatch.
- **Docker Infrastructure**: Containerized Asterisk 20+ stack with PJSIP and ARI pre-configured.

---
First alpha release. Part of the **RoboFang (Beta)** fleet development.
