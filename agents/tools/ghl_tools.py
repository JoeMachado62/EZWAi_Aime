"""
GHL Tools for LiveKit Agent
Direct GHL API integration with AIME Bridge fallback.
"""

import logging
import os
import httpx
from typing import Dict, List, Optional

logger = logging.getLogger("aime-voice-agent.ghl-tools")

# GHL API base URL
GHL_API_BASE = "https://services.leadconnectorhq.com"


class GHLTools:
    """Tools for interacting with GHL (direct API + bridge fallback)"""

    def __init__(self, bridge_url: str):
        self.base_url = bridge_url
        self.ghl_pit_token = os.getenv("GHL_PIT_TOKEN")
        self.ghl_location_id = os.getenv("GHL_LOCATION_ID")
        self._headers = {
            "Authorization": f"Bearer {self.ghl_pit_token}",
            "Version": "2021-07-28",
        } if self.ghl_pit_token else {}
        logger.info(
            f"GHL Tools initialized: bridge={bridge_url}, "
            f"direct_api={'available' if self.ghl_pit_token else 'NOT configured'}"
        )

    # ── Contact Lookup ──────────────────────────────────────────────

    async def lookup_contact_by_phone(
        self, location_id: Optional[str], phone: str
    ) -> Optional[Dict]:
        """Lookup contact by phone number via direct GHL API"""
        if not self.ghl_pit_token:
            logger.warning("No GHL_PIT_TOKEN configured")
            return None

        loc_id = location_id or self.ghl_location_id
        clean_phone = "".join(c for c in phone if c.isdigit())

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{GHL_API_BASE}/contacts/",
                    headers=self._headers,
                    params={"locationId": loc_id, "query": clean_phone, "limit": "1"},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    contacts = resp.json().get("contacts", [])
                    if contacts:
                        contact = contacts[0]
                        logger.info(f"Contact found: {contact.get('contactName', 'unknown')} (id={contact.get('id')})")
                        return contact
                    else:
                        logger.info(f"No contact found for {clean_phone}")
                        return None
                else:
                    logger.warning(f"Contact lookup HTTP {resp.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Contact lookup error: {e}")
            return None

    # ── Full Contact Context ────────────────────────────────────────

    async def get_full_contact_context(
        self, location_id: str, contact_id: str
    ) -> Dict:
        """Fetch full GHL context: contact details, notes, conversations, tasks, appointments"""
        if not self.ghl_pit_token:
            return {}

        loc_id = location_id or self.ghl_location_id
        context = {}

        try:
            async with httpx.AsyncClient() as client:
                # 1. Full contact details
                r = await client.get(
                    f"{GHL_API_BASE}/contacts/{contact_id}",
                    headers=self._headers, timeout=10.0,
                )
                if r.status_code == 200:
                    c = r.json().get("contact", {})
                    context["contact"] = {
                        "name": c.get("contactName") or c.get("firstName", ""),
                        "email": c.get("email"),
                        "phone": c.get("phone"),
                        "tags": c.get("tags", []),
                        "source": c.get("source"),
                        "dateAdded": c.get("dateAdded"),
                    }

                # 2. Notes (most recent 5)
                r2 = await client.get(
                    f"{GHL_API_BASE}/contacts/{contact_id}/notes",
                    headers=self._headers, timeout=10.0,
                )
                if r2.status_code == 200:
                    notes = r2.json().get("notes", [])
                    context["notes"] = [
                        {"body": n.get("body", "")[:300], "dateAdded": n.get("dateAdded")}
                        for n in notes[:5]
                    ]
                    logger.info(f"Loaded {len(notes)} notes for contact {contact_id}")

                # 3. Recent conversations / messages
                r3 = await client.get(
                    f"{GHL_API_BASE}/conversations/search",
                    headers=self._headers,
                    params={"locationId": loc_id, "contactId": contact_id},
                    timeout=10.0,
                )
                if r3.status_code == 200:
                    convos = r3.json().get("conversations", [])
                    if convos:
                        conv_id = convos[0].get("id")
                        # Fetch last messages
                        r4 = await client.get(
                            f"{GHL_API_BASE}/conversations/{conv_id}/messages",
                            headers=self._headers, timeout=10.0,
                        )
                        if r4.status_code == 200:
                            raw = r4.json().get("messages", {})
                            msgs = raw if isinstance(raw, list) else raw.get("messages", [])
                            context["conversations"] = [
                                {
                                    "direction": m.get("direction", "unknown"),
                                    "body": str(m.get("body", ""))[:200],
                                    "dateAdded": m.get("dateAdded"),
                                }
                                for m in msgs[:10]
                            ]
                            logger.info(f"Loaded {len(msgs)} messages for contact {contact_id}")

                # 4. Tasks
                r5 = await client.get(
                    f"{GHL_API_BASE}/contacts/{contact_id}/tasks",
                    headers=self._headers, timeout=10.0,
                )
                if r5.status_code == 200:
                    tasks = r5.json().get("tasks", [])
                    context["tasks"] = [
                        {"title": t.get("title"), "status": t.get("status"), "dueDate": t.get("dueDate")}
                        for t in tasks[:5]
                    ]

                # 5. Appointments
                r6 = await client.get(
                    f"{GHL_API_BASE}/contacts/{contact_id}/appointments",
                    headers=self._headers, timeout=10.0,
                )
                if r6.status_code == 200:
                    appts = r6.json().get("events", r6.json().get("appointments", []))
                    if isinstance(appts, list):
                        context["appointments"] = [
                            {"title": a.get("title"), "startTime": a.get("startTime"), "status": a.get("status")}
                            for a in appts[:5]
                        ]

        except Exception as e:
            logger.error(f"Failed to fetch full GHL context: {e}")

        return context

    # ── Write Operations ────────────────────────────────────────────

    async def add_contact_note(self, contact_id: str, body: str) -> bool:
        """Add a note to a GHL contact"""
        if not self.ghl_pit_token:
            logger.warning("No GHL_PIT_TOKEN - cannot add note")
            return False

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GHL_API_BASE}/contacts/{contact_id}/notes",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={"body": body},
                    timeout=10.0,
                )
                if resp.status_code in (200, 201):
                    logger.info(f"Note added to contact {contact_id}")
                    return True
                else:
                    logger.warning(f"Add note failed: HTTP {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Add note error: {e}")
            return False

    async def update_contact(self, contact_id: str, data: Dict) -> bool:
        """Update a GHL contact's fields (name, email, tags, etc.)"""
        if not self.ghl_pit_token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{GHL_API_BASE}/contacts/{contact_id}",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json=data,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    logger.info(f"Contact {contact_id} updated")
                    return True
                else:
                    logger.warning(f"Update contact failed: HTTP {resp.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Update contact error: {e}")
            return False

    # ── Calendar Operations (direct GHL API) ───────────────────────

    async def list_calendars(self, location_id: Optional[str] = None) -> List[Dict]:
        """List all calendars in the location"""
        if not self.ghl_pit_token:
            return []
        loc_id = location_id or self.ghl_location_id
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{GHL_API_BASE}/calendars/",
                    headers=self._headers,
                    params={"locationId": loc_id},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    cals = resp.json().get("calendars", [])
                    return [{"id": c["id"], "name": c.get("name"), "type": c.get("calendarType"),
                             "slotDuration": c.get("slotDuration")} for c in cals]
                logger.warning(f"List calendars HTTP {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"List calendars error: {e}")
            return []

    async def get_free_slots(
        self, calendar_id: str, start_date: str, end_date: str,
        timezone: str = "America/New_York",
    ) -> Dict:
        """Get free appointment slots. Dates as YYYY-MM-DD strings."""
        if not self.ghl_pit_token:
            return {}
        try:
            from datetime import datetime
            # Convert YYYY-MM-DD to epoch ms
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            start_ms = str(int(start_dt.timestamp() * 1000))
            end_ms = str(int(end_dt.timestamp() * 1000))

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{GHL_API_BASE}/calendars/{calendar_id}/free-slots",
                    headers=self._headers,
                    params={"startDate": start_ms, "endDate": end_ms, "timezone": timezone},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    data.pop("traceId", None)
                    return data
                logger.warning(f"Free slots HTTP {resp.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Free slots error: {e}")
            return {}

    async def create_appointment(
        self, calendar_id: str, contact_id: str,
        start_time: str, end_time: str,
        title: str = "Appointment",
        location_id: Optional[str] = None,
        status: str = "confirmed",
    ) -> Dict:
        """Create an appointment. Times as ISO 8601 strings."""
        if not self.ghl_pit_token:
            return {"success": False, "error": "No GHL token"}
        loc_id = location_id or self.ghl_location_id
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GHL_API_BASE}/calendars/events/appointments",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={
                        "calendarId": calendar_id,
                        "locationId": loc_id,
                        "contactId": contact_id,
                        "startTime": start_time,
                        "endTime": end_time,
                        "title": title,
                        "appointmentStatus": status,
                        "toNotify": True,
                    },
                    timeout=15.0,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    logger.info(f"Appointment created: {data.get('id')}")
                    return {"success": True, "id": data.get("id"), **data}
                else:
                    logger.warning(f"Create appointment HTTP {resp.status_code}: {resp.text[:200]}")
                    return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.error(f"Create appointment error: {e}")
            return {"success": False, "error": str(e)}

    # ── Contact Creation ─────────────────────────────────────────

    async def upsert_contact(
        self, phone: str,
        first_name: str = "", last_name: str = "",
        email: str = "", source: str = "voice-agent",
        tags: Optional[List[str]] = None,
        location_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create or update a contact by phone (upsert prevents duplicates)"""
        if not self.ghl_pit_token:
            return None
        loc_id = location_id or self.ghl_location_id
        body: Dict = {"locationId": loc_id, "phone": phone, "source": source}
        if first_name:
            body["firstName"] = first_name
        if last_name:
            body["lastName"] = last_name
        if email:
            body["email"] = email
        if tags:
            body["tags"] = tags
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GHL_API_BASE}/contacts/upsert",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json=body,
                    timeout=10.0,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    contact = data.get("contact", {})
                    is_new = data.get("new", False)
                    logger.info(f"Contact upsert: {'created' if is_new else 'updated'} {contact.get('id')}")
                    return contact
                else:
                    logger.warning(f"Upsert contact HTTP {resp.status_code}: {resp.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Upsert contact error: {e}")
            return None

    # ── Task Creation (direct GHL API) ───────────────────────────

    async def create_task(
        self, contact_id: str, title: str, body: str, due_date: Optional[str] = None,
    ) -> Dict:
        """Create a task on a contact"""
        if not self.ghl_pit_token:
            return {"error": "No GHL token"}
        try:
            payload: Dict = {"title": title, "body": body, "completed": False}
            if due_date:
                payload["dueDate"] = due_date
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GHL_API_BASE}/contacts/{contact_id}/tasks",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0,
                )
                if resp.status_code in (200, 201):
                    return {"success": True, **resp.json()}
                logger.warning(f"Create task HTTP {resp.status_code}")
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            logger.error(f"Create task error: {e}")
            return {"error": str(e)}
