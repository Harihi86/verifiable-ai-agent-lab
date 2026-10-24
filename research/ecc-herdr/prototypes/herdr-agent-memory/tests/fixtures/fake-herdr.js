#!/usr/bin/env node
'use strict';
// Fake Herdr CLI for unit tests. Emulates the few commands the plugin uses.
// Controlled by env: FAKE_HERDR_CWD, FAKE_HERDR_READ_TEXT, FAKE_HERDR_FAIL_AGENT_READ=1

const args = process.argv.slice(2);
const [group, verb, target] = args;

function ok(result) {
  process.stdout.write(`${JSON.stringify({ id: 'fake', result })}\n`);
  process.exit(0);
}

function fail(code, message) {
  process.stderr.write(`${JSON.stringify({ id: 'fake', error: { code, message } })}\n`);
  process.exit(1);
}

const DEFAULT_TEXT = [
  '\u001b[32m$ cargo test --workspace\u001b[0m',
  'Compiling herdr v0.9.5 (C:\\work\\repo)',
  'warning: unused variable `x` in src/pane/terminal.rs',
  'test result: FAILED. 1 failed; 212 passed',
  'error[E0308]: mismatched types --> src/app/actions.rs:120:5',
  'token leaked by mistake: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
  'Fixed by editing src/app/actions.rs and tests/cli/agents.rs',
  '\u001b]0;claude\u0007',
  '> ready for input',
].join('\n');

if (group === 'pane' && verb === 'get') {
  ok({ type: 'pane_info', pane: { pane_id: target, workspace_id: 'w1', tab_id: 'w1:t1', cwd: process.env.FAKE_HERDR_CWD || process.cwd(), agent: 'claude', agent_status: 'idle' } });
}
if (group === 'pane' && verb === 'list') {
  ok({ type: 'pane_list', panes: [{ pane_id: 'w1:p1', workspace_id: 'w1', cwd: process.env.FAKE_HERDR_CWD || process.cwd() }] });
}
if (group === 'agent' && verb === 'read') {
  if (process.env.FAKE_HERDR_FAIL_AGENT_READ === '1') {
    fail('agent_not_found', 'no agent in pane');
  }
  process.stdout.write(process.env.FAKE_HERDR_READ_TEXT || DEFAULT_TEXT);
  process.exit(0);
}
if (group === 'pane' && verb === 'read') {
  process.stdout.write(process.env.FAKE_HERDR_READ_TEXT || DEFAULT_TEXT);
  process.exit(0);
}
fail('unknown_method', `fake herdr does not implement: ${args.join(' ')}`);
