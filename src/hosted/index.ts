import { ulid } from 'ulid';
import { Workspace } from '../core/workspace.js';
import { D1Store, type D1Binding } from '../store/d1.js';
import { rpc } from '../mcp/server.js';

export interface Environment {
  DB: D1Binding;
  OWNER_USER_ID?: string;
  TRUST_PRIVATE_SITE?: string;
  WORKSPACE_TIMEZONE?: string;
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
});
async function boundedBody(request: Request): Promise<string> {
  if (!request.body) throw new Error('Empty request');
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 128000) { await reader.cancel(); throw new RangeError('Request exceeds 128000 bytes'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return new TextDecoder().decode(bytes);
}

/** Sites supplies trusted identity headers. No writes or schema changes before authentication. */
export default {
  async fetch(request: Request, env: Environment): Promise<Response> {
    const url = new URL(request.url);
    if (!env.OWNER_USER_ID && env.TRUST_PRIVATE_SITE !== 'true') return json({ error: 'Owner identity is not configured' }, 503);
    const principal = request.headers.get('oai-authenticated-user-id');
    const authorized = Boolean(principal && (!env.OWNER_USER_ID || principal === env.OWNER_USER_ID));
    if (!authorized && env.TRUST_PRIVATE_SITE !== 'true') return json({ error: 'Owner access required' }, 403);
    if (url.pathname !== '/mcp') return json({ service: 'Cognitive Workspace', transport: '/mcp' });
    if (request.method !== 'POST') return new Response(null, { status: 405, headers: { allow: 'POST' } });
    if (!request.headers.get('content-type')?.includes('application/json')) return json({ error: 'JSON required' }, 415);
    let message: unknown;
    try { message = JSON.parse(await boundedBody(request)); }
    catch (error) { return json({ jsonrpc: '2.0', id: null, error: { code: -32700, message: error instanceof RangeError ? error.message : 'Invalid JSON' } }, error instanceof RangeError ? 413 : 400); }
    // Sites may inspect schemas with its service identity while provisioning the plugin.
    // This path never reads notes or writes data; tool calls still require visitor identity.
    const method = message && typeof message === 'object' ? (message as { method?: string }).method : undefined;
    if (!authorized && !['server/discover','initialize','tools/list','ping'].includes(method ?? '')) return json({ error: 'Owner access required' }, 403);
    const workspace = new Workspace(new D1Store(env.DB), {
      id: prefix => `${prefix}_${ulid()}`,
      now: () => new Date().toISOString(),
      hash: async text => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), byte => byte.toString(16).padStart(2,'0')).join(''),
    }, principal ?? 'schema-discovery', 'chatgpt', env.WORKSPACE_TIMEZONE ?? 'America/Chicago');
    const result = await rpc(workspace, message);
    return result === undefined ? new Response(null, { status: 202 }) : json(result);
  },
};
