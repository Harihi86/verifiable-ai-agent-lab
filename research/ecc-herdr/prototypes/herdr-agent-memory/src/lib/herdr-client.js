'use strict';
// Calls back into the Herdr that owns this plugin process. Never falls back to a bare `herdr` on PATH.

const { spawnSync } = require('child_process');
const net = require('net');
const path = require('path');

function resolveHerdrInvocation(env = process.env) {
  const binary = env.HERDR_BIN_PATH;
  if (!binary) {
    throw new Error('HERDR_BIN_PATH is not set; this program only runs as a Herdr plugin command.');
  }
  // Test seam: a `.js` HERDR_BIN_PATH is executed with the current Node binary.
  if (binary.toLowerCase().endsWith('.js')) {
    return { command: process.execPath, prefix: [binary] };
  }
  if (!path.isAbsolute(binary)) {
    throw new Error('HERDR_BIN_PATH must be an absolute path.');
  }
  return { command: binary, prefix: [] };
}

/** Run a Herdr CLI command. Returns { status, stdout, stderr, json }. */
function herdrCli(args, { env = process.env, timeoutMs = 15000 } = {}) {
  const { command, prefix } = resolveHerdrInvocation(env);
  const result = spawnSync(command, [...prefix, ...args], {
    env,
    encoding: 'utf8',
    timeout: timeoutMs,
    windowsHide: true,
    maxBuffer: 8 * 1024 * 1024,
  });
  const stdout = result.stdout || '';
  const stderr = result.stderr || '';
  let json = null;
  for (const candidate of [stdout, stderr]) {
    const text = candidate.trim();
    if (text.startsWith('{')) {
      try {
        json = JSON.parse(text);
        break;
      } catch {
        json = null;
      }
    }
  }
  return { status: result.status, stdout, stderr, json, error: result.error || null };
}

function pipeNameFor(socketPath) {
  if (process.platform !== 'win32') {
    return socketPath;
  }
  if (/^\\\\[.?]\\pipe\\/i.test(socketPath)) {
    return socketPath;
  }
  return `\\\\.\\pipe\\${socketPath}`;
}

/** One raw JSON request on a fresh connection to HERDR_SOCKET_PATH. */
function rawRequest(method, params = {}, { env = process.env, timeoutMs = 5000 } = {}) {
  const socketPath = env.HERDR_SOCKET_PATH;
  if (!socketPath) {
    return Promise.reject(new Error('HERDR_SOCKET_PATH is not set.'));
  }
  const id = `plugin:${method}:${Date.now().toString(36)}`;
  return new Promise((resolve, reject) => {
    const socket = net.connect(pipeNameFor(socketPath));
    let buffer = '';
    const timer = setTimeout(() => {
      socket.destroy();
      reject(new Error(`timeout waiting for ${method}`));
    }, timeoutMs);
    socket.setEncoding('utf8');
    socket.on('connect', () => {
      socket.write(`${JSON.stringify({ id, method, params })}\n`);
    });
    socket.on('data', (chunk) => {
      buffer += chunk;
      const newline = buffer.indexOf('\n');
      if (newline !== -1) {
        clearTimeout(timer);
        const line = buffer.slice(0, newline);
        socket.end();
        try {
          resolve(JSON.parse(line));
        } catch (error) {
          reject(error);
        }
      }
    });
    socket.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

/** Display-only pane tokens (e.g. memory count). Never affects lifecycle state. */
function reportMetadataTokens(paneId, tokens, { source = 'plugin:research.agent-memory', ttlMs = null, env = process.env } = {}) {
  const params = { pane_id: paneId, source, tokens };
  if (ttlMs) {
    params.ttl_ms = ttlMs;
  }
  return rawRequest('pane.report_metadata', params, { env });
}

module.exports = { herdrCli, pipeNameFor, rawRequest, reportMetadataTokens, resolveHerdrInvocation };
