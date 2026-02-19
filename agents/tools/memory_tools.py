"""
Memory Tools for LiveKit Agent
Retrieves contact context from AIME Bridge API
"""

import logging
import httpx
from typing import Dict, Optional

logger = logging.getLogger("aime-voice-agent.memory-tools")


class MemoryTools:
    """Tools for accessing unified contact memory via AIME Bridge API"""

    def __init__(self, bridge_url: str):
        self.base_url = bridge_url

    async def get_contact_context(
        self, contact_id: Optional[str]
    ) -> Optional[Dict]:
        """Get contact context from unified memory"""
        if not contact_id:
            return None

        url = f"{self.base_url}/api/bridge/memory/context/{contact_id}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Contact context loaded for {contact_id}")
                    return data
                else:
                    logger.warning(f"Memory context failed: HTTP {response.status_code} from {url}")
        except httpx.ConnectError:
            logger.error(f"BRIDGE NOT REACHABLE at {url} - is AIME Server running on port 3000?")
        except Exception as e:
            logger.error(f"Failed to get contact context: {e}")

        return None

    async def add_interaction(
        self,
        contact_id: str,
        channel: str,
        summary: str,
        full_content: str,
    ) -> bool:
        """Add interaction to contact memory"""
        url = f"{self.base_url}/api/bridge/memory/interaction"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "contact_id": contact_id,
                        "channel": channel,
                        "summary": summary,
                        "full_content": full_content,
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return True
                logger.warning(f"Add interaction failed: HTTP {response.status_code} from {url}")
                return False
        except httpx.ConnectError:
            logger.error(f"BRIDGE NOT REACHABLE at {url} - is AIME Server running on port 3000?")
            return False
        except Exception as e:
            logger.error(f"Add interaction error: {e}")
            return False
