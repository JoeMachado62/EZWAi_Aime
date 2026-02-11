# LiveKit MCP Server - Setup Complete! 🎉

**Your AIME agents are now LiveKit experts!**

---

## ✅ What Was Configured

### 1. **LiveKit MCP Server** (in `openclaw.json`)

```json
"mcpServers": {
  "livekit-docs": {
    "transport": "http",
    "url": "https://docs.livekit.io/mcp",
    "description": "LiveKit documentation browser and search"
  }
}
```

This gives AI agents working on your AIME platform access to:

- 📚 **Complete LiveKit documentation** - All docs from https://docs.livekit.io
- 🔍 **GitHub code search** - Search across all LiveKit repos
- 📋 **Changelogs** - Version history for all LiveKit packages
- 💻 **Python examples** - LiveKit Agents SDK code samples

### 2. **Agent Instructions** (in `AIME_AGENTS.md`)

Created comprehensive guidelines for AI agents including:
- When to consult LiveKit docs
- How to use the MCP server tools
- LiveKit best practices
- AIME platform architecture
- Development workflows

---

## 🤖 How AI Agents Use This

When you (or an AI coding assistant) work on AIME, the agent will automatically:

### Search LiveKit Docs
```
Agent needs: "How to implement function tools in LiveKit?"
MCP Tool: search_docs("function tools python agents")
Result: Latest documentation on function tools
```

### Find Code Examples
```
Agent needs: "Example of LiveKit agent with custom tools"
MCP Tool: search_github_code("function_tool ai_callable")
Result: Real code from LiveKit repos
```

### Check Version Changes
```
Agent needs: "What changed in LiveKit Agents v0.10?"
MCP Tool: get_changelog("agents")
Result: Complete changelog
```

### Browse Specific Pages
```
Agent needs: "LiveKit SIP trunking documentation"
MCP Tool: get_doc_page("/sip/trunking")
Result: Full page content in markdown
```

---

## 🎯 Why This Approach is Best

### ✅ Advantages

1. **Always Up-to-Date**
   - LiveKit maintains the MCP server
   - No need to update local documentation
   - Latest features and examples

2. **No Custom Code Needed**
   - OpenClaw has native MCP support
   - No skill to build or maintain
   - Works out of the box

3. **Better Than Custom Skill**
   - More comprehensive than you could build
   - Official LiveKit support
   - Includes GitHub code search

4. **Works Across All Agents**
   - Any AI agent using OpenClaw has access
   - Voice agent code generation
   - Debugging and troubleshooting

---

## 💡 When Agents Will Use It

AI agents will automatically consult LiveKit docs when:

1. **Writing Voice Agent Code**
   - Adding new function tools
   - Implementing STT/TTS features
   - Handling LiveKit events

2. **Debugging Issues**
   - Voice quality problems
   - Connection issues
   - SIP configuration errors

3. **Adding Features**
   - Call recording
   - Participant tracking
   - Custom audio processing

4. **Updating Dependencies**
   - Understanding breaking changes
   - Finding migration guides
   - Checking compatibility

---

## 🚀 How to Use (For You)

### If You're Using Claude Code (This Session)

The MCP server is already available! Just ask questions like:

```
"How do I add a function tool to the LiveKit voice agent?"
"Show me examples of LiveKit agent error handling"
"What's the latest way to configure Deepgram with LiveKit?"
```

The agent will automatically search LiveKit docs via MCP.

### If You're Using Cursor

Add the MCP server manually:

1. Click settings (⚙️)
2. Go to **MCP Servers**
3. Add this configuration:

```json
{
  "livekit-docs": {
    "url": "https://docs.livekit.io/mcp"
  }
}
```

### If You're Using Another IDE

Install manually by adding to your MCP client configuration:

```
URL: https://docs.livekit.io/mcp
Transport: http (or "Streamable HTTP")
Name: livekit-docs
```

---

## 📋 Available MCP Tools

The LiveKit MCP server provides these tools:

### 1. `search_docs`
Search across all LiveKit documentation.

**Parameters**:
- `query`: Search term (e.g., "function tools")

**Returns**: Matching documentation pages with excerpts

### 2. `get_doc_page`
Retrieve full content of a specific doc page.

**Parameters**:
- `path`: Page path (e.g., "/agents/quickstart")

**Returns**: Complete page content in markdown

### 3. `search_github_code`
Search code across LiveKit GitHub repositories.

**Parameters**:
- `query`: Code search query
- `language`: Optional (e.g., "python")
- `repo`: Optional (e.g., "livekit/agents")

**Returns**: Code snippets with context

### 4. `get_changelog`
Get changelog for a LiveKit package.

**Parameters**:
- `package`: Package name (e.g., "agents", "server")

**Returns**: Version history and changes

### 5. `get_examples`
Browse Python Agents SDK examples.

**Parameters**:
- `category`: Optional filter

**Returns**: List of example code files

---

## 🔧 Configuration Files

### `openclaw.json` (Created)
Main OpenClaw configuration with MCP server, agents, channels, and environment variables.

**Location**: `/EZWAi_Aime/openclaw.json`

**Key sections**:
- `mcpServers`: LiveKit docs MCP server
- `agents.defaults`: Claude Sonnet 4.5 with MCP enabled
- `providers`: Anthropic and OpenAI configuration
- `env`: LiveKit and GHL credentials

### `AIME_AGENTS.md` (Created)
Instructions for AI agents working on AIME platform.

**Location**: `/EZWAi_Aime/AIME_AGENTS.md`

**Contents**:
- Project architecture
- LiveKit MCP usage guide
- Development guidelines
- Best practices
- Resource links

---

## ✨ Example Usage

### Scenario: Adding a New Function Tool

**You ask**:
> "I want to add a function tool to the voice agent that books appointments in GoHighLevel"

**Agent response** (using MCP):

1. **Searches LiveKit docs**: `search_docs("function tools python")`
2. **Finds examples**: `search_github_code("@llm.ai_callable")`
3. **Gets changelog**: `get_changelog("agents")` (checks current best practices)
4. **Generates code** based on latest LiveKit patterns
5. **Includes proper error handling** from LiveKit examples

**Result**: Modern, working code that follows LiveKit best practices!

---

## 🆘 Troubleshooting

### Issue: "MCP server not responding"

**Check internet connection**:
```bash
curl https://docs.livekit.io/mcp
```

Should return JSON response.

### Issue: "MCP tools not available"

**Verify OpenClaw configuration**:
```bash
cat openclaw.json | grep -A 5 mcpServers
```

Should show the livekit-docs configuration.

### Issue: "Agent isn't using LiveKit docs"

**Reminder in prompt**: Add this to your question:
> "Please check the LiveKit documentation using the MCP server"

Or reference the AIME_AGENTS.md file:
> "Following the AIME_AGENTS.md guidelines..."

---

## 📚 Fallback: Markdown Docs

If MCP is unavailable for any reason, you can still access LiveKit docs:

### Option 1: Append `.md` to Any URL

Any page on docs.livekit.io is available in markdown:

- https://docs.livekit.io/agents/quickstart → https://docs.livekit.io/agents/quickstart.md
- https://docs.livekit.io/sip/overview → https://docs.livekit.io/sip/overview.md

### Option 2: Use llms.txt

Complete documentation index:
- **Table of contents**: https://docs.livekit.io/llms.txt
- **Full content**: https://docs.livekit.io/llms-full.txt (very large)

Copy and paste into your AI assistant if needed.

---

## 🎯 Next Steps

1. **Test the integration**: Ask an AI agent a LiveKit question
2. **Continue with setup**: Follow [LIVEKIT_SETUP_STEPS.md](LIVEKIT_SETUP_STEPS.md)
3. **Deploy voice agent**: Once you have API keys
4. **Monitor usage**: Check that agents are using latest LiveKit patterns

---

## 📖 Documentation

- **AIME Agent Instructions**: [AIME_AGENTS.md](AIME_AGENTS.md)
- **LiveKit Setup**: [LIVEKIT_SETUP_STEPS.md](LIVEKIT_SETUP_STEPS.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **All Documentation**: [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

---

**Your AIME platform is now MCP-powered! 🚀**

AI agents working on this project will automatically access the latest LiveKit documentation, ensuring reliable, modern, working code every time.
