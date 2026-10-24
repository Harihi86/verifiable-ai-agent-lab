'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const store = require('../src/lib/vault-store');
const format = require('../src/lib/vault-format');

function tmpRoot() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-store-'));
}

function memory(overrides = {}) {
  const ts = overrides.createdAt || '2026-10-24T08:00:00.000Z';
  return {
    schema: format.MEMORY_SCHEMA_VERSION,
    id: store.newMemoryId(),
    title: 'Title',
    kind: 'context',
    scope: 'project',
    trust: 'unreviewed',
    status: 'active',
    sourceAgent: 'claude',
    projectKey: 'p-aaaaaaaaaaaa',
    workspaceId: null,
    paneId: null,
    tags: [],
    links: [],
    redactions: 0,
    createdAt: ts,
    updatedAt: ts,
    body: 'body',
    ...overrides,
  };
}

test('projectKeyFor is stable, slug-safe and anchored at the git root', () => {
  const root = tmpRoot();
  fs.mkdirSync(path.join(root, '.git'));
  const nested = path.join(root, 'src', 'deep');
  fs.mkdirSync(nested, { recursive: true });
  const a = store.projectKeyFor(root);
  const b = store.projectKeyFor(nested);
  assert.equal(a.key, b.key);
  assert.match(a.key, /^p-[0-9a-f]{12}$/);
  assert.equal(path.resolve(a.root), path.resolve(root));
  const other = store.projectKeyFor(tmpRoot());
  assert.notEqual(other.key, a.key);
});

test('createMemory is create-only, refuses secrets, and isolates projects', () => {
  const vault = path.join(tmpRoot(), 'vault');
  const first = memory({ id: 'mem_fixed-id01' });
  const file = store.createMemory(vault, first, { projectRoot: 'C:/x' });
  assert.ok(fs.existsSync(file));
  assert.throws(() => store.createMemory(vault, first), /already exists/);
  assert.throws(() => store.createMemory(vault, memory({ body: 'key sk-abcdefghijklmnopqrstuvwxyz' })), /potential secrets/);
  store.createMemory(vault, memory({ projectKey: 'p-bbbbbbbbbbbb', title: 'other project' }));
  assert.equal(store.listMemories(vault, 'p-aaaaaaaaaaaa').memories.length, 1);
  assert.equal(store.listMemories(vault, 'p-bbbbbbbbbbbb').memories.length, 1);
  assert.equal(store.listMemories(vault, 'p-cccccccccccc').memories.length, 0);
  const index = JSON.parse(fs.readFileSync(path.join(vault, 'index.json'), 'utf8'));
  assert.equal(index['p-aaaaaaaaaaaa'].root, 'C:/x');
});

test('invalid or tampered files are skipped and reported, never thrown', () => {
  const vault = path.join(tmpRoot(), 'vault');
  store.createMemory(vault, memory());
  fs.writeFileSync(path.join(vault, 'p-aaaaaaaaaaaa', 'mem_broken.md'), '---\nschema: "x"\n---\n', 'utf8');
  const listed = store.listMemories(vault, 'p-aaaaaaaaaaaa', { includeInvalid: true });
  assert.equal(listed.memories.length, 1);
  assert.equal(listed.invalid.length, 1);
  assert.match(listed.invalid[0].error, /missing fields|Unsupported/);
});

test('search ranks title > tags > body and recall respects the budget', () => {
  const vault = path.join(tmpRoot(), 'vault');
  store.createMemory(vault, memory({ title: 'unrelated', body: 'nothing here', createdAt: '2026-10-24T08:00:00.000Z', updatedAt: '2026-10-24T08:00:00.000Z' }));
  store.createMemory(vault, memory({ title: 'worktree cleanup', body: 'x', createdAt: '2026-10-24T08:01:00.000Z', updatedAt: '2026-10-24T08:01:00.000Z' }));
  store.createMemory(vault, memory({ title: 'notes', tags: ['worktree'], body: 'x', createdAt: '2026-10-24T08:02:00.000Z', updatedAt: '2026-10-24T08:02:00.000Z' }));
  store.createMemory(vault, memory({ title: 'notes2', body: 'worktree worktree worktree', createdAt: '2026-10-24T08:03:00.000Z', updatedAt: '2026-10-24T08:03:00.000Z' }));
  const { results } = store.searchMemories(vault, 'p-aaaaaaaaaaaa', 'worktree');
  assert.deepEqual(results.map((r) => r.memory.title), ['worktree cleanup', 'notes', 'notes2']);
  assert.deepEqual(results.map((r) => r.score), [8, 6, 3]);
  const digest = store.recallDigest(results, { budgetChars: 600, query: 'worktree' });
  assert.ok(digest.text.startsWith(store.RECALL_GUARD_HEADER));
  assert.ok(digest.chars <= 600 + 120, `digest ${digest.chars} chars`);
  assert.ok(digest.included >= 1 && digest.included < 3);
  assert.equal(digest.included + digest.omitted, 3);
});

test('empty query recalls most recent first', () => {
  const vault = path.join(tmpRoot(), 'vault');
  store.createMemory(vault, memory({ title: 'old', createdAt: '2026-10-24T08:00:00.000Z', updatedAt: '2026-10-24T08:00:00.000Z' }));
  store.createMemory(vault, memory({ title: 'new', createdAt: '2026-10-24T09:00:00.000Z', updatedAt: '2026-10-24T09:00:00.000Z' }));
  const { results } = store.searchMemories(vault, 'p-aaaaaaaaaaaa', '');
  assert.deepEqual(results.map((r) => r.memory.title), ['new', 'old']);
});
