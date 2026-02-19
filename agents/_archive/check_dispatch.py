"""Check existing SIP dispatch rules and trunks"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.protocol import sip as sip_proto


async def check_config():
    livekit_url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    lk = api.LiveKitAPI(livekit_url, api_key, api_secret)

    try:
        # List dispatch rules
        rules = await lk.sip.list_sip_dispatch_rule(
            sip_proto.ListSIPDispatchRuleRequest()
        )
        print("=== Dispatch Rules ===")
        for r in rules.items:
            print(f"  ID: {r.sip_dispatch_rule_id}")
            print(f"  Name: {r.name}")
            print(f"  Trunk IDs: {r.trunk_ids}")
            print(f"  Rule: {r.rule}")
            print()

        # List outbound trunks
        outbound = await lk.sip.list_sip_outbound_trunk(
            sip_proto.ListSIPOutboundTrunkRequest()
        )
        print("=== Outbound Trunks ===")
        for t in outbound.items:
            print(f"  ID: {t.sip_trunk_id}")
            print(f"  Name: {t.name}")
            print(f"  Address: {t.address}")
            print(f"  Numbers: {t.numbers}")
            print()

        # List inbound trunks
        inbound = await lk.sip.list_sip_inbound_trunk(
            sip_proto.ListSIPInboundTrunkRequest()
        )
        print("=== Inbound Trunks ===")
        for t in inbound.items:
            print(f"  ID: {t.sip_trunk_id}")
            print(f"  Name: {t.name}")
            print(f"  Numbers: {t.numbers}")
            print()

    finally:
        await lk.aclose()


if __name__ == "__main__":
    asyncio.run(check_config())
