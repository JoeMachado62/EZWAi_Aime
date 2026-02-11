"""
Memory Tools for LiveKit Agent
Retrieves contact context from unified memory
"""

import httpx
from typing import Dict, Optional


class MemoryTools:
    """Tools for accessing unified contact memory"""

    def __init__(self, openclaw_base_url: str):
        self.base_url = openclaw_base_url

    async def get_contact_context(
        self, contact_id: Optional[str]
    ) -> Optional[Dict]:
        """Get contact context from unified memory"""
        if not contact_id:
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/bridge/memory/context/{contact_id}",
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"Failed to get contact context: {e}")

        return None

    async def add_interaction(
        self,
        contact_id: str,
        channel: str,
        summary: str,
        full_content: str,
    ) -> bool:
        """Add interaction to contact memory"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/bridge/memory/interaction",
                    json={
                        "contact_id": contact_id,
                        "channel": channel,
                        "summary": summary,
                        "full_content": full_content,
                    },
                    timeout=10.0,
                )
                return response.status_code == 200
            except Exception:
                return False
