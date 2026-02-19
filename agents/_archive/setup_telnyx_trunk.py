"""
Create outbound SIP trunk in LiveKit using Telnyx credentials.
Run once to set up the trunk, then update .env with the returned trunk ID.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.protocol import sip as sip_proto


async def create_outbound_trunk():
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # Create outbound SIP trunk pointing to Telnyx
        trunk = await lk.sip.create_sip_outbound_trunk(
            sip_proto.CreateSIPOutboundTrunkRequest(
                trunk=sip_proto.SIPOutboundTrunkInfo(
                    name="Telnyx EZWAI AIME Outbound",
                    address="sip.telnyx.com",
                    numbers=["+12392169696"],
                    auth_username="userjoemachado6245765",
                    auth_password="mRv1$y^_Rq+S",
                )
            )
        )
        print(f"Outbound trunk created!")
        print(f"  Trunk ID: {trunk.sip_trunk_id}")
        print(f"  Name: {trunk.name}")
        print(f"  Address: {trunk.address}")
        print(f"  Numbers: {trunk.numbers}")
        print(f"\nUpdate your .env file:")
        print(f"  LIVEKIT_SIP_OUTBOUND_TRUNK_ID={trunk.sip_trunk_id}")
        print(f"  LIVEKIT_OUTBOUND_PHONE_NUMBER=+12392169696")
        return trunk.sip_trunk_id

    finally:
        await lk.aclose()


async def list_trunks():
    """List existing SIP trunks for reference"""
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # List outbound trunks
        outbound = await lk.sip.list_sip_outbound_trunk(
            sip_proto.ListSIPOutboundTrunkRequest()
        )
        print("\n--- Existing Outbound Trunks ---")
        for t in outbound.items:
            print(f"  {t.sip_trunk_id}: {t.name} → {t.address} ({t.numbers})")

        # List inbound trunks
        inbound = await lk.sip.list_sip_inbound_trunk(
            sip_proto.ListSIPInboundTrunkRequest()
        )
        print("\n--- Existing Inbound Trunks ---")
        for t in inbound.items:
            print(f"  {t.sip_trunk_id}: {t.name} ({t.numbers})")

    finally:
        await lk.aclose()


if __name__ == "__main__":
    print("=== Creating Telnyx Outbound SIP Trunk ===\n")
    trunk_id = asyncio.run(create_outbound_trunk())
    print("\n=== Listing All Trunks ===")
    asyncio.run(list_trunks())
