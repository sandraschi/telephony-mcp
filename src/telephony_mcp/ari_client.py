# src/telephony_mcp/ari_client.py
#
# Async ARI (Asterisk REST Interface) client.
#
# Handles the full outbound call lifecycle:
#   1. Originate channel → Stasis app
#   2. Open ARI WebSocket and wait for StasisStart on that channel
#   3. Answer, play WAV, wait for PlaybackFinished
#   4. Hangup
#
# ARI docs: https://docs.asterisk.org/Latest_API/API_Documentation/Asterisk_REST_Interface/

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Asterisk container path where telephony_tts WAVs land.
# Must match the volume mount in docker-compose.yml:
#   ./audio/tts:/var/lib/asterisk/sounds/telephony_tts:ro
ARI_SOUND_PREFIX = "telephony_tts"

# How long to wait for the callee to answer before giving up (seconds)
ANSWER_TIMEOUT = int(__import__("os").getenv("ARI_ANSWER_TIMEOUT_S", "30"))
# How long to wait for playback to finish
PLAYBACK_TIMEOUT = int(__import__("os").getenv("ARI_PLAYBACK_TIMEOUT_S", "60"))


class ARIClient:
    """
    Minimal async ARI client for outbound emergency call lifecycle.

    Usage:
        async with ARIClient(base_url, user, password, app_name) as ari:
            result = await ari.call_and_play(endpoint, wav_path)
    """

    def __init__(self, base_url: str, user: str, password: str, app_name: str):
        self.base_url = base_url.rstrip("/")
        self.auth = aiohttp.BasicAuth(user, password)
        self.app_name = app_name
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(auth=self.auth)
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call_and_play(
        self,
        endpoint: str,
        wav_path: Path | None,
        caller_id: str = "RoboFang Responder",
    ) -> dict[str, Any]:
        """
        Originate a call to `endpoint`, wait for answer, play `wav_path`, hang up.

        Args:
            endpoint: PJSIP endpoint string, e.g. "PJSIP/provider-endpoint/sip:+436641234567"
                      or a full SIP URI for test calls "PJSIP/linphone@localhost"
            wav_path: Path object from audio.synthesize_wav(). If None, call connects
                      silently (recipient hears silence then hangup).
            caller_id: CLI presented to recipient.

        Returns:
            dict with success, call_id, duration_s, error.
        """
        channel_id = await self._originate(endpoint, caller_id)
        if not channel_id:
            return {"success": False, "error": "ARI originate failed"}

        try:
            answered = await self._wait_for_stasis_start(channel_id)
            if not answered:
                return {
                    "success": False,
                    "call_id": channel_id,
                    "error": f"No answer within {ANSWER_TIMEOUT}s",
                }

            await self._answer(channel_id)

            played = False
            if wav_path and wav_path.exists():
                sound_id = f"{ARI_SOUND_PREFIX}/{wav_path.stem}"
                played = await self._play_and_wait(channel_id, sound_id)

            await self._hangup(channel_id)
            return {
                "success": True,
                "call_id": channel_id,
                "audio_played": played,
                "mode": "asterisk",
            }

        except Exception as e:
            logger.error(f"ARI call lifecycle error on {channel_id}: {e}")
            await self._hangup(channel_id)
            return {"success": False, "call_id": channel_id, "error": str(e)}

    # ------------------------------------------------------------------
    # ARI REST helpers
    # ------------------------------------------------------------------

    async def _originate(self, endpoint: str, caller_id: str) -> str | None:
        url = f"{self.base_url}/channels"
        payload = {
            "endpoint": endpoint,
            "app": self.app_name,
            "callerId": caller_id,
        }
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    cid = data.get("id")
                    logger.info(f"ARI originate OK: channel={cid} endpoint={endpoint}")
                    return cid
                body = await resp.text()
                logger.error(f"ARI originate failed ({resp.status}): {body[:300]}")
                return None
        except Exception as e:
            logger.error(f"ARI originate exception: {e}")
            return None

    async def _answer(self, channel_id: str) -> None:
        url = f"{self.base_url}/channels/{channel_id}/answer"
        try:
            async with self._session.post(url) as resp:
                logger.debug(f"ARI answer {channel_id}: {resp.status}")
        except Exception as e:
            logger.warning(f"ARI answer error: {e}")

    async def _play_and_wait(self, channel_id: str, sound_id: str) -> bool:
        """
        POST a playback, then poll ARI events until PlaybackFinished or timeout.
        Returns True if playback completed successfully.
        """
        url = f"{self.base_url}/channels/{channel_id}/play"
        payload = {"media": f"sound:{sound_id}"}
        try:
            async with self._session.post(url, json=payload) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    logger.error(f"ARI play failed ({resp.status}): {body[:200]}")
                    return False
                pb_data = await resp.json()
                playback_id = pb_data.get("id")
                logger.info(f"ARI playback started: {playback_id} sound={sound_id}")
        except Exception as e:
            logger.error(f"ARI play exception: {e}")
            return False

        # Poll for PlaybackFinished
        poll_url = f"{self.base_url}/playbacks/{playback_id}"
        deadline = asyncio.get_event_loop().time() + PLAYBACK_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(1)
            try:
                async with self._session.get(poll_url) as resp:
                    if resp.status == 404:
                        # Playback resource gone = finished
                        logger.info(f"ARI playback {playback_id} finished (404 = done)")
                        return True
                    if resp.status == 200:
                        data = await resp.json()
                        state = data.get("state", "")
                        if state == "done":
                            logger.info(f"ARI playback {playback_id} state=done")
                            return True
                        if state == "failed":
                            logger.error(f"ARI playback {playback_id} state=failed")
                            return False
            except Exception as e:
                logger.warning(f"ARI playback poll error: {e}")

        logger.warning(f"ARI playback {playback_id} timed out after {PLAYBACK_TIMEOUT}s")
        return False

    async def _hangup(self, channel_id: str) -> None:
        url = f"{self.base_url}/channels/{channel_id}"
        try:
            async with self._session.delete(url) as resp:
                logger.debug(f"ARI hangup {channel_id}: {resp.status}")
        except Exception as e:
            logger.warning(f"ARI hangup error: {e}")

    # ------------------------------------------------------------------
    # ARI WebSocket — wait for StasisStart
    # ------------------------------------------------------------------

    async def _wait_for_stasis_start(self, channel_id: str) -> bool:
        """
        Open ARI events WebSocket and wait for StasisStart on our channel_id.
        Returns True on answer, False on timeout or channel disappearing.
        """
        # Convert http(s) → ws(s)
        ws_base = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_base}/events?app={self.app_name}&api_key={self.auth.login}:{self.auth.password}"

        try:
            async with self._session.ws_connect(ws_url) as ws:
                deadline = asyncio.get_event_loop().time() + ANSWER_TIMEOUT
                async for msg in ws:
                    if asyncio.get_event_loop().time() > deadline:
                        logger.warning(f"StasisStart timeout for {channel_id}")
                        return False
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        event = json.loads(msg.data)
                        etype = event.get("type", "")
                        echan = event.get("channel", {}).get("id", "")
                        if etype == "StasisStart" and echan == channel_id:
                            logger.info(f"StasisStart received for {channel_id}")
                            return True
                        if etype in ("ChannelDestroyed", "ChannelHangupRequest") and echan == channel_id:
                            logger.info(f"Channel {channel_id} destroyed before answer")
                            return False
        except Exception as e:
            logger.error(f"ARI WebSocket error waiting for StasisStart: {e}")
            return False

        return False
