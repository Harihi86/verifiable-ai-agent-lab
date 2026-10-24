#!/usr/bin/env node
'use strict';
// Herdr `[[events]] on = "pane.agent_status_changed"` entrypoint.
// Exits 0 in every case so a plugin failure can never disturb Herdr's own lifecycle handling.

const { handleStatusEvent } = require('./lib/capture');

handleStatusEvent(process.env)
  .then((result) => {
    process.stdout.write(`${JSON.stringify({ plugin: 'research.agent-memory', ...result })}\n`);
    process.exit(0);
  })
  .catch((error) => {
    process.stdout.write(`${JSON.stringify({ plugin: 'research.agent-memory', captured: false, error: error.message })}\n`);
    process.exit(0);
  });
