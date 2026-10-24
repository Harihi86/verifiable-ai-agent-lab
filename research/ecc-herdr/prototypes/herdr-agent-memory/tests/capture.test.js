'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { handleStatusEvent, parseStatusEvent, capturePane } = require('../src/lib/capture');
const store = require('../src/lib/vault-store');
const cli = require('../src/cli');

const FAKE = path.join(__dirname, 'fixtures', 'fake-herdr.js');

function makeEnv(extra = {}) {
  const state = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-state-'));
  const config = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-config-'));
  const project = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-project-'));
  fs.mkdirSync(path.join(project, '.git'));
  return {
    env: {
      PATH: process.env.PATH,
      SystemRoot: process.env.SystemRoot || '',
      HERDR_BIN_PATH: FAKE,
      HERDR_PLUGIN_STATE_DIR: state,
      HERDR_PLUGIN_CONFIG_DIR: config,
      FAKE_HERDR_CWD: project,
      ...extra,
    },
    state,
    config,
    project,
  };
}

function statusEvent(status, paneId = 'w1:p1', agent = 'claude') {
  return JSON.stringify({ event: 'pane.agent_status_changed', data: { pane_id: paneId, agent, agent_status: status, workspace_id: 'w1' } });
}

test('parseStatusEvent accepts envelope and flat shapes', () => {
  assert.deepEqual(parseStatusEvent(statusEvent('idle')), { event: 'pane.agent_status_changed', paneId: 'w1:p1', status: 'idle', agent: 'claude', workspaceId: 'w1' });
  assert.equal(parseStatusEvent(JSON.stringify({ pane_id: 'w1:p2', agent_status: 'done' })).status, 'done');
  assert.equal(parseStatusEvent('{}'), null);
});

test('event hook captures on working->idle, writes a vault file, skips otherwise', async () => {
  const { env, state, project } = makeEnv();
  const first = await handleStatusEvent({ ...env, HERDR_PLUGIN_EVENT_JSON: statusEvent('working') });
  assert.equal(first.skipped, true);
  const second = await handleStatusEvent({ ...env, HERDR_PLUGIN_EVENT_JSON: statusEvent('idle') });
  assert.equal(second.captured, true, JSON.stringify(second));
  assert.equal(second.agent, 'claude');
  assert.equal(second.redactions, 1, 'the fake transcript contains one GitHub token');
  assert.ok(fs.existsSync(second.file));
  assert.ok(second.file.startsWith(path.join(state, 'vault')), 'memory must live under the plugin state dir');
  assert.ok(!fs.existsSync(path.join(project, '.herdr')) && !fs.existsSync(path.join(project, '.ecc')), 'never writes into the project');
  const doc = fs.readFileSync(second.file, 'utf8');
  assert.doesNotMatch(doc, /ghp_/);
  assert.match(doc, /source_agent: "claude"/);
  assert.match(doc, /src\/app\/actions\.rs/);
  assert.match(second.metadata_token || 'skipped', /skipped/, 'no socket in unit tests');
  const third = await handleStatusEvent({ ...env, HERDR_PLUGIN_EVENT_JSON: statusEvent('idle') });
  assert.equal(third.skipped, true);
});

test('cross-agent: codex and grok captures land in the same project vault and recall sees both', async () => {
  const { env, project } = makeEnv();
  for (const agent of ['codex', 'grok']) {
    await handleStatusEvent({ ...env, HERDR_PLUGIN_EVENT_JSON: statusEvent('working', `w1:p${agent.length}`, agent) });
    const result = await handleStatusEvent({ ...env, HERDR_PLUGIN_EVENT_JSON: statusEvent('idle', `w1:p${agent.length}`, agent) });
    assert.equal(result.captured, true, JSON.stringify(result));
  }
  const vault = store.resolveVaultRoot(env);
  const key = store.projectKeyFor(project).key;
  const stats = store.stats(vault, key);
  assert.equal(stats.count, 2);
  assert.deepEqual(Object.keys(stats.by_agent).sort(), ['codex', 'grok']);
  const { results } = store.searchMemories(vault, key, 'actions.rs');
  assert.equal(results.length, 2);
  const digest = store.recallDigest(results, { budgetChars: 8000 });
  assert.equal(digest.included, 2);
  assert.match(digest.text, /HISTORICAL REFERENCE ONLY/);
});

test('manual capture falls back to pane read when no agent holds the pane', () => {
  const { env } = makeEnv({ FAKE_HERDR_FAIL_AGENT_READ: '1' });
  const result = capturePane({ paneId: 'w1:p1', agent: 'manual', status: 'manual', workspaceId: null }, { env });
  assert.equal(result.captured, true);
  assert.match(fs.readFileSync(result.file, 'utf8'), /Captured via pane read/);
});

test('cli handoff + recall + list + stats work with --project', () => {
  const { env, project } = makeEnv();
  const chunks = [];
  const original = process.stdout.write.bind(process.stdout);
  process.stdout.write = (chunk) => { chunks.push(String(chunk)); return true; };
  try {
    assert.equal(cli.main(['handoff', '--project', project, '--title', 'Next steps', '--body', 'Finish the worktree cleanup; tests in tests/cli/workspace.rs', '--agent', 'codex'], env), 0);
    assert.equal(cli.main(['recall', 'worktree', '--project', project], env), 0);
    assert.equal(cli.main(['list', '--project', project], env), 0);
    assert.equal(cli.main(['stats', '--project', project], env), 0);
    assert.equal(cli.main(['handoff', '--project', project, '--body', 'leak sk-abcdefghijklmnopqrstuvwxyz'], env), 1);
  } finally {
    process.stdout.write = original;
  }
  const out = chunks.join('');
  assert.match(out, /"written"/);
  assert.match(out, /\[handoff\] Next steps/);
  assert.match(out, /"count":1/);
  assert.match(out, /potential secrets/);
});
