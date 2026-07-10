"""
Shared LiveKit dispatch helpers — room creation, SIP outbound, cloud agent dispatch.

Used by:
  - app/voice_agent/agent.py (self-hosted voice-agent HTTP /dispatch)
  - app/backend/services/livekit_cloud_dispatch.py (cloud-only mode)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger("voice_agent.livekit_dispatch")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "ARIA")

SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "twilio-aria")
SIP_OUTBOUND_NUMBER = os.getenv("SIP_OUTBOUND_NUMBER", "")
SIP_TERMINATION_ADDRESS = os.getenv("SIP_TERMINATION_ADDRESS", "")
SIP_AUTH_USERNAME = os.getenv("SIP_AUTH_USERNAME", "")
SIP_AUTH_PASSWORD = os.getenv("SIP_AUTH_PASSWORD", "")
SIP_FROM_HOST = os.getenv("SIP_FROM_HOST", SIP_TERMINATION_ADDRESS)
SIP_TRANSPORT = os.getenv("SIP_TRANSPORT", "SIP_TRANSPORT_TCP")


class LiveKitSIPDispatcher:
    """Creates LiveKit rooms and dials out via SIP to candidates."""

    def __init__(
        self,
        *,
        lk_url: str = LIVEKIT_URL,
        api_key: str = LIVEKIT_API_KEY,
        api_secret: str = LIVEKIT_API_SECRET,
    ):
        self.lk_url = lk_url.replace("ws://", "http://").replace("wss://", "https://")
        self.api_key = api_key
        self.api_secret = api_secret
        self._resolved_trunk_id: Optional[str] = None

    async def resolve_sip_trunk_id(self, api) -> str:
        if self._resolved_trunk_id:
            return self._resolved_trunk_id

        try:
            from livekit.protocol.sip import (
                DeleteSIPTrunkRequest,
                ListSIPOutboundTrunkRequest,
                SIPTransport,
            )

            transport_map = {
                "SIP_TRANSPORT_AUTO": SIPTransport.SIP_TRANSPORT_AUTO,
                "SIP_TRANSPORT_UDP": SIPTransport.SIP_TRANSPORT_UDP,
                "SIP_TRANSPORT_TCP": SIPTransport.SIP_TRANSPORT_TCP,
                "SIP_TRANSPORT_TLS": SIPTransport.SIP_TRANSPORT_TLS,
            }
            desired_transport = transport_map.get(SIP_TRANSPORT, SIPTransport.SIP_TRANSPORT_TCP)
            desired_from_host = SIP_FROM_HOST

            resp = await api.sip.list_outbound_trunk(ListSIPOutboundTrunkRequest())
            trunks = list(resp.items) if resp and resp.items else []
            for trunk in trunks:
                trunk_id = trunk.sip_trunk_id or ""
                trunk_name = trunk.name or ""
                trunk_addr = trunk.address or ""
                trunk_transport = trunk.transport
                trunk_from_host = trunk.from_host or ""
                if (
                    trunk_addr == SIP_TERMINATION_ADDRESS
                    or trunk_name == SIP_TRUNK_ID
                    or trunk_id == SIP_TRUNK_ID
                ):
                    if trunk_transport != desired_transport or trunk_from_host != desired_from_host:
                        try:
                            await api.sip.delete_sip_trunk(
                                DeleteSIPTrunkRequest(sip_trunk_id=trunk_id)
                            )
                        except Exception as del_err:
                            logger.error("Failed to delete stale SIP trunk %s: %s", trunk_id, del_err)
                        break
                    self._resolved_trunk_id = trunk_id
                    return trunk_id
        except Exception as e:
            logger.warning("Failed to list SIP trunks: %s", e)

        trunk_id = await self._create_sip_trunk(api)
        if trunk_id:
            self._resolved_trunk_id = trunk_id
            return trunk_id

        self._resolved_trunk_id = SIP_TRUNK_ID
        return SIP_TRUNK_ID

    async def _create_sip_trunk(self, api) -> Optional[str]:
        try:
            from livekit.protocol.sip import (
                CreateSIPOutboundTrunkRequest,
                SIPOutboundTrunkInfo,
                SIPTransport,
            )

            transport_map = {
                "SIP_TRANSPORT_AUTO": SIPTransport.SIP_TRANSPORT_AUTO,
                "SIP_TRANSPORT_UDP": SIPTransport.SIP_TRANSPORT_UDP,
                "SIP_TRANSPORT_TCP": SIPTransport.SIP_TRANSPORT_TCP,
                "SIP_TRANSPORT_TLS": SIPTransport.SIP_TRANSPORT_TLS,
            }
            transport = transport_map.get(SIP_TRANSPORT, SIPTransport.SIP_TRANSPORT_TCP)
            req = CreateSIPOutboundTrunkRequest(
                trunk=SIPOutboundTrunkInfo(
                    name=SIP_TRUNK_ID,
                    address=SIP_TERMINATION_ADDRESS,
                    numbers=[SIP_OUTBOUND_NUMBER],
                    auth_username=SIP_AUTH_USERNAME,
                    auth_password=SIP_AUTH_PASSWORD,
                    transport=transport,
                    from_host=SIP_FROM_HOST,
                )
            )
            result = await api.sip.create_outbound_trunk(req)
            return result.sip_trunk_id
        except Exception as e:
            logger.error("SIP outbound trunk creation failed: %s", e)
            return None

    async def create_screening_room(self, session_id: int) -> dict[str, str]:
        """Create a LiveKit room for a screening call (SIP dial is done by the cloud agent)."""
        from livekit.api import LiveKitAPI
        from livekit.protocol.room import CreateRoomRequest

        room_name = f"voice-screen-{session_id}"
        api = LiveKitAPI(self.lk_url, self.api_key, self.api_secret)
        try:
            await api.room.create_room(
                CreateRoomRequest(
                    name=room_name,
                    empty_timeout=120,
                    max_participants=3,
                )
            )
            logger.info("Screening room created: %s", room_name)
            return {"room_name": room_name, "lk_url": LIVEKIT_URL}
        finally:
            await api.aclose()

    async def create_room_and_dial(
        self,
        *,
        session_id: int,
        phone_number: str,
        candidate_name: str,
    ) -> dict[str, str]:
        """Create a LiveKit room and place an outbound SIP call to the candidate."""
        from livekit.api import CreateSIPParticipantRequest, LiveKitAPI
        from livekit.protocol.room import CreateRoomRequest

        room_name = f"voice-screen-{session_id}"
        participant_identity = f"candidate-{session_id}"
        api = LiveKitAPI(self.lk_url, self.api_key, self.api_secret)

        try:
            trunk_id = await self.resolve_sip_trunk_id(api)
            await api.room.create_room(
                CreateRoomRequest(
                    name=room_name,
                    empty_timeout=120,
                    max_participants=3,
                )
            )
            sip_phone = re.sub(r"[^\d+]", "", phone_number)
            await api.sip.create_sip_participant(
                CreateSIPParticipantRequest(
                    sip_trunk_id=trunk_id,
                    sip_call_to=sip_phone,
                    room_name=room_name,
                    participant_identity=participant_identity,
                    participant_name=candidate_name,
                    hide_phone_number=False,
                )
            )
            logger.info(
                "SIP call placed: room=%s phone=%s trunk=%s",
                room_name,
                sip_phone,
                trunk_id,
            )
            return {"room_name": room_name, "lk_url": LIVEKIT_URL}
        finally:
            await api.aclose()


async def resolve_sip_trunk_for_dispatch() -> str:
    """Resolve outbound SIP trunk ID for cloud agent metadata."""
    dispatcher = LiveKitSIPDispatcher()
    from livekit.api import LiveKitAPI

    api = LiveKitAPI(dispatcher.lk_url, dispatcher.api_key, dispatcher.api_secret)
    try:
        return await dispatcher.resolve_sip_trunk_id(api)
    finally:
        await api.aclose()


async def dispatch_cloud_agent(
    *,
    room_name: str,
    metadata: dict[str, Any],
    agent_name: str = LIVEKIT_AGENT_NAME,
    lk_url: str = LIVEKIT_URL,
    api_key: str = LIVEKIT_API_KEY,
    api_secret: str = LIVEKIT_API_SECRET,
) -> str:
    """Explicitly dispatch the LiveKit Cloud agent into a room with session metadata."""
    from livekit.api import LiveKitAPI
    from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest

    http_url = lk_url.replace("ws://", "http://").replace("wss://", "https://")
    api = LiveKitAPI(http_url, api_key, api_secret)
    try:
        req = CreateAgentDispatchRequest(
            agent_name=agent_name,
            room=room_name,
            metadata=json.dumps(metadata),
        )
        dispatch = await api.agent_dispatch.create_dispatch(req)
        dispatch_id = getattr(dispatch, "id", "") or getattr(dispatch, "dispatch_id", "")
        logger.info(
            "Cloud agent dispatched: agent=%s room=%s dispatch_id=%s",
            agent_name,
            room_name,
            dispatch_id,
        )
        return dispatch_id
    finally:
        await api.aclose()


async def dispatch_cloud_screening_call(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Full cloud dispatch: create room, dispatch ARIA cloud agent, agent dials SIP.

    The cloud agent starts its audio pipeline before placing the outbound call
    (LiveKit telephony best practice) so the greeting is heard when the candidate
    answers.

    ``payload`` mirrors the voice-agent /dispatch request body.
    """
    session_id = int(payload["session_id"])
    dispatcher = LiveKitSIPDispatcher()
    room_info = await dispatcher.create_screening_room(session_id)
    sip_trunk_id = await resolve_sip_trunk_for_dispatch()
    participant_identity = f"candidate-{session_id}"
    metadata = {
        "session_id": session_id,
        "tenant_id": payload.get("tenant_id"),
        "candidate_id": payload.get("candidate_id"),
        "candidate_name": payload.get("candidate_name"),
        "phone_number": payload.get("phone_number"),
        "participant_identity": participant_identity,
        "sip_trunk_id": sip_trunk_id,
        "jd_title": payload.get("jd_title"),
        "jd_must_have_skills": payload.get("jd_must_have_skills") or [],
        "depth": payload.get("depth") or "quick",
        "interview_config": payload.get("interview_config") or {},
        "interview_kit": payload.get("interview_kit") or {},
        "screening_result_id": payload.get("screening_result_id"),
        "tenant_config": payload.get("tenant_config") or {},
        "candidate_context": payload.get("candidate_context") or {},
        "aria_backend_url": os.getenv("ARIA_BACKEND_URL", "http://backend:8000"),
    }
    await dispatch_cloud_agent(room_name=room_info["room_name"], metadata=metadata)
    return {
        "success": True,
        "room_name": room_info["room_name"],
        "message": f"Cloud agent dispatched for session {session_id}",
    }
