"""
Telnyx SIP Configuration Diagnostic
Inspects FQDN connections, FQDNs, phone number assignments,
and credential connections to diagnose inbound call routing issues.
"""

import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

# Load .env from project root (one level up from agents/)
env_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))
load_dotenv(env_path)

API_KEY = os.getenv("TELNYX_API_KEY")
BASE = "https://api.telnyx.com/v2"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
}


async def fetch(client: httpx.AsyncClient, path: str, label: str):
    """Fetch a Telnyx API endpoint and print results."""
    url = f"{BASE}{path}"
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  GET {url}")
    print(f"{'='*60}")
    try:
        resp = await client.get(url, headers=HEADERS, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"  ERROR {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return None


async def main():
    if not API_KEY:
        print("ERROR: TELNYX_API_KEY not set in .env")
        print("Get your API key from: Telnyx Portal -> Auth -> Auth V2")
        sys.exit(1)

    print("Telnyx SIP Configuration Diagnostic")
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")

    async with httpx.AsyncClient() as client:
        # 1. List all FQDN connections
        fqdn_conns = await fetch(client, "/fqdn_connections", "FQDN CONNECTIONS")

        # 2. List all FQDNs
        fqdns = await fetch(client, "/fqdns", "FQDNs (Domain entries)")

        # 3. List all credential connections
        cred_conns = await fetch(
            client, "/credential_connections", "CREDENTIAL CONNECTIONS"
        )

        # 4. List phone numbers (filter to our numbers)
        phones = await fetch(
            client,
            "/phone_numbers?filter[phone_number]=+12392169696",
            "PHONE NUMBER: +12392169696",
        )

        phones2 = await fetch(
            client,
            "/phone_numbers?filter[phone_number]=+13059521569",
            "PHONE NUMBER: +13059521569",
        )

        # 5. List all connections (generic)
        conns = await fetch(client, "/connections", "ALL CONNECTIONS")

        # Summary
        print(f"\n{'='*60}")
        print("  DIAGNOSTIC SUMMARY")
        print(f"{'='*60}")

        if fqdn_conns and "data" in fqdn_conns:
            for conn in fqdn_conns["data"]:
                print(f"\n  FQDN Connection: {conn.get('record_type', 'unknown')}")
                print(f"    ID: {conn.get('id')}")
                print(f"    Name: {conn.get('connection_name')}")
                print(f"    Active: {conn.get('active')}")
                print(f"    Inbound: {json.dumps(conn.get('inbound', {}), indent=6)}")
                print(f"    Outbound: {json.dumps(conn.get('outbound', {}), indent=6)}")

        if fqdns and "data" in fqdns:
            for fqdn in fqdns["data"]:
                print(f"\n  FQDN Entry:")
                print(f"    ID: {fqdn.get('id')}")
                print(f"    FQDN: {fqdn.get('fqdn')}")
                print(f"    Port: {fqdn.get('port')}")
                print(f"    DNS Type: {fqdn.get('dns_record_type')}")
                print(f"    Connection ID: {fqdn.get('connection_id')}")

        if phones and "data" in phones:
            for pn in phones["data"]:
                print(f"\n  Phone +12392169696:")
                print(f"    ID: {pn.get('id')}")
                print(f"    Connection ID: {pn.get('connection_id')}")
                print(f"    Connection Name: {pn.get('connection_name')}")
                print(f"    Status: {pn.get('status')}")

        if phones2 and "data" in phones2:
            for pn in phones2["data"]:
                print(f"\n  Phone +13059521569:")
                print(f"    ID: {pn.get('id')}")
                print(f"    Connection ID: {pn.get('connection_id')}")
                print(f"    Connection Name: {pn.get('connection_name')}")
                print(f"    Status: {pn.get('status')}")

        # Check for issues
        print(f"\n{'='*60}")
        print("  POTENTIAL ISSUES")
        print(f"{'='*60}")

        if fqdn_conns and "data" in fqdn_conns:
            for conn in fqdn_conns["data"]:
                inbound = conn.get("inbound", {})
                if not inbound:
                    print(f"  [!] FQDN connection '{conn.get('connection_name')}' has no inbound config")

        if fqdns and "data" in fqdns:
            livekit_fqdns = [
                f for f in fqdns["data"] if "livekit" in (f.get("fqdn") or "").lower()
            ]
            if not livekit_fqdns:
                print("  [!] No FQDN entry pointing to LiveKit (*.sip.livekit.cloud)")
            else:
                for f in livekit_fqdns:
                    print(f"  [OK] LiveKit FQDN found: {f.get('fqdn')}:{f.get('port')}")
                    if not f.get("connection_id"):
                        print(
                            "    [!] NOT associated with any connection!"
                        )
        else:
            print("  [!] Could not retrieve FQDNs")

        if phones and "data" in phones:
            for pn in phones["data"]:
                conn_id = pn.get("connection_id")
                conn_name = pn.get("connection_name")
                if not conn_id:
                    print(f"  [!] +12392169696 is NOT assigned to any connection!")
                else:
                    print(f"  [OK] +12392169696 assigned to: {conn_name} (ID: {conn_id})")
                    # Check if it's the FQDN connection
                    if fqdn_conns and "data" in fqdn_conns:
                        fqdn_conn_ids = [c.get("id") for c in fqdn_conns["data"]]
                        if conn_id in fqdn_conn_ids:
                            print(f"    [OK] This is an FQDN connection (correct for inbound)")
                        else:
                            print(f"    [!] This is NOT an FQDN connection -- inbound calls may not route correctly")


if __name__ == "__main__":
    asyncio.run(main())
