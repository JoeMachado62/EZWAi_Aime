"""
Test script: Outbound call to Joe's cell with custom greeting
Creates room with agent dispatch. The agent itself places the SIP call
(per LiveKit docs: agent dials from within the room).
"""
import asyncio
import json
import os
import time
import logging

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-outbound")


async def main():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    logger.info(f"LiveKit URL: {livekit_url}")
    logger.info(f"API Key: {api_key[:8]}...")

    if not all([livekit_url, api_key, api_secret]):
        logger.error("Missing required env vars")
        return

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    phone_number = "+12398881606"
    timestamp = int(time.time())
    room_name = f"aime-test-outbound-{timestamp}"

    # Custom prompt that tells the agent exactly what to say
    custom_prompt = """You are making a quick test call. Your ONLY task is to deliver this exact message:

"Good Morning Joe, We got the outbound calling Working! Hooray!"

After delivering the message, say goodbye and end the call. Keep it brief and cheerful.
If you reach voicemail, leave the same message as a voicemail."""

    metadata = json.dumps({
        "direction": "outbound",
        "custom_prompt": custom_prompt,
        "phone_number": phone_number,
        "contact_name": "Joe",
    })

    logger.info(f"Creating room with agent dispatch + outbound metadata...")
    logger.info(f"Phone: {phone_number}")
    logger.info(f"Room: {room_name}")

    try:
        # Create room with agent dispatch — agent will read metadata and place the SIP call
        create_room_req = api.CreateRoomRequest(
            name=room_name,
            metadata=metadata,
            agents=[api.RoomAgentDispatch(
                agent_name="aime-voice-agent",
                metadata=metadata,
            )],
        )
        room = await lk.room.create_room(create_room_req)
        logger.info(f"Room created: {room.name} (sid={room.sid})")
        logger.info("Agent dispatched — it will place the SIP call from within the room.")
        logger.info("Monitoring call for 90 seconds...")

        # Monitor the room
        for i in range(18):
            await asyncio.sleep(5)
            try:
                parts = await lk.room.list_participants(api.ListParticipantsRequest(room=room_name))
                count = len(parts.participants)
                identities = [p.identity for p in parts.participants]
                logger.info(f"  [{i*5}s] Participants: {count} - {identities}")
                if count == 0 and i > 2:
                    logger.info("  All participants left, call ended.")
                    break
            except Exception:
                logger.info(f"  [{i*5}s] Room may have closed")
                break

    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()

    await lk.aclose()


if __name__ == "__main__":
    asyncio.run(main())
