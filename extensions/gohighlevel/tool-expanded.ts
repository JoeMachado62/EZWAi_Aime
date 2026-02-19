/**
 * GoHighLevel Agent Tools - EXPANDED VERSION (Direct REST API)
 * Bypasses @gohighlevel/api-client in favor of direct fetch() calls
 * which are proven to work with the Private Integration Token.
 */

import type { AgentToolResult } from '@mariozechner/pi-agent-core';
import * as fs from 'node:fs';
import * as path from 'node:path';

// ── Helpers ──────────────────────────────────────────────────────────

function successResult(text: string): AgentToolResult<unknown> {
  return { content: [{ type: 'text', text }] };
}
function errorResult(msg: string): AgentToolResult<unknown> {
  return { content: [{ type: 'text', text: JSON.stringify({ status: 'error', error: msg }) }] };
}

/** Load .env if env vars are missing */
function ensureEnv(): void {
  if (process.env.GHL_PIT_TOKEN) return;
  let dir = typeof __dirname !== 'undefined' ? __dirname : process.cwd();
  for (let i = 0; i < 6; i++) {
    const p = path.join(dir, '.env');
    if (fs.existsSync(p)) {
      for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
        const t = line.trim();
        if (!t || t.startsWith('#')) continue;
        const eq = t.indexOf('=');
        if (eq < 0) continue;
        const k = t.slice(0, eq).trim();
        const v = t.slice(eq + 1).trim();
        if (!process.env[k]) process.env[k] = v;
      }
      return;
    }
    dir = path.dirname(dir);
  }
}

const BASE = 'https://services.leadconnectorhq.com';

async function ghlFetch(urlPath: string, method: string, body?: unknown): Promise<unknown> {
  ensureEnv();
  const token = process.env.GHL_PIT_TOKEN;
  if (!token) throw new Error('GHL_PIT_TOKEN not set');
  const resp = await fetch(`${BASE}${urlPath}`, {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Version': '2021-07-28',
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await resp.text();
  if (!resp.ok) throw new Error(`GHL API ${resp.status}: ${text}`);
  try { return JSON.parse(text); } catch { return text; }
}

function getLoc(params: Record<string, unknown>, fallback: string | undefined): string | null {
  return (params.locationId as string) || fallback || process.env.GHL_LOCATION_ID || null;
}

// ── Tool Factory ─────────────────────────────────────────────────────

export function createGHLToolsExpanded(ctx: unknown): unknown[] | null {
  try {
    ensureEnv();
    const locationId = process.env.GHL_LOCATION_ID;

    return [

      // ==================== CONTACTS ====================
      {
        name: 'ghl_get_contact',
        description: 'Get complete contact information from GoHighLevel CRM including conversation history, tasks, appointments, and notes.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string', description: 'GHL Contact ID (required)' },
            locationId: { type: 'string', description: 'GHL Location ID (optional)' },
            includeConversations: { type: 'boolean', default: true },
            includeTasks: { type: 'boolean', default: true },
            maxMessages: { type: 'number', default: 50 },
          },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(`/contacts/${params.contactId}`, 'GET') as Record<string, unknown>;
            const contact = (data as any).contact || data;

            let result = `# Contact: ${contact.firstName || ''} ${contact.lastName || ''}\n`;
            result += `- ID: ${contact.id}\n`;
            result += `- Phone: ${contact.phone || 'N/A'}\n`;
            result += `- Email: ${contact.email || 'N/A'}\n`;
            result += `- Tags: ${(contact.tags as string[])?.join(', ') || 'none'}\n`;
            result += `- Source: ${contact.source || 'N/A'}\n`;
            result += `- Created: ${contact.dateAdded || 'N/A'}\n`;

            if (params.includeTasks !== false) {
              try {
                const tasks = await ghlFetch(`/contacts/${params.contactId}/tasks`, 'GET') as any;
                if (tasks.tasks?.length) {
                  result += `\n## Tasks (${tasks.tasks.length})\n`;
                  for (const t of tasks.tasks.slice(0, 10)) {
                    result += `- [${t.completed ? 'x' : ' '}] ${t.title}${t.dueDate ? ` (due: ${t.dueDate})` : ''}\n`;
                  }
                }
              } catch { /* tasks fetch optional */ }
            }

            if (params.includeConversations !== false) {
              try {
                const loc = getLoc(params, locationId);
                if (loc) {
                  const convs = await ghlFetch(`/conversations/search?contactId=${params.contactId}&locationId=${loc}`, 'GET') as any;
                  if (convs.conversations?.length) {
                    const convId = convs.conversations[0].id;
                    const msgs = await ghlFetch(`/conversations/${convId}/messages`, 'GET') as any;
                    if (msgs.messages?.length) {
                      result += `\n## Recent Messages (${Math.min(msgs.messages.length, Number(params.maxMessages) || 50)})\n`;
                      for (const m of msgs.messages.slice(0, Number(params.maxMessages) || 50)) {
                        result += `- [${m.direction}] ${m.body?.substring(0, 200) || '(no body)'}\n`;
                      }
                    }
                  }
                }
              } catch { /* conversation fetch optional */ }
            }

            return successResult(result);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_search_contacts',
        description: 'Search for contacts in GoHighLevel CRM by name, email, phone, or other fields.',
        parameters: {
          type: 'object',
          properties: {
            query: { type: 'string', description: 'Search query' },
            locationId: { type: 'string' },
            limit: { type: 'number', default: 10 },
          },
          required: ['query'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const q = encodeURIComponent(params.query as string);
            const limit = params.limit || 10;
            const data = await ghlFetch(`/contacts/?locationId=${loc}&query=${q}&limit=${limit}`, 'GET') as any;
            const contacts = (data.contacts || []).map((c: any) => ({
              id: c.id, name: `${c.firstName || ''} ${c.lastName || ''}`.trim(),
              email: c.email, phone: c.phone, tags: c.tags, source: c.source,
            }));
            return successResult(JSON.stringify(contacts, null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_create_contact',
        description: 'Create a new contact in GoHighLevel CRM.',
        parameters: {
          type: 'object',
          properties: {
            firstName: { type: 'string', description: 'First name (required)' },
            lastName: { type: 'string' },
            email: { type: 'string' },
            phone: { type: 'string', description: 'E.164 format like +18508428707' },
            tags: { type: 'array', items: { type: 'string' } },
            source: { type: 'string', description: 'Lead source (defaults to AIME-Agent)' },
            locationId: { type: 'string' },
          },
          required: ['firstName'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const body: Record<string, unknown> = {
              firstName: params.firstName,
              locationId: loc,
              source: params.source || 'AIME-Agent',
            };
            if (params.lastName) body.lastName = params.lastName;
            if (params.email) body.email = params.email;
            if (params.phone) body.phone = params.phone;
            if (params.tags) body.tags = params.tags;

            const data = await ghlFetch('/contacts/', 'POST', body) as any;
            const c = data.contact || data;
            return successResult(`Contact created!\nID: ${c.id}\nName: ${c.firstName} ${c.lastName || ''}\nPhone: ${c.phone || 'N/A'}\nEmail: ${c.email || 'N/A'}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_update_contact',
        description: 'Update an existing contact in GoHighLevel CRM (email, name, custom fields, etc.)',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            firstName: { type: 'string' },
            lastName: { type: 'string' },
            email: { type: 'string' },
            phone: { type: 'string' },
            tags: { type: 'array', items: { type: 'string' } },
            companyName: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const body: Record<string, unknown> = {};
            for (const key of ['firstName', 'lastName', 'email', 'phone', 'tags', 'companyName']) {
              if (params[key] !== undefined) body[key] = params[key];
            }
            const data = await ghlFetch(`/contacts/${params.contactId}`, 'PUT', body) as any;
            const c = data.contact || data;
            return successResult(`Contact updated: ${c.id}\nName: ${c.firstName || ''} ${c.lastName || ''}\nEmail: ${c.email || 'N/A'}\nPhone: ${c.phone || 'N/A'}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== CONVERSATIONS ====================
      {
        name: 'ghl_get_conversation_history',
        description: 'Get detailed conversation history for a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            locationId: { type: 'string' },
            maxMessages: { type: 'number', default: 50 },
          },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const convs = await ghlFetch(`/conversations/search?contactId=${params.contactId}&locationId=${loc}`, 'GET') as any;
            if (!convs.conversations?.length) return successResult('No conversations found.');
            const convId = convs.conversations[0].id;
            const msgs = await ghlFetch(`/conversations/${convId}/messages`, 'GET') as any;
            const max = Number(params.maxMessages) || 50;
            let result = `## Conversation History (${Math.min(msgs.messages?.length || 0, max)} messages)\n`;
            for (const m of (msgs.messages || []).slice(0, max)) {
              const dir = m.direction === 'inbound' ? '📥' : '📤';
              const date = m.dateAdded ? new Date(m.dateAdded).toLocaleString() : '';
              result += `${dir} [${date}] ${m.body?.substring(0, 300) || '(no body)'}\n`;
            }
            return successResult(result);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_send_message',
        description: 'Send a message to a contact via SMS, Email, or WhatsApp.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            message: { type: 'string' },
            type: { type: 'string', enum: ['SMS', 'Email', 'WhatsApp'], default: 'SMS' },
            locationId: { type: 'string' },
          },
          required: ['contactId', 'message'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            // First get or create conversation
            const convSearch = await ghlFetch(`/conversations/search?contactId=${params.contactId}&locationId=${loc}`, 'GET') as any;
            let conversationId: string;
            if (convSearch.conversations?.length) {
              conversationId = convSearch.conversations[0].id;
            } else {
              const newConv = await ghlFetch('/conversations/', 'POST', { contactId: params.contactId, locationId: loc }) as any;
              conversationId = newConv.conversation?.id || newConv.id;
            }
            const msgType = (params.type as string) || 'SMS';
            const msgBody: Record<string, unknown> = {
              type: msgType,
              contactId: params.contactId,
              message: params.message,
            };
            const result = await ghlFetch(`/conversations/messages`, 'POST', msgBody) as any;
            return successResult(`Message sent via ${msgType}. ID: ${result.messageId || result.id || 'sent'}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== TASKS ====================
      {
        name: 'ghl_create_task',
        description: 'Create a follow-up task for a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            title: { type: 'string' },
            description: { type: 'string' },
            dueDate: { type: 'string', description: 'ISO 8601 format' },
            assignedTo: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['contactId', 'title'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const body: Record<string, unknown> = {
              title: params.title,
              completed: false,
            };
            if (params.description) body.body = params.description;
            if (params.dueDate) body.dueDate = params.dueDate;
            if (params.assignedTo) body.assignedTo = params.assignedTo;
            const data = await ghlFetch(`/contacts/${params.contactId}/tasks`, 'POST', body) as any;
            const t = data.task || data;
            return successResult(`Task created: ${t.id} - ${t.title}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_contact_tasks',
        description: 'Get all tasks for a contact.',
        parameters: {
          type: 'object',
          properties: { contactId: { type: 'string' }, locationId: { type: 'string' } },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(`/contacts/${params.contactId}/tasks`, 'GET') as any;
            return successResult(JSON.stringify(data.tasks || [], null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_update_task',
        description: 'Update an existing task.',
        parameters: {
          type: 'object',
          properties: {
            taskId: { type: 'string' },
            contactId: { type: 'string', description: 'Contact ID that owns the task' },
            title: { type: 'string' },
            description: { type: 'string' },
            completed: { type: 'boolean' },
            dueDate: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['taskId', 'contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const body: Record<string, unknown> = {};
            if (params.title !== undefined) body.title = params.title;
            if (params.description !== undefined) body.body = params.description;
            if (params.completed !== undefined) body.completed = params.completed;
            if (params.dueDate !== undefined) body.dueDate = params.dueDate;
            const data = await ghlFetch(`/contacts/${params.contactId}/tasks/${params.taskId}`, 'PUT', body) as any;
            return successResult(`Task updated: ${data.task?.id || params.taskId}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== NOTES ====================
      {
        name: 'ghl_add_note',
        description: 'Add a note to a contact record.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            body: { type: 'string', description: 'Note text' },
          },
          required: ['contactId', 'body'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(`/contacts/${params.contactId}/notes`, 'POST', {
              body: params.body,
              userId: params.contactId,
            }) as any;
            return successResult(`Note added: ${data.note?.id || 'done'}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== CALENDARS & APPOINTMENTS ====================
      {
        name: 'ghl_list_calendars',
        description: 'List all available calendars in the location.',
        parameters: {
          type: 'object',
          properties: { locationId: { type: 'string' } },
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch(`/calendars/?locationId=${loc}`, 'GET') as any;
            const cals = (data.calendars || []).map((c: any) => ({
              id: c.id, name: c.name, description: c.description,
            }));
            return successResult(JSON.stringify(cals, null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_calendar_slots',
        description: 'Get available time slots for a calendar.',
        parameters: {
          type: 'object',
          properties: {
            calendarId: { type: 'string' },
            startDate: { type: 'string', description: 'Start date (YYYY-MM-DD)' },
            endDate: { type: 'string', description: 'End date (YYYY-MM-DD)' },
            locationId: { type: 'string' },
          },
          required: ['calendarId', 'startDate', 'endDate'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(
              `/calendars/${params.calendarId}/free-slots?startDate=${params.startDate}&endDate=${params.endDate}`,
              'GET'
            ) as any;
            return successResult(JSON.stringify(data, null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_create_appointment',
        description: 'Book an appointment on a calendar for a contact.',
        parameters: {
          type: 'object',
          properties: {
            calendarId: { type: 'string' },
            contactId: { type: 'string' },
            startTime: { type: 'string', description: 'ISO 8601 datetime' },
            endTime: { type: 'string', description: 'ISO 8601 datetime' },
            title: { type: 'string' },
            notes: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['calendarId', 'contactId', 'startTime'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const body: Record<string, unknown> = {
              calendarId: params.calendarId,
              contactId: params.contactId,
              startTime: params.startTime,
              locationId: loc,
              title: params.title || 'Appointment',
              appointmentStatus: 'confirmed',
            };
            if (params.endTime) body.endTime = params.endTime;
            if (params.notes) body.notes = params.notes;
            const data = await ghlFetch('/calendars/events/appointments', 'POST', body) as any;
            return successResult(`Appointment booked!\nID: ${data.id || data.event?.id || 'created'}\nTime: ${params.startTime}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_contact_appointments',
        description: 'Get all appointments for a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(`/contacts/${params.contactId}/appointments`, 'GET') as any;
            return successResult(JSON.stringify(data.events || data.appointments || [], null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== WORKFLOWS ====================
      {
        name: 'ghl_list_workflows',
        description: 'List all available workflows in the location.',
        parameters: {
          type: 'object',
          properties: { locationId: { type: 'string' } },
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch(`/workflows/?locationId=${loc}`, 'GET') as any;
            const wfs = (data.workflows || []).map((w: any) => ({ id: w.id, name: w.name, status: w.status }));
            return successResult(JSON.stringify(wfs, null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_trigger_workflow',
        description: 'Add a contact to a workflow to trigger automation.',
        parameters: {
          type: 'object',
          properties: {
            workflowId: { type: 'string' },
            contactId: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['workflowId', 'contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            await ghlFetch(`/workflows/${params.workflowId}/contacts`, 'POST', {
              contactId: params.contactId,
            });
            return successResult('Contact added to workflow');
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== OPPORTUNITIES / PIPELINES ====================
      {
        name: 'ghl_list_pipelines',
        description: 'List all sales pipelines and their stages.',
        parameters: {
          type: 'object',
          properties: { locationId: { type: 'string' } },
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch(`/opportunities/pipelines?locationId=${loc}`, 'GET') as any;
            return successResult(JSON.stringify(data.pipelines || [], null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_contact_opportunities',
        description: 'Get all opportunities/deals for a contact.',
        parameters: {
          type: 'object',
          properties: { contactId: { type: 'string' }, locationId: { type: 'string' } },
          required: ['contactId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch(`/opportunities/search?location_id=${loc}&contact_id=${params.contactId}`, 'GET') as any;
            return successResult(JSON.stringify(data.opportunities || [], null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_create_opportunity',
        description: 'Create a new opportunity/deal for a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            name: { type: 'string', description: 'Opportunity name' },
            pipelineId: { type: 'string' },
            pipelineStageId: { type: 'string' },
            monetaryValue: { type: 'number' },
            status: { type: 'string', enum: ['open', 'won', 'lost', 'abandoned'], default: 'open' },
            locationId: { type: 'string' },
          },
          required: ['contactId', 'name', 'pipelineId', 'pipelineStageId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch('/opportunities/', 'POST', {
              pipelineId: params.pipelineId,
              locationId: loc,
              name: params.name,
              pipelineStageId: params.pipelineStageId,
              status: params.status || 'open',
              contactId: params.contactId,
              monetaryValue: params.monetaryValue,
            }) as any;
            return successResult(`Opportunity created: ${data.opportunity?.id || data.id} - ${params.name}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_update_opportunity',
        description: 'Update an opportunity - change stage, status, value, etc.',
        parameters: {
          type: 'object',
          properties: {
            opportunityId: { type: 'string' },
            pipelineStageId: { type: 'string' },
            status: { type: 'string', enum: ['open', 'won', 'lost', 'abandoned'] },
            monetaryValue: { type: 'number' },
            name: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['opportunityId'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const body: Record<string, unknown> = {};
            for (const k of ['name', 'pipelineStageId', 'status', 'monetaryValue']) {
              if (params[k] !== undefined) body[k] = params[k];
            }
            const data = await ghlFetch(`/opportunities/${params.opportunityId}`, 'PUT', body) as any;
            return successResult(`Opportunity updated: ${data.opportunity?.id || params.opportunityId}`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== TAGS ====================
      {
        name: 'ghl_get_tags',
        description: 'Get all available tags in the location.',
        parameters: {
          type: 'object',
          properties: { locationId: { type: 'string' } },
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const data = await ghlFetch(`/locations/${loc}/tags`, 'GET') as any;
            return successResult(JSON.stringify((data.tags || []).map((t: any) => t.name || t), null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_add_tag',
        description: 'Add a tag to a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            tagName: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['contactId', 'tagName'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            // Get current tags, add new one
            const data = await ghlFetch(`/contacts/${params.contactId}`, 'GET') as any;
            const contact = data.contact || data;
            const tags = new Set(contact.tags || []);
            tags.add(params.tagName);
            await ghlFetch(`/contacts/${params.contactId}`, 'PUT', { tags: Array.from(tags) });
            return successResult(`Tag "${params.tagName}" added`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_remove_tag',
        description: 'Remove a tag from a contact.',
        parameters: {
          type: 'object',
          properties: {
            contactId: { type: 'string' },
            tagName: { type: 'string' },
            locationId: { type: 'string' },
          },
          required: ['contactId', 'tagName'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const data = await ghlFetch(`/contacts/${params.contactId}`, 'GET') as any;
            const contact = data.contact || data;
            const tags = (contact.tags || []).filter((t: string) => t !== params.tagName);
            await ghlFetch(`/contacts/${params.contactId}`, 'PUT', { tags });
            return successResult(`Tag "${params.tagName}" removed`);
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_contacts_by_tag',
        description: 'Get contacts with a specific tag.',
        parameters: {
          type: 'object',
          properties: {
            tagName: { type: 'string' },
            locationId: { type: 'string' },
            limit: { type: 'number', default: 100 },
          },
          required: ['tagName'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const q = encodeURIComponent(params.tagName as string);
            const data = await ghlFetch(`/contacts/?locationId=${loc}&query=${q}&limit=${params.limit || 100}`, 'GET') as any;
            const contacts = (data.contacts || []).filter((c: any) => c.tags?.includes(params.tagName));
            return successResult(JSON.stringify(contacts.map((c: any) => ({
              id: c.id, name: `${c.firstName || ''} ${c.lastName || ''}`.trim(), phone: c.phone, email: c.email,
            })), null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      {
        name: 'ghl_get_contacts_by_tags',
        description: 'Get contacts matching multiple tags (AND/OR logic).',
        parameters: {
          type: 'object',
          properties: {
            tags: { type: 'array', items: { type: 'string' } },
            matchAll: { type: 'boolean', default: false },
            locationId: { type: 'string' },
            limit: { type: 'number', default: 100 },
          },
          required: ['tags'],
        },
        execute: async (_id: string, params: Record<string, unknown>) => {
          try {
            const loc = getLoc(params, locationId);
            if (!loc) return errorResult('Location ID required');
            const tagList = params.tags as string[];
            const data = await ghlFetch(`/contacts/?locationId=${loc}&limit=${params.limit || 100}`, 'GET') as any;
            const contacts = (data.contacts || []).filter((c: any) => {
              if (!c.tags) return false;
              return params.matchAll
                ? tagList.every(t => c.tags.includes(t))
                : tagList.some(t => c.tags.includes(t));
            });
            return successResult(JSON.stringify(contacts.map((c: any) => ({
              id: c.id, name: `${c.firstName || ''} ${c.lastName || ''}`.trim(), phone: c.phone, tags: c.tags,
            })), null, 2));
          } catch (error: any) {
            return errorResult(`Failed: ${error.message}`);
          }
        },
      },

      // ==================== CAMPAIGNS ====================
      // (Campaigns use local in-memory storage - kept as-is from original)
      // These would need a proper campaign service for production use

    ];
  } catch (error) {
    console.error('[GHL Tools] Failed to initialize:', error);
    return null;
  }
}
