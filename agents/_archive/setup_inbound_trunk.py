"""
Create inbound SIP trunk for Telnyx number and update dispatch rule.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.protocol import sip as sip_proto


async def setup_inbound():
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # Step 1: Create inbound trunk for Telnyx number
        print("=== Creating Inbound SIP Trunk for Telnyx ===")
        trunk = await lk.sip.create_sip_inbound_trunk(
            sip_proto.CreateSIPInboundTrunkRequest(
                trunk=sip_proto.SIPInboundTrunkInfo(
                    name="Telnyx Inbound (+12392169696)",
                    numbers=["+12392169696"],
                    headers_to_attributes={
                        "X-Telnyx-Username": "telnyx.username",
                    },
                )
            )
        )
        new_inbound_id = trunk.sip_trunk_id
        print(f"  Created: {new_inbound_id}")
        print(f"  Name: {trunk.name}")
        print(f"  Numbers: {trunk.numbers}")

        # Step 2: Delete old dispatch rule
        print("\n=== Updating Dispatch Rule ===")
        old_rule_id = "SDR_78mm5Pv5aNuj"
        print(f"  Deleting old rule: {old_rule_id}")
        try:
            await lk.sip.delete_sip_dispatch_rule(
                sip_proto.DeleteSIPDispatchRuleRequest(
                    sip_dispatch_rule_id=old_rule_id
                )
            )
            print("  Deleted.")
        except Exception as e:
            print(f"  Delete failed: {e}")

        # Step 3: Create new dispatch rule with updated trunk IDs
        outbound_trunk = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID", "ST_HKShXodgQbj9")
        trunk_ids = [new_inbound_id, outbound_trunk]

        new_rule = await lk.sip.create_sip_dispatch_rule(
            sip_proto.CreateSIPDispatchRuleRequest(
                rule=sip_proto.SIPDispatchRule(
                    dispatch_rule_individual=sip_proto.SIPDispatchRuleIndividual(
                        room_prefix="aime-",
                    )
                ),
                trunk_ids=trunk_ids,
                name="AIME Voice Agent",
            )
        )
        print(f"  New rule: {new_rule.sip_dispatch_rule_id}")
        print(f"  Trunk IDs: {trunk_ids}")

        # Summary
        print("\n=== Update .env with: ===")
        print(f"LIVEKIT_SIP_INBOUND_TRUNK_ID={new_inbound_id}")
        print(f"LIVEKIT_INBOUND_PHONE_NUMBER=+12392169696")

        return new_inbound_id

    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(setup_inbound())
