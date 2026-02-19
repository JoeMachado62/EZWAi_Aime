"""
AIME Voice Agent
LiveKit-based voice AI agent with GHL integration
"""

import asyncio
import logging
import os
from typing import Annotated
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from livekit import api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    cli,
    function_tool,
    inference,
)
from livekit.plugins import deepgram, openai, elevenlabs, inworld
import httpx

from tools.ghl_tools import GHLTools
from tools.memory_tools import MemoryTools
from tools.sales_tools import SalesTools
from tenant_config import TenantConfig

logger = logging.getLogger("aime-voice-agent")
logger.setLevel(logging.INFO)


class AIMEVoiceAgent:
    """AIME Voice Agent with GHL and memory integration"""

    def __init__(self):
        # AIME Bridge API runs on port 3000 (src/aime-server.ts)
        # OpenClaw gateway runs on port 18789 but does NOT serve /api/bridge/* routes
        self.bridge_url = os.getenv("AIME_BRIDGE_URL", "http://localhost:3000")
        self.openclaw_base_url = os.getenv("OPENCLAW_BASE_URL", "http://localhost:18789")
        self.tts_provider = os.getenv("TTS_PROVIDER", "inworld")  # Default to Inworld (cost-effective)
        self.ghl_tools = GHLTools(self.bridge_url)
        self.memory_tools = MemoryTools(self.bridge_url)
        self.sales_tools = SalesTools(self.bridge_url)
        self.tenant_config = TenantConfig()
        self._current_location_id = None  # Set per-call for tool access
        self._current_contact_id = None
        self._current_phone = None
        self._calendars = []  # Loaded per-call from GHL

    def _get_tts_provider(self, tenant: dict | None = None):
        """Get TTS provider based on tenant config, falling back to env var"""
        provider = (tenant or {}).get("tts_provider") or self.tts_provider
        voice = (tenant or {}).get("tts_voice")

        if provider == "elevenlabs":
            el_voice = voice or "Josh"
            logger.info(f"Using ElevenLabs Flash v2.5 TTS (voice: {el_voice})")
            return elevenlabs.TTS(
                model="flash_v2.5",  # 75ms latency, highest quality
                voice=el_voice,
                stability=0.4,  # Lower = more natural variation (0.3-0.5)
                similarity_boost=0.85,  # Higher = closer to source voice (0.8-0.9)
                style=0.6,  # Emotional expressiveness (0.5-0.7 for sales)
                use_speaker_boost=True,  # Enhance clarity
                optimize_streaming_latency=4,  # Max latency optimization (0-4)
            )
        else:
            # Default to Inworld (cost-effective, high-quality)
            iw_voice = voice or "Sarah"
            logger.info(f"Using Inworld TTS 1.5 (voice: {iw_voice})")
            return inworld.TTS(
                model="inworld-tts-1.5-max",  # Max quality model (<200ms P50 latency)
                voice=iw_voice,
                temperature=1.0,  # Natural variation
                speaking_rate=1.0,  # Normal speed
                text_normalization="ON",  # Proper formatting
            )

    async def entry_point(self, ctx: JobContext):
        """Main entry point for voice agent"""
        logger.info(f"Voice agent starting for room: {ctx.room.name}")

        # Connect to the room first (required before any room operations)
        await ctx.connect()

        # Extract contact info from room metadata
        contact_info = await self._extract_contact_info(ctx)

        # Store location_id and contact_id for tool access
        self._current_location_id = contact_info.get("location_id")
        self._current_contact_id = contact_info.get("contact_id")
        self._current_phone = contact_info.get("phone")

        is_outbound = contact_info.get('direction') == 'outbound'
        phone_number = contact_info.get("phone_number") or contact_info.get("phone")

        # Load available calendars for this location
        try:
            self._calendars = await self.ghl_tools.list_calendars(self._current_location_id)
            logger.info(f"Loaded {len(self._calendars)} calendars")
        except Exception as e:
            logger.error(f"Failed to load calendars: {e}")
            self._calendars = []

        # GHL context is already loaded in _extract_contact_info() via direct API
        contact_context = contact_info.get("ghl_context") or None

        # Build system prompt with context
        system_prompt = self._build_system_prompt(contact_info, contact_context)

        # Create agent session with per-tenant TTS
        tenant = contact_info.get("tenant", {})
        session = AgentSession(
            stt=inference.STT(
                model="deepgram/nova-3-general",
                language="multi",
            ),
            llm=inference.LLM(
                model="openai/gpt-5.2-chat-latest",
            ),
            tts=self._get_tts_provider(tenant),
        )

        # Core tools available to all calls
        core_tools = [
            self._check_availability,
            self._book_appointment,
            self._create_contact,
            self._lookup_contact,
            self._add_note,
            self._transfer_to_human,
        ]

        if is_outbound:
            tools = [
                self.sales_tools.qualify_lead,
                self.sales_tools.handle_objection,
                self.sales_tools.schedule_follow_up,
                self.sales_tools.log_sales_activity,
            ] + core_tools
        else:
            tools = core_tools

        # Register post-call processing via shutdown callback
        async def _on_shutdown():
            await self._post_call_processing(ctx, session, contact_info)
        ctx.add_shutdown_callback(_on_shutdown)

        # Start agent session — connects to room audio pipeline
        await session.start(
            agent=Agent(
                instructions=system_prompt,
                tools=tools,
            ),
            room=ctx.room,
        )

        # For outbound calls, agent places the SIP call AFTER connecting to room
        if is_outbound and phone_number:
            outbound_trunk_id = os.environ.get("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")
            livekit_url = os.environ.get("LIVEKIT_URL")
            lk_api_key = os.environ.get("LIVEKIT_API_KEY")
            lk_api_secret = os.environ.get("LIVEKIT_API_SECRET")

            if not outbound_trunk_id or not livekit_url:
                logger.error("LIVEKIT_SIP_OUTBOUND_TRUNK_ID or LIVEKIT_URL not set")
                ctx.shutdown()
                return

            logger.info(f"Outbound: dialing {phone_number} via trunk {outbound_trunk_id}")
            try:
                from livekit.protocol import sip as sip_proto

                # Use direct API client (ctx.api may lack SIP trunk access)
                lk = api.LiveKitAPI(livekit_url, lk_api_key, lk_api_secret)
                try:
                    sip_response = await lk.sip.create_sip_participant(
                        sip_proto.CreateSIPParticipantRequest(
                            sip_trunk_id=outbound_trunk_id,
                            sip_call_to=phone_number,
                            room_name=ctx.room.name,
                            participant_identity=f"sip-phone-{contact_info.get('contact_name', 'caller')}",
                            participant_name=contact_info.get("contact_name") or "Caller",
                            wait_until_answered=True,
                        )
                    )
                    logger.info(f"Call to {phone_number} answered! ID: {sip_response.sip_call_id}")
                finally:
                    await lk.aclose()
            except Exception as e:
                logger.error(f"SIP call failed: {e}")
                import traceback
                traceback.print_exc()
                ctx.shutdown()
                return

            # For custom prompts, let the LLM deliver the message
            if contact_info.get("custom_prompt"):
                await session.generate_reply()
        elif not is_outbound:
            # For inbound, trigger LLM to generate a natural greeting
            # (generate_reply sends through LLM; say() would speak text literally)
            await session.generate_reply()

        logger.info(f"Voice agent running for room: {ctx.room.name}")

    async def _extract_contact_info(self, ctx: JobContext) -> dict:
        """Extract contact information from room metadata or SIP participant"""
        import json

        metadata = json.loads(ctx.room.metadata or "{}")

        # Try to get phone number from metadata or SIP participant
        phone = metadata.get("caller", {}).get("phone") or metadata.get("phone_number")
        called_number = None  # The number that was dialed (for tenant routing)

        # If no phone in metadata, wait for SIP participant to join then extract
        if not phone:
            # For inbound calls, the SIP participant may not have joined yet.
            # Wait up to 10 seconds for them to appear.
            for attempt in range(20):
                for participant in ctx.room.remote_participants.values():
                    attrs = getattr(participant, "attributes", {}) or {}
                    # LiveKit SIP attributes: sip.phoneNumber = caller, sip.trunkPhoneNumber = called
                    if "sip.phoneNumber" in attrs:
                        phone = attrs.get("sip.phoneNumber")
                        called_number = attrs.get("sip.trunkPhoneNumber")
                        logger.info(f"SIP attrs: caller={phone}, called={called_number}")
                        break
                    # Fallback: extract from identity
                    if participant.identity.startswith("sip_"):
                        phone = participant.identity.replace("sip_", "")
                        break
                if phone:
                    break
                if attempt < 19:
                    await asyncio.sleep(0.5)

        # Resolve location_id: use metadata if present (outbound), else tenant config (inbound)
        direction = metadata.get("direction", "inbound")
        location_id_from_metadata = metadata.get("business_id") or metadata.get("location_id")

        if location_id_from_metadata:
            resolved_location_id = location_id_from_metadata
            resolved_business_name = metadata.get("business_name", "Our Business")
            resolved_tenant = metadata.get("tenant", {
                "location_id": resolved_location_id,
                "business_name": resolved_business_name,
            })
        else:
            resolved_tenant = self.tenant_config.resolve(called_number)
            resolved_location_id = resolved_tenant.get("location_id")
            resolved_business_name = resolved_tenant.get("business_name", "Our Business")
            logger.info(
                f"Tenant resolved: {resolved_business_name} "
                f"(location_id={resolved_location_id}, called={called_number})"
            )

        contact_info = {
            "phone": phone,
            "contact_id": metadata.get("caller", {}).get("contact_id") or metadata.get("contact_id"),
            "location_id": resolved_location_id,
            "direction": direction,
            "contact_name": metadata.get("contact_name"),
            "business_name": resolved_business_name,
            "called_number": called_number,
            "tenant": resolved_tenant,
            # AI-initiated call fields
            "custom_prompt": metadata.get("custom_prompt"),
            "ai_instructions": metadata.get("ai_instructions"),
            "notification_phone": metadata.get("notification_phone"),
            "notification_method": metadata.get("notification_method"),
            "user_id": metadata.get("user_id"),
            "user_name": metadata.get("user_name"),
        }

        # Proactive caller identification via GHL
        if phone and not contact_info["contact_id"]:
            try:
                contact = await self.ghl_tools.lookup_contact_by_phone(
                    contact_info["location_id"], phone
                )
                if contact:
                    contact_info["contact_id"] = contact.get("id")
                    contact_info["contact_name"] = contact.get("contactName")
                    contact_info["name"] = contact.get("contactName")
                    contact_info["tags"] = contact.get("tags", [])
                    contact_info["is_new_lead"] = False
                    logger.info(f"Identified caller: {contact.get('contactName')} ({phone})")
                else:
                    contact_info["is_new_lead"] = True
                    logger.info(f"New lead detected: {phone}")
            except Exception as e:
                logger.error(f"Failed to lookup contact: {e}")
                contact_info["is_new_lead"] = True

        # Enrich with full GHL context if we have a contact_id
        if contact_info.get("contact_id") and contact_info.get("location_id"):
            try:
                ghl_context = await self._fetch_full_ghl_context(
                    contact_info["location_id"], contact_info["contact_id"]
                )
                contact_info["ghl_context"] = ghl_context
                logger.info(f"Loaded GHL context for contact {contact_info['contact_id']}")
            except Exception as e:
                logger.error(f"Failed to fetch GHL context: {e}")

        return contact_info

    async def _fetch_full_ghl_context(self, location_id: str, contact_id: str) -> dict:
        """Fetch full GHL context via direct API"""
        return await self.ghl_tools.get_full_contact_context(location_id, contact_id)

    def _load_prompt_file(self, relative_path: str) -> str | None:
        """Load a prompt template file relative to the agents/ directory."""
        agents_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(agents_dir, relative_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {full_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading prompt file {full_path}: {e}")
            return None

    def _build_system_prompt(self, contact_info: dict, contact_context: dict | None) -> str:
        """Build sales-optimized system prompt based on call direction"""

        # Check if there's a custom AI-generated prompt
        if contact_info.get('custom_prompt'):
            logger.info("Using custom AI-generated prompt")
            return contact_info['custom_prompt']

        # Check if outbound or inbound
        is_outbound = contact_info.get('direction') == 'outbound'

        business_name = contact_info.get("business_name", "Our Business")
        tenant = contact_info.get("tenant", {})

        # Global TTS rule: no markdown, no special characters
        tts_rules = """
CRITICAL SPEECH RULES (you are speaking via phone, not writing text):
- NEVER use asterisks, markdown, bullet points, or special formatting
- NEVER use symbols like *, **, #, -, or numbered lists
- Speak in natural conversational sentences only
- Do not say "asterisk" or spell out formatting characters
- Use plain spoken English as if talking to someone face-to-face
"""

        # Try to load tenant-specific prompt file
        prompt_key = "prompt_file_outbound" if is_outbound else "prompt_file_inbound"
        prompt_file = tenant.get(prompt_key)
        prompt = None

        if prompt_file:
            raw = self._load_prompt_file(prompt_file)
            if raw:
                caller_name = (
                    contact_info.get("contact_name")
                    or contact_info.get("name")
                    or "the caller"
                )
                try:
                    prompt = raw.format_map({
                        "business_name": business_name,
                        "caller_name": caller_name,
                        "caller_phone": contact_info.get("phone", "unknown"),
                        "timezone": tenant.get("timezone", "America/New_York"),
                    })
                except KeyError as e:
                    logger.error(f"Prompt template variable missing: {e}, using raw template")
                    prompt = raw
                logger.info(f"Loaded tenant prompt from {prompt_file}")

        # Fallback to hardcoded templates if no prompt file
        if prompt is None:
            if is_outbound:
                prompt = f"""You are an expert sales representative for {business_name}.

Your goal is to:
1. Build rapport quickly and naturally
2. Qualify the prospect's needs and budget using NEPQ techniques
3. Present solutions that address their specific pain points
4. Handle objections with empathy and data-driven insights
5. Move the conversation toward a clear next step (demo, proposal, or follow-up)

IMPORTANT RULES:
- Be conversational and human, never sound scripted or robotic
- Listen actively - ask clarifying questions before pitching
- Mirror the prospect's energy and tone
- Handle "not interested" with grace - ask permission to share one insight before ending
- Never argue or pressure - build trust and credibility instead
- If they're busy, acknowledge it and offer to call back at a better time
- Use their name naturally throughout the conversation
- Focus on their problems, not your product features

TONE: Confident, helpful, consultative (not pushy)

SALES FRAMEWORK (NEPQ):
1. Build rapport with genuine curiosity
2. Uncover problems with open-ended questions
3. Identify budget and timeline
4. Present solution tied to their specific pain points
5. Handle objections by validating concerns, then reframing
6. Close with a clear next step
"""
            else:
                prompt = f"""You are AIME, a friendly AI assistant for {business_name}.

Your goal is to:
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

TONE: Warm, professional, helpful
"""

        # Always append TTS rules regardless of prompt source
        prompt += tts_rules

        # Inject GHL CRM context (loaded directly from GHL API)
        ghl_ctx = contact_info.get("ghl_context", {})

        if ghl_ctx.get("contact"):
            c = ghl_ctx["contact"]
            if c.get("name"):
                prompt += f"\n\nCaller name: {c['name']}"
            if c.get("email"):
                prompt += f"\nEmail: {c['email']}"

        if ghl_ctx.get("notes"):
            prompt += "\n\n## CRM Notes (most recent first)\n"
            for note in ghl_ctx["notes"][:5]:
                body = str(note.get("body", ""))[:300]
                prompt += f"- {body}\n"

        if ghl_ctx.get("conversations"):
            prompt += "\n## Recent Messages\n"
            for msg in ghl_ctx["conversations"][:10]:
                direction = "Customer" if msg.get("direction") == "inbound" else "Agent"
                body = str(msg.get("body", ""))[:200]
                prompt += f"- [{direction}] {body}\n"

        if ghl_ctx.get("tasks"):
            prompt += "\n## Open Tasks\n"
            for task in ghl_ctx["tasks"]:
                prompt += f"- {task.get('title')} (status: {task.get('status', 'N/A')})\n"

        if ghl_ctx.get("appointments"):
            prompt += "\n## Upcoming Appointments\n"
            for apt in ghl_ctx["appointments"]:
                prompt += f"- {apt.get('title')} on {apt.get('startTime', 'TBD')}\n"

        if contact_info.get("tags"):
            prompt += f"\n## Contact Tags: {', '.join(contact_info['tags'])}\n"

        # Available calendars for scheduling
        if self._calendars:
            prompt += "\n\nAVAILABLE CALENDARS FOR SCHEDULING:\n"
            for cal in self._calendars:
                prompt += f"- \"{cal['name']}\" (id: {cal['id']}, {cal.get('slotDuration', 30)} min slots)\n"
            prompt += (
                "\nSCHEDULING WORKFLOW:\n"
                "1. Choose the right calendar based on context (Sales Call for demos, Intro Call for introductions, Onboarding for new clients)\n"
                "2. Use check_availability with the calendar name and date (YYYY-MM-DD)\n"
                "3. Tell the caller the available times in normal speech (e.g. '3:30 PM')\n"
                "4. If caller is new (not in CRM), use create_contact BEFORE booking\n"
                "5. Use book_appointment with the date (YYYY-MM-DD) and time in 24-hour format (e.g. '15:30' for 3:30 PM)\n"
                "IMPORTANT: When booking, the time parameter must be in 24-hour format matching the slot exactly.\n"
                "Example: if the available slot is '3:30 PM (15:30)', book with time='15:30'\n"
            )

        # New lead handling
        if contact_info.get("is_new_lead"):
            prompt += """
NEW CALLER - Lead Capture Priority:
This is a first-time caller not yet in the CRM. Your priorities:
1. Warmly greet and ask how you can help
2. Capture their name and email if possible
3. Understand their needs and qualify the lead
4. Offer to schedule an appointment or follow-up
5. Use create_contact to save them in the CRM when you have their info
"""

        return prompt

    def _generate_greeting(self, contact_info: dict, contact_context: dict | None) -> str:
        """Generate personalized greeting"""
        # For custom prompts (outbound AI-initiated calls), let the LLM handle the greeting
        if contact_info.get("custom_prompt"):
            return "Begin delivering your message now."

        name = contact_info.get("contact_name") or contact_info.get("name")

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
        """Process call data after completion - saves transcript to GHL and notifies OpenClaw"""
        try:
            # Build transcript from chat history (v1.0+ API)
            transcript_lines = []
            for item in session.history.items:
                role = getattr(item, "role", "unknown")
                text = item.text_content if hasattr(item, "text_content") else str(getattr(item, "content", ""))
                if text:
                    transcript_lines.append(f"[{role}] {text}")
            transcript = "\n".join(transcript_lines)

            # Use self._current_contact_id which gets updated if _create_contact
            # is called mid-call (contact_info dict is stale for new leads)
            contact_id = self._current_contact_id or contact_info.get("contact_id")
            phone = contact_info.get("phone", "unknown")
            direction = contact_info.get("direction", "inbound")

            # 1. Save transcript as GHL note (direct API - always works)
            if contact_id and transcript:
                from datetime import datetime
                now = datetime.now().strftime("%b %d, %Y %I:%M %p")
                note_body = (
                    f"--------- AI Voice Call ---------\n"
                    f"Direction: {direction}\n"
                    f"Time: {now}\n"
                    f"Phone: {phone}\n"
                    f"Room: {ctx.room.name}\n\n"
                    f"--- Transcript ---\n{transcript}"
                )
                saved = await self.ghl_tools.add_contact_note(contact_id, note_body)
                if saved:
                    logger.info(f"Call transcript saved to GHL for contact {contact_id}")
                else:
                    logger.warning(f"Failed to save transcript to GHL for {contact_id}")

            # 2. Notify OpenClaw gateway via hooks (port 18789)
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.openclaw_base_url}/hooks/agent",
                        json={
                            "type": "voice_call_completed",
                            "contact_id": contact_id,
                            "phone": phone,
                            "direction": direction,
                            "transcript": transcript[:2000],
                            "room_name": ctx.room.name,
                            "contact_name": contact_info.get("contact_name") or self._current_contact_id,
                        },
                        timeout=10.0,
                    )
                    logger.info("OpenClaw notified of call completion")
            except Exception as e:
                logger.warning(f"Could not notify OpenClaw gateway: {e}")

            logger.info(f"Post-call processing completed for {phone}")

        except Exception as e:
            logger.error(f"Post-call processing failed: {e}")

    def _extract_outcome_from_transcript(self, transcript: str) -> str:
        """Extract key outcome from call transcript"""
        # Simple extraction - get last few agent messages
        # In production, use Claude to summarize
        lines = transcript.split('\n')
        agent_lines = [line for line in lines if line.startswith('Agent:')]

        if agent_lines:
            # Return last 2-3 agent messages as outcome
            return '\n'.join(agent_lines[-3:])

        return "Call completed successfully. See transcript for details."

    @function_tool
    async def _check_availability(
        self,
        calendar_name: Annotated[str, "Calendar name to check (e.g. 'Sales Call', 'Intro Call', 'Onboarding')"],
        date: Annotated[str, "Date in YYYY-MM-DD format"],
    ) -> str:
        """Check available appointment slots on a specific calendar"""
        try:
            # Find calendar by name (case-insensitive partial match)
            cal = None
            for c in self._calendars:
                if calendar_name.lower() in c["name"].lower():
                    cal = c
                    break
            if not cal:
                names = ", ".join(c["name"] for c in self._calendars)
                return f"Calendar '{calendar_name}' not found. Available calendars: {names}"

            slots = await self.ghl_tools.get_free_slots(cal["id"], date, date)
            day_slots = slots.get(date, {}).get("slots", [])
            if day_slots:
                # Format times showing both 12h (for speech) and 24h (for booking tool)
                from datetime import datetime
                formatted = []
                for slot in day_slots:
                    try:
                        dt = datetime.fromisoformat(slot)
                        h12 = dt.strftime("%I:%M %p").lstrip("0")
                        h24 = dt.strftime("%H:%M")
                        formatted.append(f"{h12} ({h24})")
                    except Exception:
                        formatted.append(slot)
                return (
                    f"Available slots on {cal['name']} for {date}: {', '.join(formatted)}. "
                    f"Each slot is {cal.get('slotDuration', 30)} minutes. "
                    f"When booking, use the 24-hour time value (e.g. 15:30 for 3:30 PM)."
                )
            else:
                return f"No availability on {cal['name']} for {date}. Would you like to try another date?"
        except Exception as e:
            logger.error(f"Check availability error: {e}")
            return "I'm having trouble checking availability right now. Let me transfer you to someone who can help."

    @function_tool
    async def _book_appointment(
        self,
        calendar_name: Annotated[str, "Calendar name to book on (e.g. 'Sales Call', 'Intro Call')"],
        date: Annotated[str, "Appointment date in YYYY-MM-DD format (e.g. '2026-02-20')"],
        time: Annotated[str, "Appointment time in HH:MM 24-hour format (e.g. '15:30' for 3:30 PM)"],
        title: Annotated[str, "Appointment title (e.g. 'Sales Demo with John')"] = "Appointment",
    ) -> str:
        """Book an appointment on a calendar. Use 24-hour time format. Requires a contact to be linked to this call."""
        try:
            contact_id = self._current_contact_id
            if not contact_id:
                return "No contact record linked to this call. Please use create_contact first to save the caller, then try booking again."

            # Find calendar
            cal = None
            for c in self._calendars:
                if calendar_name.lower() in c["name"].lower():
                    cal = c
                    break
            if not cal:
                names = ", ".join(c["name"] for c in self._calendars)
                return f"Calendar '{calendar_name}' not found. Available: {names}"

            # Build ISO timestamp with Eastern timezone offset
            from datetime import datetime, timedelta, timezone
            try:
                start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                # Attach Eastern timezone offset (-05:00 EST / -04:00 EDT)
                # Use -05:00 as default (EST); GHL handles DST based on calendar settings
                eastern = timezone(timedelta(hours=-5))
                start_dt = start_dt.replace(tzinfo=eastern)
            except Exception:
                return f"Invalid date/time: {date} {time}. Use YYYY-MM-DD for date and HH:MM (24h) for time."

            duration = cal.get("slotDuration", 30)
            end_dt = start_dt + timedelta(minutes=duration)

            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()

            logger.info(f"Booking appointment: {cal['name']} on {date} at {time} -> {start_iso}")

            result = await self.ghl_tools.create_appointment(
                calendar_id=cal["id"],
                contact_id=contact_id,
                start_time=start_iso,
                end_time=end_iso,
                title=title,
                location_id=self._current_location_id,
            )
            if result.get("success"):
                friendly_time = start_dt.strftime("%B %d at %I:%M %p").lstrip("0").replace(" 0", " ")
                return f"Appointment booked on {cal['name']} for {friendly_time} Eastern. A confirmation will be sent to the contact."
            else:
                return f"Could not book the appointment: {result.get('error', 'unknown error')}. Please try a different time."
        except Exception as e:
            logger.error(f"Book appointment error: {e}")
            return "I'm having trouble booking that appointment. Let me transfer you to someone who can help."

    @function_tool
    async def _create_contact(
        self,
        first_name: Annotated[str, "Caller's first name"],
        last_name: Annotated[str, "Caller's last name"] = "",
        email: Annotated[str, "Caller's email address (must be valid format like name@domain.com, leave blank if unknown)"] = "",
        phone: Annotated[str, "Caller's phone number (leave blank to use current caller's number)"] = "",
    ) -> str:
        """Create or update a contact in the CRM. Use this for new callers not yet in the system."""
        try:
            import re
            use_phone = phone or self._current_phone or ""
            if not use_phone:
                return "No phone number available. Please ask the caller for their phone number."

            # Validate email format before sending to GHL (prevents 422 errors)
            valid_email = ""
            if email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
                valid_email = email.strip()
            elif email:
                logger.warning(f"Invalid email format rejected: {email}")

            contact = await self.ghl_tools.upsert_contact(
                phone=use_phone,
                first_name=first_name,
                last_name=last_name,
                email=valid_email,
                source="voice-agent",
                tags=["voice-lead"],
                location_id=self._current_location_id,
            )
            if contact:
                self._current_contact_id = contact.get("id")
                name = contact.get("contactName") or f"{first_name} {last_name}".strip()
                result = f"Contact saved: {name}."
                if valid_email:
                    result += f" Email: {valid_email}."
                result += " You can now book appointments for this contact."
                return result
            else:
                return "Failed to create the contact record. The CRM may be temporarily unavailable."
        except Exception as e:
            logger.error(f"Create contact error: {e}")
            return "I encountered an error creating the contact record."

    @function_tool
    async def _lookup_contact(
        self,
        phone: Annotated[str, "Phone number to lookup"],
    ) -> str:
        """Look up contact information"""
        try:
            contact = await self.ghl_tools.lookup_contact_by_phone(self._current_location_id, phone)
            if contact:
                return f"Found contact: {contact.get('contactName', 'Unknown')}"
            else:
                return "No contact found with that phone number."
        except Exception as e:
            logger.error(f"Failed to lookup contact: {e}")
            return "I'm having trouble looking up that information right now."

    @function_tool
    async def _add_note(
        self,
        note: Annotated[str, "The note content to add to the contact's CRM record"],
    ) -> str:
        """Add a note to the current contact's CRM record in GoHighLevel"""
        contact_id = self._current_contact_id
        if not contact_id:
            return "No contact record linked to this call. I cannot add a note without a contact ID."
        try:
            saved = await self.ghl_tools.add_contact_note(contact_id, note)
            if saved:
                return f"Note saved to CRM record successfully."
            else:
                return "Failed to save the note. The CRM may be temporarily unavailable."
        except Exception as e:
            logger.error(f"Add note tool error: {e}")
            return "I encountered an error trying to save that note."

    @function_tool
    async def _transfer_to_human(
        self,
        reason: Annotated[str, "Reason for transfer"],
        department: Annotated[str, "Department"] = "support",
    ) -> str:
        """Transfer the call to a human agent"""
        # This would trigger a warm transfer in production
        logger.info(f"Transfer requested: {reason} -> {department}")
        return f"I understand you need {reason}. Let me connect you with our {department} team. Please hold for just a moment."


agent = AIMEVoiceAgent()
server = AgentServer()


@server.rtc_session(agent_name="aime-voice-agent")
async def entrypoint(ctx: JobContext):
    await agent.entry_point(ctx)


def main():
    """Entry point for running the agent"""
    cli.run_app(server)


if __name__ == "__main__":
    main()
