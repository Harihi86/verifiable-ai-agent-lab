# Provenance and baseline record

Recorded: 2026-10-24 (local), host `<research-host>` (Windows 11 Pro 10.0.26300), user `<user>`.
Executor: Claude Code (Claude Fable 5.1) in the Claude Desktop Code tab, running locally on this Windows machine.
Primary working directory: `C:\Herdr-dev` (empty before this project started; inspected 2026-10-24 ~16:00).

## Protected source (read-only)

| Item | Value |
|---|---|
| Path | `C:\herdr` |
| HEAD | `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01` |
| Branch | `dev/architecture` |
| `git describe --tags` | `v0.9.5` |
| Tree hash | `8aa25836bb7c8d14ffa866a852dbc724098ca088` |
| Working tree | clean (no modified or untracked tracked-area files; `.local/` is gitignored) |
| Remote | `origin https://github.com/herdrdev/herdr.git` (fetch refspec limited to `refs/tags/v0.9.5`) |
| Worktrees / alternates / submodules | none |
| Shallow | no (25,535 objects in one pack) |

The expected baseline (v0.9.5, commit `2ecf19a9…`) matches what is actually present. No difference to report.
`C:\herdr\.local\<private-migration-note>` (migration note dated 2026-10-24) confirms the same baseline, that no product source
was modified locally, that the production binary is `C:\herdr\.local\<private>`, that all local Herdr
processes were stopped, and that the cross-machine connection is intentionally paused.

## Handoff archive

`Herdr-v0.9.5-research-source.zip` and `Herdr-research-baseline.json` were searched for under `C:\Herdr-dev`,
`%USERPROFILE%`, `Downloads`, `Desktop`, `Documents` and `C:\herdr` (depth 2). **Neither exists on this machine.**
Because the protected Git repository itself is available locally, the independent copy was made directly from it
(see below) instead of from an archive; full upstream history is therefore retained.

## Independent Herdr research repository

| Item | Value |
|---|---|
| Path | `C:\Herdr-dev\herdr` |
| Method | `git clone --no-local --no-hardlinks file:///c/herdr herdr` (objects copied through the pack protocol; no hard links, no alternates, no shared metadata) |
| Verified | HEAD `2ecf19a9…`, tree hash `8aa25836…` identical to protected source; `git worktree list` shows only itself; `.git/objects/info/alternates` absent |
| Remote | reset to `https://github.com/herdrdev/herdr.git` (so nothing points back at `C:\herdr`) |
| Research branch | `research/ecc-integration` created from `dev/architecture` @ `2ecf19a9` |
| Local commit identity | `<user> <<redacted-email>>` (repo-local config only; `commit.gpgsign=false`) |
| `.githooks` | inactive (no `core.hooksPath`); commit style follows `scripts/conventional_commits.py` manually |

All later commits on `research/ecc-integration` are **research commits**, not upstream history.

## ECC source

| Item | Value |
|---|---|
| Requested | `https://github.com/affaan-m/ECC` |
| Resolved (`gh api repos/affaan-m/ECC`) | `full_name=affaan-m/ECC`, `html_url=https://github.com/affaan-m/ECC`, no redirect, not a fork, not archived |
| Default branch | `main` |
| License (GitHub metadata) | MIT |
| Pinned commit | `90606c8315ee09cafc303515c5f33024db6b9882` (2026-10-20 17:28:23 -0400, "docs: correct MODULE_NOT_FOUND plugin cache path (#3586)") |
| Package | `ecc-universal` 2.2.3 (`VERSION`, `package.json`); latest tag `v2.2.3` |
| Path | `C:\Herdr-dev\ecc` (plain `git clone`; untrusted third-party content, never executed) |

Note: the clone initially landed at `C:\Herdr-dev\herdr\ecc` because two parallel shell calls shared a working
directory; it was moved to `C:\Herdr-dev\ecc` with `mv` before any Git operation in the Herdr clone. The Herdr clone
showed only an untracked directory during that interval and is clean afterwards.

## Workspace-local Herdr binary (for disposable backend tests only)

Downloaded the official release asset `herdr-windows-x86_64.zip` (GitHub release `v0.9.5`, published 2026-10-14)
into `C:\Herdr-dev\runtime\bin\download\` and extracted it to `C:\Herdr-dev\runtime\bin\herdr-0.9.5\`.
Expected digest from the GitHub release API: `sha256:d2c6c9c971c43a0bfdde8c692a9a1a7a45c3e4807cd01ae45662b4734fac1cbf`.
Production binary digest (read-only hash of `C:\herdr\.local\<private>`): `cd877c8744296f4a38a2703bf13cf11728973649ec54959959c4587ffe5368b2`.
Verification results are recorded in `C:\Herdr-dev\research\00-provenance.md` § "Binary verification" below once computed.
The production binary itself was **not** copied.

## Tooling on this executor (checked 2026-10-24)

| Tool | Status |
|---|---|
| cargo / rustc / rustup | not installed |
| just | not installed |
| zig | not installed (Herdr requires Zig 0.16.0 for vendored libghostty-vt) |
| MSVC `cl.exe` / Windows SDK | not found on PATH |
| python | 3.12.10 (`<USERPROFILE>\AppData\Local\Programs\Python\Python312\python.exe`) |
| node / npm | v24.19.0 / 11.17.0 |
| git | 2.55.0.windows.5 |
| gh | 2.102.0 |
| production `herdr` on PATH | `C:\herdr\.local\<private>` and a <private-pilot-path> pilot copy are on PATH — **never invoked by this project**; all research invocations use the absolute workspace path |

Consequence: a from-source Herdr build is blocked on this executor (no Rust toolchain, no Zig, no C/C++ toolchain or
Windows SDK). Installing them would require either elevation (VS Build Tools) or accepting Microsoft's SDK license via
`xwin`, which is not authorized by the research prompt. Prototypes are therefore implemented against Herdr's external
extension surfaces (plugin manifest, CLI/JSON API) and validated with Python/Node tests plus a disposable local Herdr
backend using the verified release binary.

## Binary verification (computed 2026-10-24)

| Artifact | SHA-256 | Result |
|---|---|---|
| `C:\Herdr-dev\runtime\bin\download\herdr-windows-x86_64.zip` | `d2c6c9c971c43a0bfdde8c692a9a1a7a45c3e4807cd01ae45662b4734fac1cbf` | matches GitHub release digest |
| `C:\Herdr-dev\runtime\bin\herdr-0.9.5\herdr.exe` (extracted) | `cd877c8744296f4a38a2703bf13cf11728973649ec54959959c4587ffe5368b2` | byte-identical to production `C:\herdr\.local\<private>` |

Zip contents: `herdr.exe`, `conpty/conpty.dll`, `conpty/herdr-conpty.json`, `conpty/x64/OpenConsole.exe`, `conpty/arm64/OpenConsole.exe`,
`THIRD-PARTY-NOTICES/*`. Extraction was performed with `python -I` + `zipfile` from `C:\Herdr-dev\runtime` (not from inside the download directory).
This binary is only ever invoked by absolute path with a scrubbed environment (see the isolation harness under `C:\Herdr-dev\prototypes`).
