"""
GHL Tools for LiveKit Agent
Calls OpenClaw bridge to interact with GHL
"""

import httpx
from typing import Dict, List, Optional


class GHLTools:
    """Tools for interacting with GHL via OpenClaw bridge"""

    def __init__(self, openclaw_base_url: str):
        self.base_url = openclaw_base_url

    async def lookup_contact_by_phone(
        self, location_id: Optional[str], phone: str
    ) -> Optional[Dict]:
        """Lookup contact by phone number"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/bridge/contacts/lookup",
                json={"location_id": location_id, "phone": phone},
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None

    async def check_availability(
        self, date: str, service_type: str
    ) -> List[str]:
        """Check available appointment slots"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/bridge/appointments/availability",
                json={"date": date, "service_type": service_type},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("slots", [])
            return []

    async def book_appointment(
        self,
        date: str,
        time: str,
        name: str,
        phone: str,
        service: str,
    ) -> Dict:
        """Book an appointment"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/bridge/appointments/book",
                json={
                    "date": date,
                    "time": time,
                    "name": name,
                    "phone": phone,
                    "service": service,
                },
                timeout=15.0,
            )
            return response.json()

    async def create_task(
        self,
        contact_id: str,
        title: str,
        body: str,
        due_date: Optional[str] = None,
    ) -> Dict:
        """Create a task in GHL"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/bridge/tasks/create",
                json={
                    "contact_id": contact_id,
                    "title": title,
                    "body": body,
                    "due_date": due_date,
                },
                timeout=10.0,
            )
            return response.json()
