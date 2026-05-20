# src/telephony_mcp/contacts.py
#
# JSON-backed contact store.
# Resolves names ("Steve", "Marion") to E.164 numbers (+43...).
# File: data/contacts.json — created on first write.

import asyncio
import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

CONTACTS_PATH = Path(
    os.getenv(
        "TELEPHONY_CONTACTS_PATH",
        str(Path(__file__).parent.parent.parent.parent / "data" / "contacts.json"),
    )
)

E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def _is_e164(s: str) -> bool:
    return bool(E164_RE.match(s))


def _load() -> dict[str, dict]:
    """Return contacts dict {name_lower: {name, number, notes}}. Thread-safe read."""
    if not CONTACTS_PATH.exists():
        return {}
    try:
        return json.loads(CONTACTS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to read contacts: {e}")
        return {}


def _save(contacts: dict[str, dict]) -> None:
    CONTACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTACTS_PATH.write_text(
        json.dumps(contacts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def resolve(name_or_number: str) -> tuple[str, str] | None:
    """
    Resolve a contact name or E.164 number.

    Returns (e164_number, display_name) or None if not found.
    If input is already E.164, returns it as-is with the number as display name.
    """
    s = name_or_number.strip()
    if _is_e164(s):
        return s, s

    def _lookup():
        contacts = _load()
        key = s.lower()
        # Exact key match
        if key in contacts:
            c = contacts[key]
            return c["number"], c["name"]
        # Partial match on name
        for k, c in contacts.items():
            if key in k or key in c["name"].lower():
                return c["number"], c["name"]
        return None

    return await asyncio.to_thread(_lookup)


async def add_contact(name: str, number: str, notes: str = "") -> dict:
    """Add or update a contact. Number must be E.164."""
    if not _is_e164(number):
        return {"success": False, "error": f"Number must be E.164 format (+43...), got: {number}"}

    def _write():
        contacts = _load()
        key = name.strip().lower()
        contacts[key] = {"name": name.strip(), "number": number, "notes": notes}
        _save(contacts)
        return contacts[key]

    record = await asyncio.to_thread(_write)
    logger.info(f"Contact saved: {name} → {number}")
    return {"success": True, "contact": record}


async def remove_contact(name: str) -> dict:
    def _delete():
        contacts = _load()
        key = name.strip().lower()
        if key not in contacts:
            return False
        del contacts[key]
        _save(contacts)
        return True

    found = await asyncio.to_thread(_delete)
    if found:
        return {"success": True, "removed": name}
    return {"success": False, "error": f"Contact '{name}' not found"}


async def list_contacts() -> list[dict]:
    def _list():
        return list(_load().values())

    return await asyncio.to_thread(_list)
