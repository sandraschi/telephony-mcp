# src/telephony_mcp/providers/base.py

from abc import ABC, abstractmethod
from typing import Any


class TelephonyProvider(ABC):
    """Base interface for telephony providers (Twilio, Asterisk, etc.)."""

    @abstractmethod
    async def make_call(self, to_number: str, message: str, script_type: str = "emergency") -> dict[str, Any]:
        """
        Initiates an outbound call with a specific message.
        Returns a dict with success/error/call_id.
        """
        pass

    @abstractmethod
    async def send_sms(self, to_number: str, text: str) -> dict[str, Any]:
        """
        Sends an outbound SMS.
        """
        pass
