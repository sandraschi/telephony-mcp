# src/telephony_mcp/server.py

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from fastmcp import FastMCP, Context
from fastmcp.server import create_proxy

from telephony_mcp.contacts import (
    add_contact as _add_contact,
    list_contacts as _list_contacts,
    remove_contact as _remove_contact,
    resolve,
)
from telephony_mcp.db import get_stats, init_db, log_call
from telephony_mcp.providers.asterisk_provider import AsteriskProvider
from telephony_mcp.providers.twilio_provider import TwilioProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telephony-mcp")

init_db()

mcp = FastMCP(
    "Telephony Bridge",
    instructions=(
        "MCP server for outbound phone calls and SMS. "
        "Accepts contact names ('Steve', 'Marion') or E.164 numbers (+43...). "
        "Provider: TELEPHONY_PROVIDER=asterisk (default, uses Asterisk ARI + speechops TTS) "
        "or TELEPHONY_PROVIDER=twilio. All calls logged to SQLite audit DB."
    ),
)

# MCP Bridge: ProxyProvider for multi-server federation
_bridge_urls = os.getenv("MCP_BRIDGE_URLS", "")
if _bridge_urls:
    for _url in _bridge_urls.split(","):
        _url = _url.strip()
        if _url:
            try:
                mcp.add_provider(create_proxy(_url))
                logger.info("MCP bridge registered: %s", _url)
            except Exception as e:
                logger.warning("MCP bridge failed for %s: %s", _url, e)


def get_provider():
    mode = os.getenv("TELEPHONY_PROVIDER", "asterisk").lower()
    if mode == "twilio":
        return TwilioProvider()
    return AsteriskProvider()


async def _resolve_or_fail(contact: str) -> tuple[str, str] | None:
    """Resolve contact name/number. Returns (e164, display_name) or None."""
    result = await resolve(contact)
    return result


# ── Call tools ────────────────────────────────────────────────────────────────

@mcp.tool()
async def make_call(
    contact: str,
    message: str,
    ctx: Context,
    script_type: str = "general",
) -> dict[str, Any]:
    """
    Place an outbound phone call and speak a message via TTS.

    Accepts a contact name from the contacts store ("Steve", "Marion") or
    a raw E.164 number (+43664XXXXXXX). The message is synthesised via
    speechops (Gemini TTS) with a pre-recorded WAV fallback.

    Args:
        contact: Contact name or E.164 number.
        message: Text to speak. German and English both work.
        script_type: Hint for audio caching — 'general', 'emergency', 'test'.

    Returns:
        dict with success, call_id, mode, contact_name, to_number, error.
    """
    resolved = await _resolve_or_fail(contact)
    if resolved is None:
        return {
            "success": False,
            "error": f"Contact '{contact}' not found. Add via add_contact or use E.164.",
        }
    to_number, contact_name = resolved
    await ctx.info(f"Calling {contact_name} ({to_number})")

    provider = get_provider()
    t0 = time.monotonic()
    result = await provider.make_call(to_number, message, script_type=script_type)
    duration_ms = int((time.monotonic() - t0) * 1000)

    await log_call({
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": "make_call",
        "contact_name": contact_name,
        "to_number": to_number,
        "message": message,
        "script_type": script_type,
        "provider": result.get("mode", os.getenv("TELEPHONY_PROVIDER", "asterisk")),
        "success": result.get("success", False),
        "call_id": result.get("call_id"),
        "error": result.get("error"),
        "audio_played": result.get("audio_played", False),
        "duration_ms": duration_ms,
    })
    return {**result, "contact_name": contact_name, "to_number": to_number}


@mcp.tool()
async def make_emergency_call(
    to_number: str,
    message: str,
    ctx: Context,
) -> dict[str, Any]:
    """
    Trigger an automated emergency call (backward-compatible wrapper for make_call).

    Args:
        to_number: E.164 number or contact name.
        message: German-language emergency message to speak.

    Returns:
        dict with success, call_id, mode, error.
    """
    return await make_call(to_number, message, ctx, script_type="emergency")


@mcp.tool()
async def send_sms(
    contact: str,
    text: str,
    ctx: Context,
) -> dict[str, Any]:
    """
    Send an SMS to a contact or E.164 number.

    Note: Requires TELEPHONY_PROVIDER=twilio. Asterisk SIP SMS is trunk-dependent.

    Args:
        contact: Contact name or E.164 number.
        text: SMS body.

    Returns:
        dict with success, sms_id, mode, error.
    """
    resolved = await _resolve_or_fail(contact)
    if resolved is None:
        return {"success": False, "error": f"Contact '{contact}' not found."}
    to_number, contact_name = resolved
    await ctx.info(f"Sending SMS to {contact_name} ({to_number})")

    provider = get_provider()
    t0 = time.monotonic()
    result = await provider.send_sms(to_number, text)
    duration_ms = int((time.monotonic() - t0) * 1000)

    await log_call({
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": "send_sms",
        "contact_name": contact_name,
        "to_number": to_number,
        "message": text,
        "script_type": "sms",
        "provider": result.get("mode", os.getenv("TELEPHONY_PROVIDER", "asterisk")),
        "success": result.get("success", False),
        "call_id": result.get("sms_id"),
        "error": result.get("error"),
        "audio_played": False,
        "duration_ms": duration_ms,
    })
    return {**result, "contact_name": contact_name, "to_number": to_number}


@mcp.tool()
async def telephony_dispatch_test(
    sip_uri: str,
    ctx: Context,
) -> dict[str, Any]:
    """
    Dry-run verification call to a local SIP URI (e.g. Linphone).

    Sends a fixed German test message. Does not require a real SIP trunk.

    Args:
        sip_uri: e.g. sip:linphone@localhost

    Returns:
        dict with success, call_id, mode, audio_played, error.
    """
    test_msg = (
        "Achtung. Dies ist ein Test der RoboFang Rettungskette. "
        "Bitte bestaetigen Sie den Empfang."
    )
    await ctx.info(f"Dispatch test → {sip_uri}")
    provider = get_provider()
    t0 = time.monotonic()
    result = await provider.make_call(sip_uri, test_msg, script_type="test")
    duration_ms = int((time.monotonic() - t0) * 1000)

    await log_call({
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": "dispatch_test",
        "contact_name": "TEST",
        "to_number": sip_uri,
        "message": test_msg,
        "script_type": "test",
        "provider": result.get("mode", os.getenv("TELEPHONY_PROVIDER", "asterisk")),
        "success": result.get("success", False),
        "call_id": result.get("call_id"),
        "error": result.get("error"),
        "audio_played": result.get("audio_played", False),
        "duration_ms": duration_ms,
    })
    return result


# ── Contact tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def add_contact(
    name: str,
    number: str,
    ctx: Context,
    notes: str = "",
) -> dict[str, Any]:
    """
    Add or update a contact in the phone book.

    Args:
        name: Display name (e.g. "Steve").
        number: E.164 phone number (e.g. +43664XXXXXXX).
        notes: Optional free-text notes.

    Returns:
        dict with success, contact record.
    """
    result = await _add_contact(name, number, notes)
    if result["success"]:
        await ctx.info(f"Contact saved: {name} → {number}")
    return result


@mcp.tool()
async def list_contacts(ctx: Context) -> dict[str, Any]:
    """
    List all contacts in the phone book.

    Returns:
        dict with contacts list and count.
    """
    contacts = await _list_contacts()
    return {"contacts": contacts, "count": len(contacts)}


@mcp.tool()
async def remove_contact(name: str, ctx: Context) -> dict[str, Any]:
    """
    Remove a contact from the phone book.

    Args:
        name: Contact name to remove.

    Returns:
        dict with success, error.
    """
    return await _remove_contact(name)


# ── Status ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def telephony_status(ctx: Context) -> dict[str, Any]:
    """
    Return current telephony configuration, provider readiness, and audit stats.

    Returns:
        dict with provider, config (redacted), ready flag, call statistics, contact count.
    """
    provider_name = os.getenv("TELEPHONY_PROVIDER", "asterisk").lower()
    if provider_name == "twilio":
        ready = bool(
            os.getenv("TWILIO_ACCOUNT_SID")
            and os.getenv("TWILIO_AUTH_TOKEN")
            and os.getenv("TWILIO_FROM_NUMBER")
        )
        config = {
            "TWILIO_ACCOUNT_SID": "set" if os.getenv("TWILIO_ACCOUNT_SID") else "missing",
            "TWILIO_AUTH_TOKEN": "set" if os.getenv("TWILIO_AUTH_TOKEN") else "missing",
            "TWILIO_FROM_NUMBER": os.getenv("TWILIO_FROM_NUMBER", "missing"),
        }
    else:
        ready = True
        config = {
            "ASTERISK_ARI_URL": os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari"),
            "ASTERISK_ARI_USER": os.getenv("ASTERISK_ARI_USER", "robofang"),
            "ASTERISK_ARI_PASS": "set" if os.getenv("ASTERISK_ARI_PASS") else "default",
            "SPEECHOPS_BASE_URL": os.getenv("SPEECHOPS_BASE_URL", "http://localhost:10918"),
        }

    stats = await get_stats()
    contacts = await _list_contacts()
    return {
        "provider": provider_name,
        "ready": ready,
        "config": config,
        "stats": stats,
        "contact_count": len(contacts),
    }


def main() -> None:
    init_db()
    mcp.run()


if __name__ == "__main__":
    main()
