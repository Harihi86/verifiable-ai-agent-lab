#!/usr/bin/env node
'use strict';
// Plugin CLI: recall | list | show | handoff | capture | stats
// Runs as a Herdr plugin action (--from-context) or directly by an orchestrator with --project <cwd>.

const fs = require('fs');

const client = require('./lib/herdr-client');
const store = require('./lib/vault-store');
const format = require('./lib/vault-format');
const { capturePane, loadConfig } = require('./lib/capture');

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      const next = argv[index + 1];
      if (next !== undefined && !next.startsWith('--')) {
        flags[key] = next;
        index += 1;
      } else {
        flags[key] = true;
      }
    } else {
      positional.push(arg);
    }
  }
  return { command: positional[0], positional: positional.slice(1), flags };
}

function contextFromEnv(env) {
  if (!env.HERDR_PLUGIN_CONTEXT_JSON) {
    return {};
  }
  try {
    return JSON.parse(env.HERDR_PLUGIN_CONTEXT_JSON);
  } catch {
    return {};
  }
}

/** Resolve the project working directory from flags, plugin context, or the caller's cwd. */
function resolveProjectCwd(flags, env) {
  if (flags.project) {
    return { cwd: flags.project, via: '--project' };
  }
  if (flags['from-context']) {
    const context = contextFromEnv(env);
    const direct = (context.workspace && context.workspace.cwd) || (context.pane && context.pane.cwd) || context.cwd;
    if (direct) {
      return { cwd: direct, via: 'context json' };
    }
    const paneId = context.pane_id || (context.pane && context.pane.pane_id) || env.HERDR_PANE_ID;
    if (paneId && env.HERDR_BIN_PATH) {
      const result = client.herdrCli(['pane', 'get', paneId], { env });
      const pane = result.json && result.json.result && result.json.result.pane;
      if (pane && (pane.foreground_cwd || pane.cwd)) {
        return { cwd: pane.foreground_cwd || pane.cwd, via: `pane get ${paneId}` };
      }
    }
    const workspaceId = context.workspace_id || env.HERDR_WORKSPACE_ID;
    if (workspaceId && env.HERDR_BIN_PATH) {
      const result = client.herdrCli(['pane', 'list', '--workspace', workspaceId], { env });
      const panes = result.json && result.json.result && result.json.result.panes;
      if (Array.isArray(panes) && panes.length && panes[0].cwd) {
        return { cwd: panes[0].cwd, via: `pane list --workspace ${workspaceId}` };
      }
    }
  }
  return { cwd: process.cwd(), via: 'process cwd' };
}

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function main(argv, env = process.env) {
  const { command, positional, flags } = parseArgs(argv);
  const out = (value) => process.stdout.write(typeof value === 'string' ? `${value}\n` : `${JSON.stringify(value, null, flags.json ? 2 : 0)}\n`);

  if (!command || command === 'help') {
    out('usage: cli.js <recall [query]|list|show <id>|handoff|capture --pane <id>|stats> [--project <cwd>] [--from-context] [--json]');
    return 0;
  }

  const vaultRoot = store.resolveVaultRoot(env);
  const { cwd, via } = resolveProjectCwd(flags, env);
  const project = store.projectKeyFor(cwd);

  switch (command) {
    case 'recall': {
      const query = flags.query || positional.join(' ');
      const limit = Number(flags.limit || 20);
      const budget = Number(flags.budget || 8000);
      const { results, invalid } = store.searchMemories(vaultRoot, project.key, query, { limit });
      const digest = store.recallDigest(results, { budgetChars: budget, query });
      if (flags.json) {
        out({ project_key: project.key, project_root: project.root, resolved_via: via, included: digest.included, omitted: digest.omitted, chars: digest.chars, invalid, digest: digest.text });
      } else {
        out(digest.text);
      }
      return 0;
    }
    case 'list': {
      const { memories, invalid } = store.listMemories(vaultRoot, project.key);
      out({
        project_key: project.key,
        project_root: project.root,
        resolved_via: via,
        count: memories.length,
        invalid,
        memories: memories.slice(0, Number(flags.limit || 50)).map((entry) => ({
          id: entry.memory.id, kind: entry.memory.kind, agent: entry.memory.sourceAgent, created_at: entry.memory.createdAt, title: entry.memory.title, redactions: entry.memory.redactions,
        })),
      });
      return 0;
    }
    case 'show': {
      const id = positional[0];
      const { memories } = store.listMemories(vaultRoot, project.key);
      const found = memories.find((entry) => entry.memory.id === id);
      if (!found) {
        out({ error: `memory not found: ${id}` });
        return 1;
      }
      out(flags.json ? found.memory : fs.readFileSync(found.file, 'utf8'));
      return 0;
    }
    case 'handoff': {
      const body = flags.body || readStdin().trim();
      if (!body) {
        out({ error: 'handoff requires --body or stdin text' });
        return 1;
      }
      const context = contextFromEnv(env);
      const timestamp = store.nowIso();
      const memory = {
        schema: format.MEMORY_SCHEMA_VERSION,
        id: store.newMemoryId(),
        title: (flags.title || `handoff from ${flags.agent || 'operator'}`).slice(0, 200),
        kind: 'handoff',
        scope: 'project',
        trust: 'unreviewed',
        status: 'active',
        sourceAgent: store.toSlug(flags.agent || 'operator', 'operator'),
        projectKey: project.key,
        workspaceId: context.workspace_id ? store.toSlug(context.workspace_id) : null,
        paneId: context.pane_id ? store.toSlug(context.pane_id) : null,
        tags: ['handoff', ...(flags.tags ? String(flags.tags).split(',').map((tag) => store.toSlug(tag)) : [])],
        links: [],
        redactions: 0,
        createdAt: timestamp,
        updatedAt: timestamp,
        body,
      };
      try {
        const file = store.createMemory(vaultRoot, memory, { projectRoot: project.root });
        out({ written: file, id: memory.id, project_key: project.key });
        return 0;
      } catch (error) {
        out({ error: error.message });
        return 1;
      }
    }
    case 'capture': {
      const paneId = flags.pane || env.HERDR_PANE_ID;
      if (!paneId) {
        out({ error: 'capture requires --pane <id>' });
        return 1;
      }
      const result = capturePane({ paneId, agent: flags.agent || 'manual', status: 'manual', workspaceId: env.HERDR_WORKSPACE_ID || null }, { env, config: loadConfig(env), kind: flags.kind || 'context', titleHint: flags.title || null });
      out(result);
      return result.captured ? 0 : 1;
    }
    case 'stats': {
      out({ project_key: project.key, project_root: project.root, resolved_via: via, ...store.stats(vaultRoot, project.key) });
      return 0;
    }
    default:
      out({ error: `unknown command: ${command}` });
      return 2;
  }
}

if (require.main === module) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (error) {
    process.stdout.write(`${JSON.stringify({ error: error.message })}\n`);
    process.exit(1);
  }
}

module.exports = { main, parseArgs, resolveProjectCwd };
