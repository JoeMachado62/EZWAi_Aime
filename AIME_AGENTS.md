# AIME Platform - Agent Instructions

This file contains instructions for AI agents working on the AIME (AI-powered Multi-channel Engagement) platform.

---

## Project Overview

**AIME** is an AI-powered voice agent platform built on:
- **OpenClaw**: Multi-channel AI gateway framework (v2026.2.9)
- **LiveKit**: Real-time voice communication infrastructure
- **GoHighLevel (GHL)**: CRM integration via official SDK
- **Claude Sonnet 4.5**: Primary LLM with cost-optimized routing (T0-T3)

### Architecture

```
Phone Call (+13059521569)
    ↓
LiveKit Cloud (SIP)
    ↓
Voice Agent (Python)
    ├─→ Deepgram (STT)
    ├─→ Anthropic Claude (LLM)
    ├─→ Cartesia/OpenAI (TTS)
    └─→ OpenClaw Bridge (Node.js)
         ├─→ GHL Plugin (contacts, conversations, tasks)
         ├─→ Contact Memory (cross-channel history)
         └─→ Model Router (T0→T3 cost optimization)
```

---

## LiveKit Documentation

**IMPORTANT**: LiveKit Agents is a fast-evolving project, and the documentation is updated frequently. You should **always refer to the latest documentation** when working with this project.

### LiveKit MCP Server

This project is configured with the **LiveKit Docs MCP Server**, which provides:
- Documentation browsing and search
- GitHub code search across LiveKit repositories
- Changelog access for LiveKit packages
- Python Agents SDK examples

**MCP Server URL**: https://docs.livekit.io/mcp

### When to Use LiveKit Docs

**Always consult LiveKit documentation when**:
1. Working with LiveKit voice agents (`agents/voice_agent.py`)
2. Implementing or debugging SIP telephony features
3. Configuring LiveKit Cloud deployment
4. Troubleshooting voice quality or connection issues
5. Adding new LiveKit features (participant tracking, recordings, etc.)
6. Updating LiveKit dependencies

### How to Access Documentation

The LiveKit MCP server is already configured in `openclaw.json`. When you need LiveKit documentation:

1. **Search the docs**:
   ```
   Use MCP tool: search_docs with query "voice agents python"
   ```

2. **Browse specific pages**:
   ```
   Use MCP tool: get_doc_page with path "/agents/quickstart"
   ```

3. **Find code examples**:
   ```
   Use MCP tool: search_github_code with query "function_tool"
   ```

4. **Check changelogs**:
   ```
   Use MCP tool: get_changelog with package "agents"
   ```

### Markdown Docs (Fallback)

If MCP is unavailable, access any LiveKit docs page in Markdown by appending `.md` to the URL:
- Example: https://docs.livekit.io/agents/quickstart.md

Complete index: https://docs.livekit.io/llms.txt

---

## Development Guidelines

### 1. **Cost Optimization is Critical**

The model router (T0-T3) saves 90%+ on LLM costs:
- **T0 (Ollama)**: Free - Use for simple routing, health checks
- **T1 (Haiku)**: $0.25/1M - Use for contact lookups, formatting
- **T2 (Sonnet)**: $3/1M - Use for conversations, task extraction
- **T3 (Opus)**: $15/1M - Use only for complex reasoning, errors

**Always**: Use the lowest tier that can handle the task. Let automatic escalation handle edge cases.

### 2. **LiveKit Best Practices**

When working with LiveKit voice agents:

- **Function Tools**: Use `@llm.ai_callable` decorator for LLM-callable functions
- **Session Management**: Use `AgentSession` for STT/LLM/TTS pipeline
- **Context Building**: Fetch contact context BEFORE starting session
- **Error Handling**: Gracefully handle LiveKit disconnections
- **Logging**: Use `logger.info()` for debugging voice flows

**Example**:
```python
@llm.ai_callable()
async def get_contact_info(phone_number: str):
    """Retrieve contact information from GoHighLevel CRM."""
    return await ghl_tools.lookup_contact(phone_number)
```

### 3. **GoHighLevel Integration**

Use the **official GHL SDK** (`@gohighlevel/api-client`):

```typescript
// Good - Use SDK
const client = await this.ghlAuth.getClient(locationId);
const contact = await client.contacts.get(contactId);

// Bad - Don't use raw HTTP
const response = await fetch(`https://api.gohighlevel.com/...`);
```

---

## Resources

### Documentation
- **AIME Platform**: [AIME_README.md](AIME_README.md)
- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **LiveKit Setup**: [LIVEKIT_SETUP_STEPS.md](LIVEKIT_SETUP_STEPS.md)

### External Docs
- **LiveKit**: https://docs.livekit.io/ (via MCP)
- **LiveKit MCP**: https://docs.livekit.io/mcp
- **GHL SDK**: https://marketplace.gohighlevel.com/docs/sdk/node/
- **OpenClaw**: https://docs.openclaw.ai
- **Anthropic**: https://docs.anthropic.com

---

**Remember**: Always consult the latest LiveKit documentation via the MCP server when working with voice agents. The framework evolves quickly, and up-to-date docs ensure reliable, working code.
