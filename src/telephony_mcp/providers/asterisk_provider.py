# src/telephony_mcp/providers/asterisk_provider.py

import logging
import os
from typing import Any

from telephony_mcp.ari_client import ARIClient
from telephony_mcp.audio import synthesize_wav
from telephony_mcp.providers.base import TelephonyProvider

logger = logging.getLogger(__name__)


class AsteriskProvider(TelephonyProvider):
    def __init__(self):
        self.ari_url = os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari")
        self.ari_user = os.getenv("ASTERISK_ARI_USER", "robofang")
        self.ari_pass = os.getenv("ASTERISK_ARI_PASS", "robofang_pass")
        self.app_name = "robofang"
        # PJSIP outbound endpoint name from pjsip.conf [provider-endpoint]
        self.outbound_endpoint = os.getenv("ASTERISK_OUTBOUND_ENDPOINT", "provider-endpoint")

    def _build_endpoint(self, to: str) -> str:
        """
        Build the ARI endpoint string for an outbound call.

        E.164 numbers   → PJSIP/provider-endpoint/sip:+43...
        Full SIP URIs   → PJSIP/linphone@localhost (test calls)
        """
        if to.startswith("sip:"):
            # Already a SIP URI — strip prefix for PJSIP dial
            return f"PJSIP/{to[4:]}"
        return f"PJSIP/{self.outbound_endpoint}/sip:{to}"

    async def make_call(
        self, to_number: str, message: str, script_type: str = "emergency"
    ) -> dict[str, Any]:
        """
        Synthesize `message` via speechops (Gemini TTS, fallback pre-recorded WAV),
        originate an outbound call via ARI, wait for answer, play the audio, hang up.
        """
        # Step 1: get audio
        wav_path = await synthesize_wav(message, script_type)
        if wav_path is None:
            logger.warning("No audio available — call will connect silently")

        # Step 2: originate + lifecycle
        endpoint = self._build_endpoint(to_number)
        async with ARIClient(
            self.ari_url, self.ari_user, self.ari_pass, self.app_name
        ) as ari:
            result = await ari.call_and_play(endpoint, wav_path)

        return result

    async def send_sms(self, to_number: str, text: str) -> dict[str, Any]:
        """
        SIP MESSAGE (SMS over SIP) is trunk-dependent.
        Most Austrian SIP trunks do not support it — use Twilio for SMS.
        """
        logger.info(f"SIP SMS to {to_number} — not supported by Asterisk provider")
        return {
            "success": False,
            "error": (
                "SIP SMS is trunk-dependent and not implemented. "
                "Set TELEPHONY_PROVIDER=twilio for SMS support."
            ),
        }
