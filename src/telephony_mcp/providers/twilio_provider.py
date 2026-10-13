# src/telephony_mcp/providers/twilio_provider.py

import asyncio
import logging
import os
from typing import Any

from twilio.rest import Client

from telephony_mcp.providers.base import TelephonyProvider

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
            logger.warning("Twilio credentials missing - running in mock mode.")

    async def make_call(
        self, to_number: str, message: str, script_type: str = "emergency"
    ) -> dict[str, Any]:
        if not self.client:
            return {"success": True, "call_id": "MOCK_TWILIO_CALL", "mode": "mock"}

        twiml = (
            f"<Response>"
            f'<Say language="de-AT" voice="Polly.Marlene-Neural">{message}</Say>'
            f"</Response>"
        )

        def _create():
            return self.client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=self.from_number,
            )

        try:
            call = await asyncio.to_thread(_create)
            return {"success": True, "call_id": call.sid, "mode": "twilio"}
        except Exception as e:
            logger.error(f"Twilio call failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_sms(self, to_number: str, text: str) -> dict[str, Any]:
        if not self.client:
            return {"success": True, "sms_id": "MOCK_TWILIO_SMS", "mode": "mock"}

        def _create():
            return self.client.messages.create(
                body=text,
                from_=self.from_number,
                to=to_number,
            )

        try:
            msg = await asyncio.to_thread(_create)
            return {"success": True, "sms_id": msg.sid, "mode": "twilio"}
        except Exception as e:
            logger.error(f"Twilio SMS failed: {e}")
            return {"success": False, "error": str(e)}
