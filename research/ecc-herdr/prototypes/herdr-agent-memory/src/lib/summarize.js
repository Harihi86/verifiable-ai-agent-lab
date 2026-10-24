'use strict';
// Mechanical (non-LLM) summary of recent terminal output. Nothing here calls a model or executes text.

const { redactSecrets } = require('./vault-format');

// CSI, OSC (BEL or ST terminated), and other 2-byte escapes.
const ANSI_PATTERN = /\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]/g;
const FILE_PATTERN = /(?:[A-Za-z]:)?[\w./\\-]*[\w-]+\.(?:rs|py|js|cjs|mjs|ts|tsx|jsx|toml|json|jsonc|ya?ml|md|mdx|txt|sh|ps1|psm1|cmd|bat|sql|go|java|kt|swift|c|h|cpp|hpp|cs|rb|php|html|css|scss|lock|cfg|ini|env)\b/g;
const COMMAND_PATTERN = /^(?:\$|>|PS [^>]*>|❯|»)\s+(.+)$/;
const ERROR_PATTERN = /\b(error|failed|failure|exception|panic|traceback|denied|fatal)\b/i;

function stripAnsi(text) {
  return String(text || '').replace(ANSI_PATTERN, '');
}

// Terminal UI chrome that carries no task content: box borders, footer key hints, telemetry banners.
const CHROME_KEYWORDS = /(?:^|\s)(?:ctrl\+[a-z.]+|shift\+tab|esc):\S|\[(?:dashboard|opt out|opt in|stop)\]|help improve|terms and privacy|opt-in to allow|retain coding data|training and debugging|change anytime via settings|\b\d+k \/ \d+k\b/i;
const BOX_CHARS = /[─-╿▀-▟]/g;

function isChrome(line) {
  if (CHROME_KEYWORDS.test(line)) {
    return true;
  }
  const boxCount = (line.match(BOX_CHARS) || []).length;
  const content = line.replace(BOX_CHARS, '').trim();
  // Pure borders, an empty prompt box ("│ >"), or border-dominated lines such as "╰─── Grok 4.7 (high) ─╯".
  return boxCount > 0 && (content.length <= 2 || boxCount >= content.length);
}

function cleanLines(text, maxLines) {
  const lines = stripAnsi(text).replace(/\r\n?/g, '\n').split('\n').map((line) => line.replace(/\s+$/g, ''));
  const kept = [];
  for (const line of lines) {
    if (line.trim().length === 0 || isChrome(line)) {
      continue;
    }
    if (kept.length > 0 && kept[kept.length - 1] === line) {
      continue; // collapse exact repeats (spinners, progress reprints)
    }
    kept.push(line);
  }
  return kept.slice(-maxLines);
}

function unique(values, limit) {
  const seen = [];
  for (const value of values) {
    if (!seen.includes(value)) {
      seen.push(value);
      if (seen.length >= limit) {
        break;
      }
    }
  }
  return seen;
}

/**
 * Summarize terminal text into a bounded Markdown body plus structured hints.
 * Secrets are redacted (counted) so the vault accepts the document.
 */
function summarizeTranscript(text, { maxLines = 60, maxChars = 4000 } = {}) {
  const lines = cleanLines(text, maxLines);
  const files = unique(lines.join('\n').match(FILE_PATTERN) || [], 30)
    .filter((candidate) => !/^\d+\.\d+$/.test(candidate));
  const commands = unique(lines.map((line) => (COMMAND_PATTERN.exec(line) || [])[1]).filter(Boolean), 15);
  const errors = unique(lines.filter((line) => ERROR_PATTERN.test(line)), 10);

  const sections = [`### Recent output (last ${lines.length} lines)`, '```text', ...lines, '```'];
  if (files.length) {
    sections.push('', '### Files mentioned', ...files.map((file) => `- ${file}`));
  }
  if (commands.length) {
    sections.push('', '### Commands observed (not to be re-run)', ...commands.map((command) => `- \`${command}\``));
  }
  if (errors.length) {
    sections.push('', '### Error-like lines', ...errors.map((line) => `- ${line}`));
  }
  let body = sections.join('\n');
  if (body.length > maxChars) {
    body = `${body.slice(0, maxChars - 20).trimEnd()}\n[... truncated]`;
    // keep the code fence balanced if truncation cut inside it
    const fences = (body.match(/^```/gm) || []).length;
    if (fences % 2 === 1) {
      body += '\n```';
    }
  }
  const redacted = redactSecrets(body);
  const lastLine = lines.length ? lines[lines.length - 1] : '';
  return {
    body: redacted.text,
    redactions: redacted.count,
    files,
    commands,
    errors,
    sourceLines: lines.length,
    headline: (errors[0] || lastLine).slice(0, 80),
  };
}

module.exports = { stripAnsi, summarizeTranscript };
