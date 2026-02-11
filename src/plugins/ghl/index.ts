/**
 * GoHighLevel Plugin for OpenClaw
 * Main entry point for GHL integration
 */

import { GHLAuth, MemorySessionStorage, RedisSessionStorage } from './auth.js';
import { GHLContacts } from './contacts.js';
import { GHLConversations } from './conversations.js';
import { GHLTasks } from './tasks.js';
import { GHLWebhooks } from './webhooks.js';
import type {
  GHLConfig,
  GHLPluginOptions,
  SessionStorage,
  GHLContact,
  GHLConversation,
  GHLMessage,
  GHLTask,
  ContactMemoryContext,
} from './types.js';

export * from './types.js';
export * from './auth.js';
export * from './contacts.js';
export * from './conversations.js';
export * from './tasks.js';
export * from './webhooks.js';

/**
 * Main GHL Plugin class
 */
export class GHLPlugin {
  public auth: GHLAuth;
  public contacts: GHLContacts;
  public conversations: GHLConversations;
  public tasks: GHLTasks;
  public webhooks: GHLWebhooks;

  private config: GHLConfig;
  private sessionStorage: SessionStorage;

  constructor(options: GHLPluginOptions) {
    this.config = options.config;

    // Initialize session storage (Redis or in-memory)
    if (options.redisUrl) {
      // TODO: Initialize Redis client
      // For now, using in-memory storage
      this.sessionStorage = new MemorySessionStorage();
    } else {
      this.sessionStorage = new MemorySessionStorage();
    }

    // Initialize authentication
    this.auth = new GHLAuth(this.config, this.sessionStorage);

    // Initialize service modules
    this.contacts = new GHLContacts(this.auth);
    this.conversations = new GHLConversations(this.auth);
    this.tasks = new GHLTasks(this.auth);
    this.webhooks = new GHLWebhooks(this.config.webhookSecret || '');
  }

  /**
   * Initialize the plugin with OpenClaw
   */
  async initialize(): Promise<void> {
    console.log('[GHL Plugin] Initializing GoHighLevel integration...');

    // Setup webhook handlers
    this.setupWebhookHandlers();

    console.log('[GHL Plugin] Initialization complete');
  }

  /**
   * Setup default webhook handlers
   */
  private setupWebhookHandlers(): void {
    this.webhooks.setupDefaultHandlers({
      onInboundMessage: async (event) => {
        console.log('[GHL Plugin] Inbound message received:', event.id);
        // This will be handled by the bridge layer
      },
      onContactCreate: async (event) => {
        console.log('[GHL Plugin] New contact created:', event.id);
      },
      onContactUpdate: async (event) => {
        console.log('[GHL Plugin] Contact updated:', event.id);
      },
      onTaskComplete: async (event) => {
        console.log('[GHL Plugin] Task completed:', event.id);
      },
      onAppointmentCreate: async (event) => {
        console.log('[GHL Plugin] Appointment created:', event.id);
      },
    });
  }

  /**
   * Build complete contact context for AI agent
   * This is the main function called by other parts of the system
   */
  async buildContactContext(
    locationId: string,
    contactId: string,
    options?: {
      maxMessages?: number;
      includeTasks?: boolean;
      includeAppointments?: boolean;
    }
  ): Promise<ContactMemoryContext> {
    // Get contact details
    const contact = await this.contacts.getContact(locationId, contactId);
    if (!contact) {
      throw new Error(`Contact ${contactId} not found`);
    }

    // Get conversation history
    const messages = await this.conversations.getAllContactMessages(
      locationId,
      contactId,
      options?.maxMessages || 50
    );

    // Group messages into conversation summaries
    const conversationSummaries = this.summarizeConversations(messages);

    // Get tasks if requested
    let tasks: GHLTask[] = [];
    if (options?.includeTasks !== false) {
      tasks = await this.contacts.getContactTasks(locationId, contactId);
    }

    // Get appointments if requested
    let appointments: any[] = [];
    if (options?.includeAppointments !== false) {
      appointments = await this.contacts.getContactAppointments(locationId, contactId);
    }

    // Get notes
    const notes = await this.contacts.getContactNotes(locationId, contactId);

    // Extract key facts from notes
    const keyFacts = notes.map((note) => note.body).slice(0, 5);

    // Build context object
    const context: ContactMemoryContext = {
      contactId: contact.id,
      contactName: contact.contactName || `${contact.firstName} ${contact.lastName}`.trim(),
      conversations: conversationSummaries,
      tasks: tasks.map((task) => ({
        title: task.title,
        dueDate: task.dueDate,
        completed: task.completed,
      })),
      appointments: appointments.map((apt) => ({
        title: apt.title,
        startTime: apt.startTime,
        status: apt.status,
      })),
      keyFacts,
      preferences: contact.customFields || {},
      lastInteraction:
        messages.length > 0 ? messages[0].dateAdded : contact.dateUpdated || contact.dateAdded || '',
    };

    return context;
  }

  /**
   * Summarize conversations by grouping messages
   */
  private summarizeConversations(messages: GHLMessage[]): Array<{
    date: string;
    channel: string;
    summary: string;
    sentiment?: string;
  }> {
    const summaries: Array<{
      date: string;
      channel: string;
      summary: string;
      sentiment?: string;
    }> = [];

    // Group messages by conversation (simplified - just take chunks of messages)
    const chunkSize = 10;
    for (let i = 0; i < messages.length; i += chunkSize) {
      const chunk = messages.slice(i, i + chunkSize);
      if (chunk.length === 0) continue;

      const date = new Date(chunk[0].dateAdded).toLocaleDateString();
      const channel = chunk[0].type;
      const preview = chunk
        .slice(0, 3)
        .map((m) => `${m.direction === 'inbound' ? 'Customer' : 'Agent'}: ${m.body.substring(0, 50)}`)
        .join(' | ');

      summaries.push({
        date,
        channel,
        summary: preview,
      });
    }

    return summaries;
  }

  /**
   * Format contact context as text for AI prompt
   */
  formatContextForAI(context: ContactMemoryContext): string {
    let formatted = `# Contact: ${context.contactName}\n\n`;

    formatted += `## Recent Conversations (${context.conversations.length})\n`;
    for (const conv of context.conversations.slice(0, 5)) {
      formatted += `- **${conv.date}** (${conv.channel}): ${conv.summary}\n`;
    }

    if (context.tasks.length > 0) {
      formatted += `\n## Active Tasks (${context.tasks.length})\n`;
      for (const task of context.tasks.filter((t) => !t.completed).slice(0, 5)) {
        formatted += `- [ ] ${task.title}${task.dueDate ? ` (due: ${new Date(task.dueDate).toLocaleDateString()})` : ''}\n`;
      }
    }

    if (context.appointments.length > 0) {
      formatted += `\n## Upcoming Appointments\n`;
      for (const apt of context.appointments.slice(0, 3)) {
        formatted += `- **${new Date(apt.startTime).toLocaleString()}**: ${apt.title} (${apt.status})\n`;
      }
    }

    if (context.keyFacts.length > 0) {
      formatted += `\n## Key Facts\n`;
      for (const fact of context.keyFacts) {
        formatted += `- ${fact}\n`;
      }
    }

    formatted += `\n**Last Interaction**: ${new Date(context.lastInteraction).toLocaleString()}\n`;

    return formatted;
  }
}

/**
 * Factory function to create GHL plugin instance
 */
export function createGHLPlugin(config: GHLConfig, options?: { redisUrl?: string }): GHLPlugin {
  return new GHLPlugin({
    config,
    redisUrl: options?.redisUrl,
  });
}

/**
 * Load GHL configuration from environment variables
 */
export function loadGHLConfigFromEnv(): GHLConfig {
  const clientId = process.env.GHL_CLIENT_ID;
  const clientSecret = process.env.GHL_CLIENT_SECRET;
  const redirectUri = process.env.GHL_REDIRECT_URI;

  if (!clientId || !clientSecret || !redirectUri) {
    throw new Error(
      'Missing required GHL configuration. Please set GHL_CLIENT_ID, GHL_CLIENT_SECRET, and GHL_REDIRECT_URI environment variables.'
    );
  }

  return {
    clientId,
    clientSecret,
    redirectUri,
    webhookSecret: process.env.GHL_WEBHOOK_SECRET,
    pitToken: process.env.GHL_PIT_TOKEN,
  };
}
