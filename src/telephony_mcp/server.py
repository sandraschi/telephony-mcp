# src/telephony_mcp/server.py

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from telephony_mcp.providers.asterisk_provider import AsteriskProvider
from telephony_mcp.providers.twilio_provider import TwilioProvider

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telephony-mcp")

# Initialize FastMCP server
mcp = FastMCP("Telephony Bridge")

def get_provider():
    """Factory to return the active telephony provider."""
    mode = os.getenv("TELEPHONY_PROVIDER", "asterisk").lower()
    if mode == "twilio":
        return TwilioProvider()
    return AsteriskProvider()

@mcp.tool()
async def make_emergency_call(to_number: str, message: str) -> dict[str, Any]:
    """
    Triggers an automated emergency call with a German TTS message.
    to_number: Destination in E.164 format (+43...)
    message: The German message to be spoken.
    """
    logger.info(f"Initiating emergency call to {to_number}")
    provider = get_provider()
    result = await provider.make_call(to_number, message, script_type="emergency")
    return result

@mcp.tool()
async def send_emergency_sms(to_number: str, text: str) -> dict[str, Any]:
    """
    Triggers an automated emergency SMS.
    to_number: Destination in E.164 format (+43...)
    text: SMS content.
    """
    logger.info(f"Sending emergency SMS to {to_number}")
    provider = get_provider()
    result = await provider.send_sms(to_number, text)
    return result

@mcp.tool()
async def telephony_dispatch_test(sip_uri: str) -> dict[str, Any]:
    """
    Performs a 'Dry Run' rescue verification call to a test SIP URI (e.g. Linphone).
    sip_uri: The destination URI (e.g. sip:linphone@localhost)
    """
    test_msg = "Achtung. Dies ist ein Test der RoboFang Rettungskette. Bitte bestaetigen Sie den Empfang."
    provider = get_provider()
    # For SIP providers, to_number can be a full URI
    result = await provider.make_call(sip_uri, test_msg, script_type="test")
    return result

if __name__ == "__main__":
    mcp.run()
