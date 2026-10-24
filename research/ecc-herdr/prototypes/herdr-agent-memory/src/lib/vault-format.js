'use strict';
// Adapted from ECC `scripts/lib/memory-vault-format.js` (MIT, Copyright (c) 2026 Affaan Mustafa).
// See THIRD-PARTY-NOTICES.md. Schema renamed and provenance fields added for Herdr.

const { TextDecoder } = require('util');

const MEMORY_SCHEMA_VERSION = 'herdr.agent-memory.v1';
const MEMORY_KINDS = Object.freeze([
  'context', 'decision', 'fact', 'handoff', 'lesson', 'note', 'preference', 'runbook',
]);
const MEMORY_SCOPES = Object.freeze(['project', 'session']);
const MEMORY_TRUST_STATES = Object.freeze(['unreviewed']);
const MEMORY_STATUSES = Object.freeze(['active', 'rejected', 'superseded']);

const MAX_BODY_BYTES = 64 * 1024;
const MAX_DOCUMENT_BYTES = 128 * 1024;
const MAX_TITLE_CHARS = 200;
const MAX_TAGS = 32;
const MAX_LINKS = 64;

const MEMORY_ID_PATTERN = /^mem_[a-z0-9][a-z0-9_-]{2,127}$/;
const SLUG_PATTERN = /^[a-z0-9][a-z0-9._:-]{0,63}$/;
const ISO_TIMESTAMP_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;

const FRONTMATTER_FIELDS = Object.freeze([
  ['schema', 'schema'],
  ['id', 'id'],
  ['title', 'title'],
  ['kind', 'kind'],
  ['scope', 'scope'],
  ['trust', 'trust'],
  ['status', 'status'],
  ['source_agent', 'sourceAgent'],
  ['project_key', 'projectKey'],
  ['workspace_id', 'workspaceId'],
  ['pane_id', 'paneId'],
  ['tags', 'tags'],
  ['links', 'links'],
  ['redactions', 'redactions'],
  ['created_at', 'createdAt'],
  ['updated_at', 'updatedAt'],
]);
const FRONTMATTER_KEYS = new Map(FRONTMATTER_FIELDS);
const FATAL_UTF8_DECODER = new TextDecoder('utf-8', { fatal: true });

// Secret indicators (from ECC). Writes containing a hit are refused unless redacted first.
const SECRET_PATTERNS = Object.freeze([
  { label: 'provider API key', pattern: /\bsk-[A-Za-z0-9_-]{16,}\b/i },
  { label: 'Stripe key', pattern: /\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b/ },
  { label: 'npm token', pattern: /\bnpm_[A-Za-z0-9]{20,}\b/ },
  { label: 'Hugging Face token', pattern: /\bhf_[A-Za-z0-9]{20,}\b/ },
  { label: 'GitHub token', pattern: /\bgh[pors]_[A-Za-z0-9]{16,}\b/ },
  { label: 'GitHub token', pattern: /\bgithub_pat_[A-Za-z0-9_]{16,}\b/ },
  { label: 'Google API key', pattern: /\bAIza[A-Za-z0-9_-]{16,}\b/ },
  { label: 'Slack token', pattern: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/ },
  { label: 'AWS access key', pattern: /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/ },
  { label: 'private key', pattern: /-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----/ },
]);

function hasUnsafeControlCharacters(value, allowBodyWhitespace = false) {
  return Array.from(value).some((character) => {
    const codePoint = character.codePointAt(0);
    const allowedWhitespace = allowBodyWhitespace
      && (codePoint === 0x09 || codePoint === 0x0a || codePoint === 0x0d);
    const isControl = (codePoint <= 0x1f && !allowedWhitespace)
      || (codePoint >= 0x7f && codePoint <= 0x9f);
    const isBidi = (codePoint >= 0x202a && codePoint <= 0x202e)
      || (codePoint >= 0x2066 && codePoint <= 0x2069);
    return isControl || isBidi;
  });
}

function asNonEmptyString(value, label, maxChars = 10000) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    throw new Error(`${label} must be a non-empty string.`);
  }
  const normalized = value.trim();
  if (normalized.length > maxChars) {
    throw new Error(`${label} is too long (maximum ${maxChars} characters).`);
  }
  if (hasUnsafeControlCharacters(normalized)) {
    throw new Error(`${label} must not contain control or bidirectional formatting characters.`);
  }
  return normalized;
}

function validateEnum(value, allowed, label) {
  const normalized = asNonEmptyString(value, label, 64);
  if (!allowed.includes(normalized)) {
    throw new Error(`${label} must be one of: ${allowed.join(', ')}.`);
  }
  return normalized;
}

function validateSlug(value, label) {
  const normalized = asNonEmptyString(value, label, 64);
  if (!SLUG_PATTERN.test(normalized)) {
    throw new Error(`${label} must be a lowercase letters/numbers slug.`);
  }
  return normalized;
}

function validateMemoryId(value) {
  const normalized = asNonEmptyString(value, 'memory id', 132);
  if (!MEMORY_ID_PATTERN.test(normalized)) {
    throw new Error('memory id must match mem_<lowercase-id> and cannot contain a path.');
  }
  return normalized;
}

function validateOptionalSlug(value, label) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  return validateSlug(value, label);
}

function uniqueStrings(values, { label, limit, validator }) {
  if (!Array.isArray(values)) {
    throw new Error(`${label} must be an array.`);
  }
  if (values.length > limit) {
    throw new Error(`${label} has too many values (maximum ${limit}).`);
  }
  return values.reduce((result, value) => {
    const normalized = validator(value);
    if (result.includes(normalized)) {
      throw new Error(`${label} must not contain duplicate values.`);
    }
    return [...result, normalized];
  }, []);
}

function validateTimestamp(value, label) {
  const normalized = asNonEmptyString(value, label, 64);
  const parsed = new Date(normalized);
  if (!ISO_TIMESTAMP_PATTERN.test(normalized) || Number.isNaN(parsed.getTime())
    || parsed.toISOString() !== normalized) {
    throw new Error(`${label} must be an ISO-8601 timestamp.`);
  }
  return normalized;
}

function validateRedactions(value) {
  if (value === undefined || value === null) {
    return 0;
  }
  if (!Number.isInteger(value) || value < 0 || value > 100000) {
    throw new Error('redactions must be a non-negative integer.');
  }
  return value;
}

function normalizeBody(value) {
  if (typeof value !== 'string') {
    throw new Error('memory body must be a string.');
  }
  if (hasUnsafeControlCharacters(value, true)) {
    throw new Error('memory body must not contain unsafe control or bidirectional formatting characters.');
  }
  const normalized = value.trim();
  if (normalized.length === 0) {
    throw new Error('memory body must contain non-whitespace context.');
  }
  if (Buffer.byteLength(normalized, 'utf8') > MAX_BODY_BYTES) {
    throw new Error(`memory body is too large (maximum ${MAX_BODY_BYTES} bytes).`);
  }
  return normalized;
}

function normalizeMemory(memory) {
  if (!memory || typeof memory !== 'object' || Array.isArray(memory)) {
    throw new Error('memory must be an object.');
  }
  if (memory.schema !== MEMORY_SCHEMA_VERSION) {
    throw new Error('Unsupported memory schema.');
  }
  return {
    schema: memory.schema,
    id: validateMemoryId(memory.id),
    title: asNonEmptyString(memory.title, 'memory title', MAX_TITLE_CHARS),
    kind: validateEnum(memory.kind, MEMORY_KINDS, 'memory kind'),
    scope: validateEnum(memory.scope, MEMORY_SCOPES, 'memory scope'),
    trust: validateEnum(memory.trust, MEMORY_TRUST_STATES, 'memory trust'),
    status: validateEnum(memory.status, MEMORY_STATUSES, 'memory status'),
    sourceAgent: validateSlug(memory.sourceAgent, 'source agent'),
    projectKey: validateSlug(memory.projectKey, 'project key'),
    workspaceId: validateOptionalSlug(memory.workspaceId, 'workspace id'),
    paneId: validateOptionalSlug(memory.paneId, 'pane id'),
    tags: uniqueStrings(memory.tags || [], { label: 'tags', limit: MAX_TAGS, validator: (v) => validateSlug(v, 'tag') }),
    links: uniqueStrings(memory.links || [], { label: 'links', limit: MAX_LINKS, validator: validateMemoryId }),
    redactions: validateRedactions(memory.redactions),
    createdAt: validateTimestamp(memory.createdAt, 'created_at'),
    updatedAt: validateTimestamp(memory.updatedAt, 'updated_at'),
    body: normalizeBody(memory.body),
  };
}

function serializeMemoryDocument(memory) {
  const normalized = normalizeMemory(memory);
  const metadata = FRONTMATTER_FIELDS
    .map(([serializedKey, objectKey]) => `${serializedKey}: ${JSON.stringify(normalized[objectKey])}`)
    .join('\n');
  return `---\n${metadata}\n---\n\n${normalized.body}\n`;
}

function decodeUtf8(buffer, label = 'text') {
  try {
    return FATAL_UTF8_DECODER.decode(buffer);
  } catch {
    throw new Error(`${label} must contain valid UTF-8 text.`);
  }
}

function parseFrontmatterLine(line, sourcePath, seen) {
  const separator = line.indexOf(':');
  if (separator <= 0) {
    throw new Error(`Invalid memory frontmatter line in ${sourcePath}.`);
  }
  const serializedKey = line.slice(0, separator).trim();
  const objectKey = FRONTMATTER_KEYS.get(serializedKey);
  if (!objectKey) {
    throw new Error(`Unknown memory frontmatter field in ${sourcePath}.`);
  }
  if (seen.has(objectKey)) {
    throw new Error(`Duplicate memory frontmatter field in ${sourcePath}.`);
  }
  const rawValue = line.slice(separator + 1).trim();
  try {
    return { objectKey, value: JSON.parse(rawValue) };
  } catch {
    throw new Error(`Memory frontmatter field in ${sourcePath} must use a JSON value.`);
  }
}

function parseMemoryDocument(source, sourcePath = '<memory>') {
  const openingMarker = typeof source === 'string' ? /^---\r?\n/.exec(source) : null;
  if (!openingMarker) {
    throw new Error(`Memory document ${sourcePath} must start with --- frontmatter.`);
  }
  if (Buffer.byteLength(source, 'utf8') > MAX_DOCUMENT_BYTES) {
    throw new Error(`Memory document ${sourcePath} is too large.`);
  }
  const remainder = source.slice(openingMarker[0].length);
  const closingMarker = /\r?\n---(?=\r?\n|$)/.exec(remainder);
  if (!closingMarker) {
    throw new Error(`Memory document ${sourcePath} has no closing frontmatter marker.`);
  }
  const frontmatterSource = remainder.slice(0, closingMarker.index);
  const seen = new Set();
  const values = {};
  for (const line of frontmatterSource.split(/\r?\n/)) {
    const next = parseFrontmatterLine(line, sourcePath, seen);
    values[next.objectKey] = next.value;
    seen.add(next.objectKey);
  }
  const missing = FRONTMATTER_FIELDS.map(([, k]) => k).filter((k) => !seen.has(k));
  if (missing.length > 0) {
    throw new Error(`Memory document ${sourcePath} is missing fields: ${missing.join(', ')}.`);
  }
  const afterMarker = remainder.slice(closingMarker.index + closingMarker[0].length);
  const body = afterMarker.replace(/^\r?\n/, '').replace(/\r?\n$/, '');
  return normalizeMemory({ ...values, body });
}

function findPotentialSecrets(value) {
  const text = typeof value === 'string' ? value : '';
  return SECRET_PATTERNS
    .filter((item) => item.pattern.test(text))
    .map((item) => item.label)
    .filter((label, index, labels) => labels.indexOf(label) === index);
}

/** Replace every secret match with a labelled placeholder. Returns { text, count }. */
function redactSecrets(value) {
  let text = typeof value === 'string' ? value : '';
  let count = 0;
  for (const item of SECRET_PATTERNS) {
    const global = new RegExp(item.pattern.source, item.pattern.flags.includes('g') ? item.pattern.flags : `${item.pattern.flags}g`);
    text = text.replace(global, () => {
      count += 1;
      return `[REDACTED:${item.label.replace(/\s+/g, '-').toLowerCase()}]`;
    });
  }
  return { text, count };
}

module.exports = {
  FRONTMATTER_FIELDS,
  MAX_BODY_BYTES,
  MAX_DOCUMENT_BYTES,
  MEMORY_KINDS,
  MEMORY_SCHEMA_VERSION,
  MEMORY_SCOPES,
  MEMORY_STATUSES,
  MEMORY_TRUST_STATES,
  SECRET_PATTERNS,
  asNonEmptyString,
  decodeUtf8,
  findPotentialSecrets,
  hasUnsafeControlCharacters,
  normalizeMemory,
  parseMemoryDocument,
  redactSecrets,
  serializeMemoryDocument,
  validateMemoryId,
  validateSlug,
};
