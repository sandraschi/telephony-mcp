# src/telephony_mcp/providers/twilio_provider.py

import logging
import os
from typing import Any

from telephony_mcp.providers.base import TelephonyProvider
from twilio.rest import Client

logger = logging.getLogger(__name__)

class TwilioProvider(TelephonyProvider):
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not found; running in mock mode.")

    async def make_call(self, to_number: str, message: str, script_type: str = "emergency") -> dict[str, Any]:
        if not self.client:
            return {"success": True, "call_id": "MOCK_TWILIO_CALL", "mode": "mock"}

        try:
            # Twilio's neural TTS usually defaults to 'Polly.Marlene-Neural' for German
            twiml = f'<Response><Say language="de-AT" voice="Polly.Marlene-Neural">{message}</Say></Response>'
            call = self.client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=self.from_number
            )
            return {"success": True, "call_id": call.sid}
        except Exception as e:
            logger.error(f"Twilio call failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_sms(self, to_number: str, text: str) -> dict[str, Any]:
        if not self.client:
             return {"success": True, "sms_id": "MOCK_TWILIO_SMS", "mode": "mock"}

        try:
            message = self.client.messages.create(
                body=text,
                from_=self.from_number,
                to=to_number
            )
            return {"success": True, "sms_id": message.sid}
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return {"success": False, "error": str(e)}
