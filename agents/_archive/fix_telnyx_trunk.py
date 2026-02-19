"""
Fix Telnyx outbound SIP trunk with proper headers and config.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.protocol import sip as sip_proto


async def inspect_trunk_fields():
    """Inspect what fields SIPOutboundTrunkInfo supports"""
    # Check available fields on the proto
    info = sip_proto.SIPOutboundTrunkInfo()
    print("=== SIPOutboundTrunkInfo fields ===")
    for field in info.DESCRIPTOR.fields:
        print(f"  {field.name} (type={field.type}, label={field.label})")


async def recreate_trunk():
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # First, delete the old trunk
        print("Deleting old trunk ST_NvMu6L8DwHAq...")
        try:
            await lk.sip.delete_sip_trunk(
                sip_proto.DeleteSIPTrunkRequest(sip_trunk_id="ST_NvMu6L8DwHAq")
            )
            print("  Deleted.")
        except Exception as e:
            print(f"  Delete failed (may not exist): {e}")

        # Recreate with headers
        print("\nCreating new trunk with X-Telnyx-Username header...")
        trunk = await lk.sip.create_sip_outbound_trunk(
            sip_proto.CreateSIPOutboundTrunkRequest(
                trunk=sip_proto.SIPOutboundTrunkInfo(
                    name="Telnyx EZWAI AIME Outbound",
                    address="sip.telnyx.com",
                    numbers=["+12392169696"],
                    auth_username="userjoemachado6245765",
                    auth_password="mRv1$y^_Rq+S",
                    headers={
                        "X-Telnyx-Username": "userjoemachado6245765",
                    },
                    headers_to_attributes={
                        "X-Telnyx-Username": "telnyx.username",
                    },
                )
            )
        )
        print(f"  New trunk created!")
        print(f"  Trunk ID: {trunk.sip_trunk_id}")
        print(f"  Address: {trunk.address}")
        print(f"  Numbers: {trunk.numbers}")
        print(f"  Headers: {trunk.headers}")
        print(f"  Full proto: {trunk}")
        print(f"\n  Update .env:")
        print(f"  LIVEKIT_SIP_OUTBOUND_TRUNK_ID={trunk.sip_trunk_id}")
        print(f"  LIVEKIT_SIP_TRUNK_ID={trunk.sip_trunk_id}")
        return trunk.sip_trunk_id

    finally:
        await lk.aclose()


if __name__ == "__main__":
    print("=== Inspecting trunk fields ===")
    asyncio.run(inspect_trunk_fields())
    print("\n=== Recreating trunk ===")
    asyncio.run(recreate_trunk())
