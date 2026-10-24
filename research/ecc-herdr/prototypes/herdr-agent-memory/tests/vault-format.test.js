'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');

const format = require('../src/lib/vault-format');

function sample(overrides = {}) {
  const ts = '2026-10-24T08:00:00.000Z';
  return {
    schema: format.MEMORY_SCHEMA_VERSION,
    id: 'mem_abc123',
    title: 'Fix pane focus regression',
    kind: 'context',
    scope: 'project',
    trust: 'unreviewed',
    status: 'active',
    sourceAgent: 'claude',
    projectKey: 'p-0123456789ab',
    workspaceId: 'w1',
    paneId: 'w1:p1',
    tags: ['auto-capture', 'claude'],
    links: [],
    redactions: 0,
    createdAt: ts,
    updatedAt: ts,
    body: 'The focus bug came from stale pane ids after move.',
    ...overrides,
  };
}

test('serialize/parse round trip preserves every field', () => {
  const doc = format.serializeMemoryDocument(sample());
  assert.ok(doc.startsWith('---\nschema: "herdr.agent-memory.v1"\n'));
  const parsed = format.parseMemoryDocument(doc, 'sample.md');
  assert.deepEqual(parsed, format.normalizeMemory(sample()));
});

test('rejects foreign schema, bad ids, unknown kinds and oversized bodies', () => {
  assert.throws(() => format.normalizeMemory(sample({ schema: 'ecc.memory.v1' })), /Unsupported memory schema/);
  assert.throws(() => format.normalizeMemory(sample({ id: '../escape' })), /memory id/);
  assert.throws(() => format.normalizeMemory(sample({ kind: 'hook' })), /memory kind/);
  assert.throws(() => format.normalizeMemory(sample({ trust: 'reviewed' })), /memory trust/);
  assert.throws(() => format.normalizeMemory(sample({ body: 'x'.repeat(format.MAX_BODY_BYTES + 1) })), /too large/);
});

test('rejects control and bidirectional formatting characters in title and body', () => {
  assert.throws(() => format.normalizeMemory(sample({ title: 'bad' + String.fromCharCode(0x202e) + 'title' })), /control or bidirectional/);
  assert.throws(() => format.normalizeMemory(sample({ body: 'line\u0000null' })), /unsafe control/);
  // ordinary newlines and tabs are fine in the body
  format.normalizeMemory(sample({ body: 'a\n\tb' }));
});

test('parser refuses unknown and duplicate frontmatter fields', () => {
  const doc = format.serializeMemoryDocument(sample());
  assert.throws(() => format.parseMemoryDocument(doc.replace('title:', 'evil:'), 'x.md'), /missing fields|Unknown memory frontmatter/);
  const dup = doc.replace('---\n\n', 'kind: "note"\n---\n\n');
  assert.throws(() => format.parseMemoryDocument(dup, 'x.md'), /Duplicate memory frontmatter/);
});

test('secret detection and redaction cover the ECC pattern set', () => {
  const text = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 and AKIAABCDEFGHIJKLMNOP and -----BEGIN RSA PRIVATE KEY-----';
  const labels = format.findPotentialSecrets(text);
  assert.deepEqual(labels.sort(), ['AWS access key', 'GitHub token', 'private key']);
  const redacted = format.redactSecrets(text);
  assert.equal(redacted.count, 3);
  assert.equal(format.findPotentialSecrets(redacted.text).length, 0);
  assert.match(redacted.text, /\[REDACTED:github-token\]/);
});
