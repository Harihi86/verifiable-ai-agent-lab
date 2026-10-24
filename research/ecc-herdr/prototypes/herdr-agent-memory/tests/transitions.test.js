'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { observeStatus } = require('../src/lib/transitions');

test('captures only on working -> idle/done, with cooldown', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-transitions-'));
  let now = 1_000_000;
  assert.equal(observeStatus(dir, 'w1:p1', 'idle', {}, now).capture, false, 'first idle has no working history');
  assert.equal(observeStatus(dir, 'w1:p1', 'working', {}, now += 1000).capture, false);
  const settled = observeStatus(dir, 'w1:p1', 'idle', {}, now += 1000);
  assert.equal(settled.capture, true);
  assert.equal(settled.reason, 'working->idle');
  assert.equal(observeStatus(dir, 'w1:p1', 'working', {}, now += 1000).capture, false);
  const tooSoon = observeStatus(dir, 'w1:p1', 'done', {}, now += 1000);
  assert.equal(tooSoon.capture, false);
  assert.equal(tooSoon.reason, 'cooldown');
  assert.equal(observeStatus(dir, 'w1:p1', 'working', {}, now += 20000).capture, false);
  assert.equal(observeStatus(dir, 'w1:p1', 'done', {}, now += 1000).capture, true);
  assert.equal(observeStatus(dir, 'w1:p1', 'blocked', {}, now += 1000).capture, false);
});

test('panes are tracked independently and ids are filename-safe', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-transitions-'));
  observeStatus(dir, 'w1:p1', 'working', {}, 1);
  observeStatus(dir, 'w2:p7', 'working', {}, 1);
  assert.equal(observeStatus(dir, 'w1:p1', 'idle', {}, 2).capture, true);
  assert.equal(observeStatus(dir, 'w2:p7', 'idle', {}, 2).capture, true);
  const files = fs.readdirSync(path.join(dir, 'transitions')).sort();
  assert.deepEqual(files, ['w1_p1.json', 'w2_p7.json']);
});

test('requireWorkingTransition=false captures every settle', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-memory-transitions-'));
  assert.equal(observeStatus(dir, 'w1:p1', 'idle', { requireWorkingTransition: false }, 1).capture, true);
});
