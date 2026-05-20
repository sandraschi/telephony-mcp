# src/telephony_mcp/audio.py
#
# Audio synthesis layer for telephony-mcp.
#
# Strategy:
#   1. Call speechops REST API (GET /api/v1/tts/wav) — Gemini by default (best German).
#   2. If speechops is unreachable or returns an error, fall back to a pre-recorded
#      WAV from audio/fallback/{script_type}.wav.
#   3. Write the result to a shared temp dir that Asterisk can read via its
#      ARI sound: URI scheme (mounted at ASTERISK_AUDIO_SHARE).

import logging
import os
import shutil
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

# Where synthesized WAVs land — must be mounted into the Asterisk container.
# Map container path /var/lib/asterisk/sounds/telephony_tts → this host dir.
AUDIO_SHARE = Path(
    os.getenv(
        "TELEPHONY_AUDIO_SHARE",
        str(Path(__file__).parent.parent.parent.parent / "audio" / "tts"),
    )
)

FALLBACK_DIR = Path(__file__).parent.parent.parent.parent / "audio" / "fallback"

SPEECHOPS_BASE = os.getenv("SPEECHOPS_BASE_URL", "http://localhost:10918")
SPEECHOPS_PROVIDER = os.getenv("SPEECHOPS_TTS_PROVIDER", "gemini")
SPEECHOPS_VOICE = os.getenv("SPEECHOPS_TTS_VOICE", "Kore")
SPEECHOPS_TIMEOUT = int(os.getenv("SPEECHOPS_TIMEOUT_S", "10"))


async def synthesize_wav(text: str, script_type: str = "emergency") -> Path | None:
    """
    Synthesize text to a WAV file readable by Asterisk.

    Returns the absolute Path to the WAV on success, None if both
    speechops and fallback are unavailable.

    The returned path is inside AUDIO_SHARE, so the ARI sound URI is:
        sound:telephony_tts/<filename_without_extension>
    """
    AUDIO_SHARE.mkdir(parents=True, exist_ok=True)

    # Sanitise filename: strip non-alphanum so Asterisk won't choke
    safe_type = "".join(c if c.isalnum() else "_" for c in script_type)
    out_path = AUDIO_SHARE / f"{safe_type}.wav"

    # --- Try speechops ---
    wav_bytes = await _fetch_from_speechops(text)
    if wav_bytes:
        out_path.write_bytes(wav_bytes)
        logger.info(f"TTS WAV written via speechops: {out_path} ({len(wav_bytes)} bytes)")
        return out_path

    # --- Fallback: pre-recorded ---
    fallback = FALLBACK_DIR / f"{safe_type}.wav"
    if fallback.exists():
        shutil.copy2(fallback, out_path)
        logger.warning(f"speechops unreachable — using fallback WAV: {fallback}")
        return out_path

    logger.error(
        f"No audio available: speechops failed and no fallback at {fallback}. "
        "Call will connect silently."
    )
    return None


async def _fetch_from_speechops(text: str) -> bytes | None:
    """Call speechops /api/v1/tts/wav and return raw WAV bytes, or None on any failure."""
    url = f"{SPEECHOPS_BASE}/api/v1/tts/wav"
    params = {
        "text": text,
        "provider": SPEECHOPS_PROVIDER,
        "voice_id": SPEECHOPS_VOICE,
    }
    try:
        timeout = aiohttp.ClientTimeout(total=SPEECHOPS_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.read()
                body = await resp.text()
                logger.warning(f"speechops TTS returned {resp.status}: {body[:200]}")
                return None
    except Exception as e:
        logger.warning(f"speechops unreachable: {e}")
        return None
