/**
 * AIME Server
 * Main server that integrates all AIME components
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import Database from 'better-sqlite3';
import { createGHLPlugin, loadGHLConfigFromEnv } from './plugins/ghl/index.js';
import { ContactMemoryManager } from './memory/contact-memory/index.js';
import { createModelRouter } from './routing/model-router/index.js';
import { BridgeLayer } from './bridge/index.js';

const app = new Hono();

// Enable CORS
app.use('/*', cors());

// Global instances
let ghlPlugin: any;
let memoryManager: any;
let modelRouter: any;
let bridgeLayer: any;

/**
 * Initialize AIME platform
 */
async function initializeAIME() {
  console.log('🚀 Initializing AIME Platform...');

  // 1. Initialize GHL Plugin
  const ghlConfig = loadGHLConfigFromEnv();
  ghlPlugin = createGHLPlugin(ghlConfig, {
    redisUrl: process.env.REDIS_URL,
  });
  await ghlPlugin.initialize();
  console.log('✅ GHL Plugin initialized');

  // 2. Initialize Database
  const dbPath = process.env.DATABASE_PATH || './data/aime.db';
  const db = new Database(dbPath);
  console.log('✅ Database initialized');

  // 3. Initialize Contact Memory
  memoryManager = new ContactMemoryManager(ghlPlugin, db);
  await memoryManager.initialize(db);
  console.log('✅ Contact Memory initialized');

  // 4. Initialize Model Router
  modelRouter = createModelRouter();
  console.log('✅ Model Router initialized');

  // 5. Initialize Bridge Layer
  bridgeLayer = new BridgeLayer(ghlPlugin, memoryManager, modelRouter);
  await bridgeLayer.initialize();
  console.log('✅ Bridge Layer initialized');

  console.log('🎉 AIME Platform ready!');
}

/**
 * Health check
 */
app.get('/health', (c) => {
  return c.json({ status: 'healthy', timestamp: Date.now() });
});

/**
 * GHL OAuth callback
 */
app.get('/auth/ghl/callback', async (c) => {
  const code = c.req.query('code');

  if (!code) {
    return c.json({ error: 'No authorization code provided' }, 400);
  }

  try {
    const tokens = await ghlPlugin.auth.exchangeCodeForTokens(code);
    return c.json({ success: true, locationId: tokens.locationId });
  } catch (error) {
    return c.json({ error: String(error) }, 500);
  }
});

/**
 * GHL Webhooks
 */
app.post('/webhooks/ghl', async (c) => {
  const signature = c.req.header('x-ghl-signature');
  const body = await c.req.text();

  const result = await ghlPlugin.webhooks.processWebhook(body, signature);

  if (result.success) {
    return c.json({ success: true });
  } else {
    return c.json({ success: false, error: result.error }, 400);
  }
});

/**
 * Bridge API: Process completed call
 */
app.post('/api/bridge/process-call', async (c) => {
  const data = await c.req.json();
  const result = await bridgeLayer.processCall(data);
  return c.json(result);
});

/**
 * Bridge API: Get contact context
 */
app.get('/api/bridge/memory/context/:contactId', async (c) => {
  const contactId = c.req.param('contactId');
  const context = await bridgeLayer.getContactContext(contactId);
  return c.json(context);
});

/**
 * Bridge API: Lookup contact
 */
app.post('/api/bridge/contacts/lookup', async (c) => {
  const { location_id, phone } = await c.req.json();
  const contact = await bridgeLayer.lookupContact(location_id, phone);
  return c.json(contact);
});

/**
 * Bridge API: Check availability
 */
app.post('/api/bridge/appointments/availability', async (c) => {
  const { location_id, date, service_type } = await c.req.json();
  const slots = await bridgeLayer.checkAvailability(location_id, date, service_type);
  return c.json({ slots });
});

/**
 * Bridge API: Book appointment
 */
app.post('/api/bridge/appointments/book', async (c) => {
  const data = await c.req.json();
  const result = await bridgeLayer.bookAppointment({
    locationId: data.location_id || '',
    date: data.date,
    time: data.time,
    name: data.name,
    phone: data.phone,
    service: data.service,
  });
  return c.json(result);
});

/**
 * Bridge API: Create task
 */
app.post('/api/bridge/tasks/create', async (c) => {
  const data = await c.req.json();
  const task = await bridgeLayer.createTask(data);
  return c.json(task);
});

/**
 * Model Router API: Get cost report
 */
app.get('/api/router/cost-report', (c) => {
  const report = modelRouter.getCostReport();
  return c.text(report, 200, { 'Content-Type': 'text/plain' });
});

/**
 * Model Router API: Get metrics
 */
app.get('/api/router/metrics', (c) => {
  const metrics = modelRouter.getCostMetrics();
  return c.json(metrics);
});

/**
 * Contact Memory API: Sync contact
 */
app.post('/api/memory/sync/:locationId/:contactId', async (c) => {
  const locationId = c.req.param('locationId');
  const contactId = c.req.param('contactId');

  try {
    await memoryManager.syncContactFromGHL(locationId, contactId);
    return c.json({ success: true });
  } catch (error) {
    return c.json({ error: String(error) }, 500);
  }
});

/**
 * Contact Memory API: Get context
 */
app.get('/api/memory/context/:contactId', async (c) => {
  const contactId = c.req.param('contactId');
  const context = await memoryManager.getContactContext(contactId);
  return c.json(context);
});

/**
 * Contact Memory API: Search contacts
 */
app.get('/api/memory/search', async (c) => {
  const query = c.req.query('q') || '';
  const limit = parseInt(c.req.query('limit') || '10');
  const results = await memoryManager.searchContacts(query, limit);
  return c.json(results);
});

/**
 * Start server
 */
async function startServer() {
  await initializeAIME();

  const port = parseInt(process.env.PORT || '3000');
  console.log(`\n🌟 AIME Server running on http://localhost:${port}\n`);

  return app;
}

// Auto-start if running directly
if (import.meta.url === `file://${process.argv[1]}`) {
  startServer().then((app) => {
    const port = parseInt(process.env.PORT || '3000');
    console.log(`Server started on port ${port}`);
  });
}

export { app, startServer };
