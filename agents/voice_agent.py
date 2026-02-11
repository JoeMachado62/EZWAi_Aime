"""
AIME Voice Agent
LiveKit-based voice AI agent with GHL integration
"""

import asyncio
import logging
import os
from typing import Annotated

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, cartesia
import httpx

from tools.ghl_tools import GHLTools
from tools.memory_tools import MemoryTools

logger = logging.getLogger("aime-voice-agent")
logger.setLevel(logging.INFO)


class AIMEVoiceAgent:
    """AIME Voice Agent with GHL and memory integration"""

    def __init__(self):
        self.openclaw_base_url = os.getenv("OPENCLAW_BASE_URL", "http://localhost:3000")
        self.ghl_tools = GHLTools(self.openclaw_base_url)
        self.memory_tools = MemoryTools(self.openclaw_base_url)

    async def entry_point(self, ctx: JobContext):
        """Main entry point for voice agent"""
        logger.info(f"Voice agent starting for room: {ctx.room.name}")

        # Extract contact info from room metadata
        contact_info = await self._extract_contact_info(ctx)

        # Load contact context from unified memory
        contact_context = await self.memory_tools.get_contact_context(
            contact_info.get("contact_id")
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(contact_info, contact_context)

        # Create agent session
        session = AgentSession(
            stt=deepgram.STT(model="nova-2-general"),
            llm=openai.LLM(model="gpt-4o-mini"),  # T1 default
            tts=cartesia.TTS(voice="79a125e8-cd45-4c13-8a67-188112f4dd22"),  # Professional voice
        )

        # Start agent with tools
        await session.start(
            agent=Agent(
                instructions=system_prompt,
                tools=[
                    self._check_availability,
                    self._book_appointment,
                    self._lookup_contact,
                    self._transfer_to_human,
                ],
            )
        )

        # Proactively greet (required for telephony)
        greeting = self._generate_greeting(contact_info, contact_context)
        await session.generate_reply(instructions=greeting)

        # Wait for session to end
        await session.wait_for_completion()

        # Post-call processing
        await self._post_call_processing(ctx, session, contact_info)

        logger.info(f"Voice agent completed for room: {ctx.room.name}")

    async def _extract_contact_info(self, ctx: JobContext) -> dict:
        """Extract contact information from room metadata or SIP participant"""
        import json

        metadata = json.loads(ctx.room.metadata or "{}")

        # Try to get phone number from metadata or SIP participant
        phone = metadata.get("caller", {}).get("phone")

        # If no phone in metadata, try to extract from SIP participant
        if not phone:
            for participant in ctx.room.remote_participants.values():
                if participant.identity.startswith("sip_"):
                    phone = participant.identity.replace("sip_", "")
                    break

        contact_info = {
            "phone": phone,
            "contact_id": metadata.get("caller", {}).get("contact_id"),
            "location_id": metadata.get("business_id"),
        }

        # If we have phone but no contact_id, try to look it up
        if phone and not contact_info["contact_id"]:
            try:
                contact = await self.ghl_tools.lookup_contact_by_phone(
                    contact_info["location_id"], phone
                )
                if contact:
                    contact_info["contact_id"] = contact.get("id")
                    contact_info["name"] = contact.get("contactName")
            except Exception as e:
                logger.error(f"Failed to lookup contact: {e}")

        return contact_info

    def _build_system_prompt(self, contact_info: dict, contact_context: dict | None) -> str:
        """Build system prompt with contact context"""
        prompt = """You are AIME, an AI assistant for [Business Name].

You are professional, friendly, and helpful. Your goal is to:
1. Answer questions about services and pricing
2. Schedule appointments
3. Help with customer inquiries
4. Transfer to a human when needed

Guidelines:
- Keep responses concise and conversational
- Use the caller's name when you know it
- Reference their history naturally
- Always confirm important details before booking
- Offer to transfer to a human if the request is complex
"""

        if contact_context:
            prompt += f"\n\n# Contact Context\n\n{contact_context.get('summary', '')}\n"

            if contact_context.get("recent_interactions"):
                prompt += "\n## Recent History\n"
                for interaction in contact_context["recent_interactions"][:3]:
                    prompt += f"- {interaction}\n"

            if contact_context.get("key_facts"):
                prompt += "\n## Key Facts to Remember\n"
                for fact in contact_context["key_facts"][:3]:
                    prompt += f"- {fact}\n"

            if contact_context.get("recommendations"):
                prompt += "\n## Recommendations for This Call\n"
                for rec in contact_context["recommendations"]:
                    prompt += f"- {rec}\n"

        return prompt

    def _generate_greeting(self, contact_info: dict, contact_context: dict | None) -> str:
        """Generate personalized greeting"""
        name = contact_info.get("name")

        if name and contact_context:
            days_since = contact_context.get("days_since_last_contact", 999)
            if days_since < 7:
                return f"Greet {name} warmly and acknowledge it's good to hear from them again."
            else:
                return f"Greet {name} warmly - it's been a while since you last spoke."
        elif name:
            return f"Greet {name} professionally and ask how you can help them today."
        else:
            return "Greet the caller professionally and ask how you can help them today."

    async def _post_call_processing(
        self, ctx: JobContext, session: AgentSession, contact_info: dict
    ):
        """Process call data after completion"""
        try:
            # Get transcript
            transcript = session.get_transcript()

            # Send to OpenClaw bridge for processing
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.openclaw_base_url}/api/bridge/process-call",
                    json={
                        "contact_id": contact_info.get("contact_id"),
                        "location_id": contact_info.get("location_id"),
                        "phone": contact_info.get("phone"),
                        "transcript": transcript,
                        "duration_seconds": session.duration_seconds,
                        "room_name": ctx.room.name,
                    },
                    timeout=30.0,
                )

            logger.info(f"Post-call processing completed for {contact_info.get('phone')}")

        except Exception as e:
            logger.error(f"Post-call processing failed: {e}")

    @function_tool
    async def _check_availability(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        service_type: Annotated[str, "Type of service"] = "consultation",
    ) -> str:
        """Check available appointment slots"""
        # This will call OpenClaw bridge → GHL API
        try:
            slots = await self.ghl_tools.check_availability(date, service_type)
            if slots:
                return f"Available slots on {date}: {', '.join(slots)}"
            else:
                return f"No availability on {date}. Would you like to try another date?"
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            return "I'm having trouble checking availability right now. Let me transfer you to someone who can help."

    @function_tool
    async def _book_appointment(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM format"],
        name: Annotated[str, "Customer name"],
        phone: Annotated[str, "Customer phone number"],
        service: Annotated[str, "Service type"],
    ) -> str:
        """Book an appointment"""
        try:
            result = await self.ghl_tools.book_appointment(date, time, name, phone, service)
            if result.get("success"):
                return f"Great! I've booked your {service} appointment for {date} at {time}. You'll receive a confirmation shortly."
            else:
                return f"I'm sorry, there was an issue booking that slot. {result.get('error', 'Please try another time.')}"
        except Exception as e:
            logger.error(f"Failed to book appointment: {e}")
            return "I'm having trouble booking that appointment. Let me transfer you to someone who can help."

    @function_tool
    async def _lookup_contact(
        self,
        phone: Annotated[str, "Phone number to lookup"],
    ) -> str:
        """Look up contact information"""
        try:
            contact = await self.ghl_tools.lookup_contact_by_phone(None, phone)
            if contact:
                return f"Found contact: {contact.get('contactName', 'Unknown')}"
            else:
                return "No contact found with that phone number."
        except Exception as e:
            logger.error(f"Failed to lookup contact: {e}")
            return "I'm having trouble looking up that information right now."

    @function_tool
    async def _transfer_to_human(
        self,
        reason: Annotated[str, "Reason for transfer"],
        department: Annotated[str, "Department"] = "support",
    ) -> str:
        """Transfer the call to a human agent"""
        # This would trigger a warm transfer in production
        logger.info(f"Transfer requested: {reason} → {department}")
        return f"I understand you need {reason}. Let me connect you with our {department} team. Please hold for just a moment."


def main():
    """Entry point for running the agent"""
    agent = AIMEVoiceAgent()

    cli.run_app(
        WorkerOptions(
            entry_point_fnc=agent.entry_point,
            agent_name="aime-voice-agent",
        )
    )


if __name__ == "__main__":
    main()
