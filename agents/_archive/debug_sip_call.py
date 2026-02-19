"""Debug SIP call status and trunk configuration"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.protocol import sip as sip_proto
from livekit.protocol import room as room_proto


async def debug():
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # Check the outbound trunk details
        print("=== Outbound Trunk Details ===")
        outbound = await lk.sip.list_sip_outbound_trunk(
            sip_proto.ListSIPOutboundTrunkRequest()
        )
        for t in outbound.items:
            if t.sip_trunk_id == "ST_NvMu6L8DwHAq":
                print(f"  ID: {t.sip_trunk_id}")
                print(f"  Name: {t.name}")
                print(f"  Address: {t.address}")
                print(f"  Transport: {t.transport}")
                print(f"  Numbers: {t.numbers}")
                print(f"  Auth Username: {t.auth_username}")
                print(f"  Auth Password set: {bool(t.auth_password)}")
                # Print all fields
                print(f"  Full proto: {t}")

        # Check rooms - look for the call room
        print("\n=== Active Rooms ===")
        rooms = await lk.room.list_rooms(room_proto.ListRoomsRequest())
        for r in rooms.rooms:
            print(f"  Room: {r.name} (participants: {r.num_participants}, created: {r.creation_time})")
            if "aime-outbound" in r.name:
                # Get participants in this room
                participants = await lk.room.list_participants(
                    room_proto.ListParticipantsRequest(room=r.name)
                )
                for p in participants.participants:
                    print(f"    Participant: {p.identity} (state: {p.state}, name: {p.name})")

        # Try to get SIP call info
        print("\n=== Recent SIP Participants ===")
        # List all dispatch rules to confirm config
        rules = await lk.sip.list_sip_dispatch_rule(
            sip_proto.ListSIPDispatchRuleRequest()
        )
        for r in rules.items:
            print(f"  Rule: {r.sip_dispatch_rule_id} - trunks: {r.trunk_ids}")
            print(f"    Rule details: {r.rule}")

    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(debug())
