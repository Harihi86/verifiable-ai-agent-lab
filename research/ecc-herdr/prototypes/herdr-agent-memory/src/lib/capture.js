'use strict';
// Capture pipeline: Herdr event -> pane cwd -> recent output -> mechanical summary -> vault document.

const fs = require('fs');
const path = require('path');

const client = require('./herdr-client');
const store = require('./vault-store');
const format = require('./vault-format');
const { summarizeTranscript } = require('./summarize');
const { observeStatus } = require('./transitions');

const CONFIG_DEFAULTS = Object.freeze({
  lines: 120,
  max_summary_chars: 4000,
  capture_states: ['idle', 'done'],
  require_working_transition: true,
  cooldown_ms: 15000,
  report_metadata_token: true,
});

function loadConfig(env = process.env) {
  const dir = env.HERDR_PLUGIN_CONFIG_DIR;
  if (!dir) {
    return { ...CONFIG_DEFAULTS };
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(path.join(dir, 'config.json'), 'utf8'));
    return { ...CONFIG_DEFAULTS, ...parsed };
  } catch {
    return { ...CONFIG_DEFAULTS };
  }
}

/** Accept both the documented `{event, data:{...}}` envelope and a flat payload. */
function parseStatusEvent(raw) {
  if (!raw) {
    return null;
  }
  const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
  const data = parsed.data && typeof parsed.data === 'object' ? parsed.data : parsed;
  const paneId = data.pane_id;
  const status = data.agent_status || data.status;
  if (!paneId || !status) {
    return null;
  }
  return {
    event: parsed.event || parsed.type || 'pane.agent_status_changed',
    paneId,
    status,
    agent: data.agent || 'unknown',
    workspaceId: data.workspace_id || null,
  };
}

function paneCwd(paneId, env) {
  const result = client.herdrCli(['pane', 'get', paneId], { env });
  const pane = result.json && result.json.result && result.json.result.pane;
  if (!pane) {
    throw new Error(`pane get ${paneId} failed: ${result.stderr || result.stdout || result.error}`);
  }
  return { cwd: pane.foreground_cwd || pane.cwd, pane };
}

function readRecentOutput(paneId, lines, env) {
  // `agent read` prints text directly (not JSON); fall back to `pane read` when no agent holds the pane.
  const agentRead = client.herdrCli(['agent', 'read', paneId, '--source', 'recent-unwrapped', '--lines', String(lines)], { env });
  if (agentRead.status === 0) {
    return { text: agentRead.stdout, via: 'agent read' };
  }
  const paneRead = client.herdrCli(['pane', 'read', paneId, '--source', 'recent-unwrapped', '--lines', String(lines)], { env });
  if (paneRead.status === 0) {
    return { text: paneRead.stdout, via: 'pane read' };
  }
  throw new Error(`could not read pane ${paneId}: ${paneRead.stderr || agentRead.stderr}`);
}

/** Capture one memory for a pane. Returns a JSON-serialisable record of what happened. */
function capturePane({ paneId, agent, status, workspaceId }, { env = process.env, config = loadConfig(env), scope = 'project', kind = 'context', titleHint = null } = {}) {
  const vaultRoot = store.resolveVaultRoot(env);
  const { cwd } = paneCwd(paneId, env);
  const project = store.projectKeyFor(cwd);
  const output = readRecentOutput(paneId, config.lines, env);
  const summary = summarizeTranscript(output.text, { maxLines: Math.min(config.lines, 120), maxChars: config.max_summary_chars });
  if (summary.sourceLines === 0) {
    return { captured: false, reason: 'empty output', paneId, projectKey: project.key };
  }
  const agentSlug = store.toSlug(agent, 'unknown');
  const timestamp = store.nowIso();
  const memory = {
    schema: format.MEMORY_SCHEMA_VERSION,
    id: store.newMemoryId(),
    title: (titleHint || `${agentSlug} settled (${status}) in ${paneId}: ${summary.headline || 'no headline'}`).slice(0, 200),
    kind,
    scope,
    trust: 'unreviewed',
    status: 'active',
    sourceAgent: agentSlug,
    projectKey: project.key,
    workspaceId: workspaceId ? store.toSlug(workspaceId) : null,
    paneId: store.toSlug(paneId),
    tags: ['auto-capture', agentSlug, `status:${store.toSlug(status)}`],
    links: [],
    redactions: summary.redactions,
    createdAt: timestamp,
    updatedAt: timestamp,
    body: `Captured via ${output.via} from cwd ${project.root}.\n\n${summary.body}`,
  };
  const file = store.createMemory(vaultRoot, memory, { projectRoot: project.root });
  const count = store.stats(vaultRoot, project.key).count;
  return {
    captured: true,
    file,
    id: memory.id,
    paneId,
    agent: agentSlug,
    status,
    projectKey: project.key,
    projectRoot: project.root,
    redactions: summary.redactions,
    files: summary.files,
    bodyChars: memory.body.length,
    count,
  };
}

/** Event-hook entrypoint logic (pure function of env for testability). */
async function handleStatusEvent(env = process.env) {
  const started = Date.now();
  const event = parseStatusEvent(env.HERDR_PLUGIN_EVENT_JSON);
  if (!event) {
    return { skipped: true, reason: 'no parseable HERDR_PLUGIN_EVENT_JSON' };
  }
  const config = loadConfig(env);
  const stateDir = env.HERDR_AGENT_MEMORY_STATE || env.HERDR_PLUGIN_STATE_DIR;
  if (!stateDir) {
    return { skipped: true, reason: 'no HERDR_PLUGIN_STATE_DIR' };
  }
  const decision = observeStatus(stateDir, event.paneId, event.status, {
    captureStates: config.capture_states,
    requireWorkingTransition: config.require_working_transition,
    cooldownMs: config.cooldown_ms,
  });
  if (!decision.capture) {
    return { skipped: true, reason: decision.reason, pane_id: event.paneId, status: event.status };
  }
  const result = capturePane(event, { env, config });
  if (result.captured && config.report_metadata_token && env.HERDR_SOCKET_PATH) {
    try {
      await client.reportMetadataTokens(event.paneId, { memory: `${result.count} notes` }, { env });
      result.metadata_token = 'reported';
    } catch (error) {
      result.metadata_token = `skipped: ${error.message}`;
    }
  }
  result.elapsed_ms = Date.now() - started;
  return result;
}

module.exports = { CONFIG_DEFAULTS, capturePane, handleStatusEvent, loadConfig, parseStatusEvent };
