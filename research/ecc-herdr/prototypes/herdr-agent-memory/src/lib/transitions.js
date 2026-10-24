'use strict';
// Per-pane status memory so capture fires on a settle transition, not on every status event.

const fs = require('fs');
const path = require('path');

const DEFAULTS = Object.freeze({
  captureStates: ['idle', 'done'],
  requireWorkingTransition: true,
  cooldownMs: 15000,
});

function statePathFor(stateDir, paneId) {
  const safe = String(paneId).replace(/[^A-Za-z0-9_-]+/g, '_');
  return path.join(stateDir, 'transitions', `${safe}.json`);
}

function readState(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return { last_status: null, last_capture_at: 0, last_seen_at: 0 };
  }
}

function writeState(file, state) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(state), 'utf8');
  fs.renameSync(tmp, file);
}

/**
 * Decide whether this status event should trigger a capture, and record the observation.
 * Returns { capture, reason, previous }.
 */
function observeStatus(stateDir, paneId, status, options = {}, now = Date.now()) {
  const settings = { ...DEFAULTS, ...options };
  const file = statePathFor(stateDir, paneId);
  const previous = readState(file);
  let capture = false;
  let reason = 'not-a-capture-state';
  const lastCapture = previous.last_capture_at || 0;
  if (settings.captureStates.includes(status)) {
    if (settings.requireWorkingTransition && previous.last_status !== 'working') {
      reason = `no working->${status} transition (previous: ${previous.last_status || 'none'})`;
    } else if (lastCapture > 0 && now - lastCapture < settings.cooldownMs) {
      reason = 'cooldown';
    } else {
      capture = true;
      reason = `${previous.last_status || 'none'}->${status}`;
    }
  }
  writeState(file, {
    last_status: status,
    last_seen_at: now,
    last_capture_at: capture ? now : (previous.last_capture_at || 0),
  });
  return { capture, reason, previous };
}

module.exports = { DEFAULTS, observeStatus, statePathFor };
