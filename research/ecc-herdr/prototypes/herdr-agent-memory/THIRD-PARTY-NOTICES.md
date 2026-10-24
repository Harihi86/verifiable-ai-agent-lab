# Third-party notices

This research prototype adapts design and code from the ECC project
(https://github.com/affaan-m/ECC, package `ecc-universal` 2.2.3, commit
`90606c8315ee09cafc303515c5f33024db6b9882`), which is licensed under the MIT License.

Adapted material (all in `src/lib/vault-format.js` and `src/lib/vault-store.js`):

- `scripts/lib/memory-vault-format.js`: memory document shape (JSON-valued Markdown frontmatter),
  kind / scope / trust / status vocabularies, size limits, id and slug patterns, control-character and
  bidirectional-formatting rejection, the `SECRET_PATTERNS` list, and the frontmatter parser/serializer.
- `scripts/lib/memory-vault.js`: create-only write discipline (exclusive temp file + rename) and the
  lexical scoring weights (title x8, tags x6, bounded body hits).
- `scripts/hooks/session-start.js` / `session-end.js`: the "HISTORICAL REFERENCE ONLY" recall wrapper,
  the bounded recall budget (8000 chars), and the idea of a mechanical (non-LLM) session summary.

Changes made here: the schema identifier is `herdr.agent-memory.v1`; provenance fields
(`source_agent`, `pane_id`, `workspace_id`, `project_key`, `redactions`) were added; storage lives under
Herdr's `HERDR_PLUGIN_STATE_DIR` instead of the user's repository or home directory; capture is driven by
Herdr `pane.agent_status_changed` events; no LLM is invoked and no content is ever injected automatically.

## MIT License (ECC)

MIT License

Copyright (c) 2026 Affaan Mustafa

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
