# src/telephony_mcp/providers/asterisk_provider.py

import logging
import os
from typing import Any

import aiohttp
from telephony_mcp.providers.base import TelephonyProvider

logger = logging.getLogger(__name__)

class AsteriskProvider(TelephonyProvider):
    def __init__(self):
        self.ari_url = os.getenv("ASTERISK_ARI_URL", "http://localhost:8088/ari")
        self.ari_user = os.getenv("ASTERISK_ARI_USER", "robofang")
        self.ari_pass = os.getenv("ASTERISK_ARI_PASS", "robofang_pass")
        self.app_name = "robofang"
        self.default_tech = "PJSIP/provider-endpoint" # From pjsip.conf

    async def make_call(self, to_number: str, message: str, script_type: str = "emergency") -> dict[str, Any]:
        """
        1. Originates call via ARI to a Stasis app.
        2. Once answered, plays TTS (handled via Playback URLs in Asterisk 20+).
        Note: For industrial SOTA, we would use a local TTS engine and provide the URL.
        """
        auth = aiohttp.BasicAuth(self.ari_user, self.ari_pass)

        # In a real SOTA 2026 setup, we would call an internal TTS service to generate
        # a high-fidelity German wav/mp3 and get its URL.
        # For this industrial beta, we assume we use Asterisk's internal playback
        # or a pre-defined TTS bridge.

        originate_url = f"{self.ari_url}/channels"
        params = {
            "endpoint": f"{self.default_tech}/sip:{to_number}",
            "app": self.app_name,
            "appArgs": message, # Pass message to Stasis app
            "callerId": "RoboFang Responder",
            "variables": {"MESSAGE_TEXT": message}
        }

        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.post(originate_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        channel_id = data.get("id")
                        logger.info(f"Asterisk call originated: {channel_id}")
                        return {"success": True, "call_id": channel_id, "mode": "asterisk"}
                    else:
                        text = await resp.text()
                        logger.error(f"Asterisk ARI Fail ({resp.status}): {text}")
                        return {"success": False, "error": f"ARI status {resp.status}"}
        except Exception as e:
            logger.error(f"Asterisk connection error: {e}")
            return {"success": False, "error": str(e)}

    async def send_sms(self, to_number: str, text: str) -> dict[str, Any]:
        """
        Note: SIP SMS depends on provider support (SIP MESSAGE).
        Twilio is better for SMS, but Asterisk can do it if the trunk allows.
        """
        logger.info(f"SIP SMS to {to_number} (NOT IMPLEMENTED - SIP trunk dependent)")
        return {"success": False, "error": "SIP SMS not supported by current trunk driver"}
