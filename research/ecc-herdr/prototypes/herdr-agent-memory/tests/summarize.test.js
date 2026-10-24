'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');

const { stripAnsi, summarizeTranscript } = require('../src/lib/summarize');

const ESC = String.fromCharCode(27);
const BEL = String.fromCharCode(7);
const TRANSCRIPT = [
  `${ESC}[32m$ cargo test --workspace${ESC}[0m`,
  `${ESC}]0;claude${BEL}Compiling herdr v0.9.5`,
  'error[E0308]: mismatched types --> src/app/actions.rs:120:5',
  'error[E0308]: mismatched types --> src/app/actions.rs:120:5',
  'Fixed by editing src/app/actions.rs and tests/cli/agents.rs',
  'token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
  '',
  '> ready',
].join('\n');

test('stripAnsi removes CSI and OSC sequences', () => {
  assert.equal(stripAnsi(`${ESC}[32mok${ESC}[0m ${ESC}]0;title${BEL}x`), 'ok x');
});

test('summary extracts files, commands, errors, collapses repeats, and redacts secrets', () => {
  const summary = summarizeTranscript(TRANSCRIPT);
  assert.equal(summary.sourceLines, 6);
  assert.deepEqual(summary.files, ['src/app/actions.rs', 'tests/cli/agents.rs']);
  assert.deepEqual(summary.commands, ['cargo test --workspace', 'ready']);
  assert.equal(summary.errors.length, 1);
  assert.equal(summary.redactions, 1);
  assert.doesNotMatch(summary.body, /ghp_/);
  assert.match(summary.body, /\[REDACTED:github-token\]/);
  assert.match(summary.headline, /^error\[E0308\]/);
});

test('summary respects the character cap and keeps the code fence balanced', () => {
  const big = Array.from({ length: 500 }, (_, i) => `line ${i} ${'x'.repeat(50)}`).join('\n');
  const summary = summarizeTranscript(big, { maxLines: 200, maxChars: 1500 });
  assert.ok(summary.body.length <= 1550, `body ${summary.body.length}`);
  assert.equal((summary.body.match(/^```/gm) || []).length % 2, 0);
  assert.match(summary.body, /truncated/);
});

test('terminal chrome (footer hints, borders, telemetry banner) is dropped and never becomes the headline', () => {
  // Shape of a real Grok Build 1.0.67 screen captured through `herdr agent read` (research/07 R12).
  const grokScreen = [
    '  master C:/H/r/s/r/tmp/throwaway-repo        15K / 256K \u2502 [Dashboard]',
    '     \u2022 This repository exists only to validate Herdr-native agent dispatch.',
    '     Nothing was changed. The repository remains as it was.',
    '  Help improve Grok                                   [Opt out] [Opt in]',
    '  Off by default. Opt-in to allow SpaceXAI to retain coding data, e.g., prompts, traces, &',
    '  metrics, for training and debugging purposes. Change anytime via settings.',
    '  Read Terms and Privacy Policy.',
    '  \u256d\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256e',
    '  \u2502 >                                                                      \u2502',
    '  \u2570\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 Grok 4.7 (high) \u2500\u256f',
    '  Shift+Tab:mode  \u2502  Ctrl+x:shortcuts',
  ].join('\n');
  const summary = summarizeTranscript(grokScreen);
  assert.doesNotMatch(summary.headline, /shortcuts|Dashboard|Opt in|Grok 4\.7|training and debugging|Opt-in/);
  assert.match(summary.headline, /Nothing was changed/);
  assert.doesNotMatch(summary.body, /Ctrl\+x:shortcuts|Grok 4\.7 \(high\)/);
  assert.match(summary.body, /Nothing was changed/);
});

test('Codex footer chrome is dropped and the headline is the last content line', () => {
  // Shape of a real Codex CLI 0.163 screen captured through `herdr agent read` (research/07 R17).
  const codexScreen = [
    '\u2022 Called Read README.md',
    '  \u2514 - It contains one Python module, `src/hello.py`, that prints a greeting.',
    '\u2022 \u2022 Validates Herdr-native agent dispatch.',
    '  \u2022 Will be deleted after validation. No files changed; nothing remains to do.',
    '  Worked for 25s \u2022 17:49',
    '',
    '\u203a Ask Codex to do anything',
    '',
    '  GPT-6.1-Sol xhigh \u00b7 C:/tmp/throwaway-repo \u00b7 Validate Her\u2026',
    '  ? for shortcuts',
  ].join('\n');
  const summary = summarizeTranscript(codexScreen);
  assert.doesNotMatch(summary.headline, /shortcuts|Ask Codex/);
  assert.doesNotMatch(summary.body, /\? for shortcuts|Ask Codex to do anything/);
  assert.match(summary.body, /No files changed/);
});
