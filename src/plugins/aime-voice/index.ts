/**
 * AIME Voice Plugin for OpenClaw
 * LiveKit voice agent with GHL CRM synchronization
 */

import type { OpenClawPluginApi, OpenClawPluginDefinition } from '../types.js';
import { BridgeLayer } from '../../bridge/index.js';
import { AICallInitiator } from '../../ai-call-initiator.js';
import { ContactMemoryManager } from '../../memory/contact-memory/index.js';

const aimeVoicePlugin: OpenClawPluginDefinition = {
  id: 'aime-voice',
  name: 'AIME Voice Agent',
  description: 'LiveKit voice agent with GoHighLevel CRM synchronization and contact memory integration',
  version: '1.0.0',

  register(api: OpenClawPluginApi) {
    api.logger.info('Initializing AIME Voice plugin...');

    let bridgeLayer: BridgeLayer | null = null;
    let callInitiator: AICallInitiator | null = null;

    // Initialize bridge layer
    const initializeBridge = () => {
      if (!bridgeLayer) {
        // Get GHL plugin instance
        const ghlPlugin = api.runtime?.getPlugin?.('gohighlevel');

        // Get memory manager
        const memoryManager = new ContactMemoryManager({
          dbPath: api.runtime?.getDataPath?.('contact-memory.db') || './data/contact-memory.db'
        });

        bridgeLayer = new BridgeLayer({
          ghlPlugin,
          memoryManager,
          modelRouter: api.runtime?.modelRouter
        });

        api.logger.info('Bridge layer initialized');
      }
      return bridgeLayer;
    };

    // Initialize AI call initiator
    const initializeCallInitiator = () => {
      if (!callInitiator) {
        callInitiator = new AICallInitiator();
        api.logger.info('AI call initiator initialized');
      }
      return callInitiator;
    };

    // Register HTTP routes from AIME server
    api.registerHttpRoute({
      path: '/api/bridge/process-call',
      handler: async (req, res) => {
        try {
          const bridge = initializeBridge();
          // Normalize snake_case from Python voice agent to camelCase
          const body = req.body;
          const normalized = {
            contactId: body.contactId || body.contact_id,
            locationId: body.locationId || body.location_id,
            phone: body.phone,
            transcript: body.transcript,
            durationSeconds: body.durationSeconds || body.duration_seconds || 0,
            roomName: body.roomName || body.room_name,
          };
          const result = await bridge.processCall(normalized);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({
            success: true,
            data: result
          }));
        } catch (error) {
          api.logger.error('[AIME Voice] Call processing error:', error);
          res.statusCode = 500;
          res.end(JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error)
          }));
        }
      }
    });

    api.registerHttpRoute({
      path: '/api/calls/ai-initiate',
      handler: async (req, res) => {
        try {
          const initiator = initializeCallInitiator();
          const result = await initiator.initiateCall(req.body);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({
            success: true,
            data: result
          }));
        } catch (error) {
          api.logger.error('[AIME Voice] Call initiation error:', error);
          res.statusCode = 500;
          res.end(JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error)
          }));
        }
      }
    });

    api.registerHttpRoute({
      path: '/api/calls/completed',
      handler: async (req, res) => {
        try {
          const bridge = initializeBridge();
          // Handle call completion webhook from voice agent
          const body = req.body;
          const normalized = {
            contactId: body.metadata?.contact_id || body.contact_id,
            locationId: body.metadata?.location_id || body.location_id || '',
            transcript: body.transcript || '',
            durationSeconds: 0,
            roomName: body.roomName || body.room_name || '',
          };
          const result = await bridge.processCall(normalized);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({
            success: true,
            data: result
          }));
        } catch (error) {
          api.logger.error('[AIME Voice] Call completion error:', error);
          res.statusCode = 500;
          res.end(JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error)
          }));
        }
      }
    });

    api.registerHttpRoute({
      path: '/api/calls/status/:roomName',
      handler: async (req, res) => {
        try {
          const roomName = req.params?.roomName;
          if (!roomName) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Room name required' }));
            return;
          }

          const bridge = initializeBridge();
          const status = await bridge.getCallStatus(roomName);

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({
            success: true,
            data: status
          }));
        } catch (error) {
          api.logger.error('[AIME Voice] Status check error:', error);
          res.statusCode = 500;
          res.end(JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error)
          }));
        }
      }
    });

    // Bridge context endpoint — exposes GHL contact context to Python voice agent
    api.registerHttpRoute({
      path: '/api/bridge/memory/context/:contactId',
      handler: async (req, res) => {
        try {
          const contactId = req.params?.contactId;
          const locationId = req.query?.locationId as string;
          if (!contactId) {
            res.statusCode = 400;
            res.end(JSON.stringify({ error: 'Contact ID required' }));
            return;
          }

          const ghlPlugin = api.runtime?.getPlugin?.('gohighlevel') as any;
          let context: any = {};

          if (ghlPlugin && locationId) {
            // Pull full GHL context: conversations, tasks, appointments
            const [conversations, tasks, appointments] = await Promise.allSettled([
              ghlPlugin.conversations?.getAllContactMessages?.(locationId, contactId, 10),
              ghlPlugin.tasks?.getContactTasks?.(locationId, contactId),
              ghlPlugin.calendars?.getContactAppointments?.(locationId, contactId),
            ]);

            context = {
              conversations: conversations.status === 'fulfilled' ? conversations.value : [],
              tasks: tasks.status === 'fulfilled' ? tasks.value : [],
              appointments: appointments.status === 'fulfilled' ? appointments.value : [],
            };
          } else {
            // Fallback to bridge layer memory
            const bridge = initializeBridge();
            context = await bridge.getContactContext(contactId);
          }

          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(context));
        } catch (error) {
          api.logger.error('[AIME Voice] Context fetch error:', error);
          res.statusCode = 500;
          res.end(JSON.stringify({
            error: error instanceof Error ? error.message : String(error)
          }));
        }
      }
    });

    // Register livekit_call tool — gives OpenClaw agents access to LiveKit HD voice calls
    api.registerTool({
      name: 'livekit_call',
      label: 'LiveKit Call',
      description: 'Make AI voice calls via LiveKit with HD voice quality (Deepgram Nova-3 STT + Inworld 1.5 Max TTS). Supports single calls, AI-parsed instructions, batch outreach by GHL tag/pipeline, and status checks.',
      parameters: {
        type: 'object',
        properties: {
          action: {
            type: 'string',
            enum: ['initiate', 'ai_initiate', 'batch_call', 'status'],
            description: 'Action: initiate (direct call), ai_initiate (parse NL instruction), batch_call (call contacts by tag), status (check call status)',
          },
          phone_number: { type: 'string', description: 'Phone number in E.164 format (e.g., +13055551234)' },
          instructions: { type: 'string', description: 'Instructions for the voice agent or natural language call instruction' },
          contact_name: { type: 'string', description: 'Name of the person being called' },
          contact_id: { type: 'string', description: 'GHL contact ID' },
          location_id: { type: 'string', description: 'GHL location ID' },
          filter_tag: { type: 'string', description: 'GHL tag to filter contacts for batch_call' },
          filter_pipeline: { type: 'string', description: 'Pipeline name for batch_call filtering' },
          filter_stage: { type: 'string', description: 'Pipeline stage for batch_call filtering' },
          room_name: { type: 'string', description: 'LiveKit room name (for status action)' },
          campaign_id: { type: 'string', description: 'Campaign ID (for status action)' },
        },
        required: ['action'],
      },
      async execute(_toolCallId: string, params: any) {
        const json = (payload: unknown) => ({
          content: [{ type: 'text' as const, text: JSON.stringify(payload, null, 2) }],
          details: payload,
        });

        try {
          const initiator = initializeCallInitiator();
          const bridge = initializeBridge();

          switch (params.action) {
            case 'ai_initiate': {
              if (!params.instructions) throw new Error('instructions required for ai_initiate');
              const result = await (initiator as any).initiateCall({
                instructions: params.instructions,
                phoneNumber: params.phone_number,
                contactName: params.contact_name,
                contactId: params.contact_id,
                locationId: params.location_id,
              });
              return json({ success: true, ...result });
            }

            case 'initiate': {
              if (!params.phone_number) throw new Error('phone_number required for initiate');
              const result = await (initiator as any).initiateCall({
                phoneNumber: params.phone_number,
                contactName: params.contact_name || 'Unknown',
                instructions: params.instructions || 'Have a professional conversation.',
                contactId: params.contact_id,
                locationId: params.location_id,
              });
              return json({ success: true, ...result });
            }

            case 'batch_call': {
              if (!params.filter_tag && !params.filter_pipeline) {
                throw new Error('filter_tag or filter_pipeline required for batch_call');
              }
              if (!params.instructions) throw new Error('instructions required for batch_call');

              const ghlPlugin = api.runtime?.getPlugin?.('gohighlevel') as any;
              const locationId = params.location_id;
              if (!ghlPlugin || !locationId) {
                throw new Error('GHL plugin and location_id required for batch_call');
              }

              // Query contacts by tag
              let contacts: any[] = [];
              if (params.filter_tag) {
                contacts = await ghlPlugin.tags?.getContactsByTag?.(locationId, params.filter_tag) || [];
              }

              if (contacts.length === 0) {
                return json({ success: true, message: 'No contacts found matching filter', total: 0 });
              }

              // For each contact, generate personalized prompt and initiate call
              const results: any[] = [];
              for (const contact of contacts) {
                try {
                  // Pull contact context for personalization
                  let contactContext: any = {};
                  try {
                    const [convos, tasks] = await Promise.allSettled([
                      ghlPlugin.conversations?.getAllContactMessages?.(locationId, contact.id, 5),
                      ghlPlugin.tasks?.getContactTasks?.(locationId, contact.id),
                    ]);
                    contactContext = {
                      conversations: convos.status === 'fulfilled' ? convos.value : [],
                      tasks: tasks.status === 'fulfilled' ? tasks.value : [],
                    };
                  } catch { /* proceed without context */ }

                  // Generate personalized prompt
                  const personalizedPrompt = await (initiator as any).generatePersonalizedPrompt(
                    params.instructions,
                    {
                      name: contact.contactName || contact.firstName || 'there',
                      tags: contact.tags || [],
                      conversations: contactContext.conversations || [],
                      tasks: contactContext.tasks || [],
                    }
                  );

                  // Initiate call
                  const callResult = await (initiator as any).initiateCall({
                    phoneNumber: contact.phone,
                    contactName: contact.contactName || contact.firstName || 'Unknown',
                    instructions: personalizedPrompt,
                    contactId: contact.id,
                    locationId,
                  });

                  results.push({ contactId: contact.id, name: contact.contactName, status: 'initiated', ...callResult });
                } catch (err) {
                  results.push({ contactId: contact.id, name: contact.contactName, status: 'failed', error: String(err) });
                }
              }

              return json({
                success: true,
                total: contacts.length,
                initiated: results.filter(r => r.status === 'initiated').length,
                failed: results.filter(r => r.status === 'failed').length,
                results,
              });
            }

            case 'status': {
              const roomName = params.room_name;
              if (!roomName) throw new Error('room_name required for status');
              const status = await bridge.getCallStatus(roomName);
              return json({ success: true, ...status });
            }

            default:
              return json({ error: `Unknown action: ${params.action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    });

    // Register lifecycle hooks for voice session integration
    api.on('session_start', async (event, ctx) => {
      // Initialize contact context for voice sessions
      if (ctx.channel === 'aime-voice') {
        const contactId = ctx.metadata?.contactId;
        if (contactId) {
          try {
            const bridge = initializeBridge();
            const context = await bridge.getContactContext(contactId);

            api.logger.info(`[AIME Voice] Loaded context for contact ${contactId}`);

            // Prepend context to agent prompt
            return {
              prependContext: context
            };
          } catch (error) {
            api.logger.error('[AIME Voice] Failed to load contact context:', error);
          }
        }
      }
    });

    api.on('session_end', async (event, ctx) => {
      // Process call transcript and update memory
      if (ctx.channel === 'aime-voice') {
        try {
          const bridge = initializeBridge();
          await bridge.syncCallToMemory(ctx.sessionKey);

          api.logger.info(`[AIME Voice] Synced session ${ctx.sessionKey} to memory`);
        } catch (error) {
          api.logger.error('[AIME Voice] Failed to sync call to memory:', error);
        }
      }
    });

    // Hook for post-call processing
    api.on('agent_end', async (event, ctx) => {
      if (ctx.channel === 'aime-voice' && ctx.metadata?.roomName) {
        try {
          const bridge = initializeBridge();

          // Extract transcript from event
          const transcript = event.messages?.map(m => m.content).join('\\n') || '';

          // Process transcript for tasks, sentiment, etc.
          await bridge.processTranscript({
            roomName: ctx.metadata.roomName,
            contactId: ctx.metadata.contactId,
            transcript,
            duration: ctx.metadata.duration
          });

          api.logger.info(`[AIME Voice] Processed transcript for ${ctx.metadata.roomName}`);
        } catch (error) {
          api.logger.error('[AIME Voice] Transcript processing error:', error);
        }
      }
    });

    api.logger.info('AIME Voice plugin registered');
  },

  activate(api: OpenClawPluginApi) {
    api.logger.info('AIME Voice plugin activated - LiveKit integration ready');
  }
};

export default aimeVoicePlugin;
