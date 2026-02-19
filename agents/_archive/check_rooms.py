"""Check if the outbound room exists and has participants"""
import asyncio, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
from livekit import api
from livekit.protocol import room as room_proto

async def check():
    lk = api.LiveKitAPI(
        os.environ["LIVEKIT_URL"],
        os.environ["LIVEKIT_API_KEY"],
        os.environ["LIVEKIT_API_SECRET"],
    )
    try:
        rooms = await lk.room.list_rooms(room_proto.ListRoomsRequest())
        if not rooms.rooms:
            print("No active rooms found.")
        for r in rooms.rooms:
            print(f"Room: {r.name}")
            print(f"  Participants: {r.num_participants}")
            print(f"  Metadata: {r.metadata[:200] if r.metadata else 'none'}")
            participants = await lk.room.list_participants(
                room_proto.ListParticipantsRequest(room=r.name)
            )
            for p in participants.participants:
                print(f"  - {p.identity} (state={p.state}, name={p.name})")
    finally:
        await lk.aclose()

asyncio.run(check())
