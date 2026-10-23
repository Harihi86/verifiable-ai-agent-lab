"""Small interfaces for submitted implementations and source-based reviews."""

import ast
import hashlib
from pathlib import Path, PurePosixPath
from typing import Protocol


class DevelopmentAdapter(Protocol):
    identity: str

    def files(self) -> dict[str, str]: ...


class DirectoryAdapter:
    identity = "local-directory-submission"

    def __init__(self, directory: Path):
        self.directory = directory.resolve()

    def files(self):
        if not self.directory.is_dir():
            raise ValueError("Submission directory does not exist")
        files = {}
        for path in sorted(self.directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("Symlinks are not accepted")
            if path.is_file():
                if path.suffix not in {".py", ".json", ".toml", ".md", ".txt"}:
                    raise ValueError(f"Unsupported submitted file: {path.name}")
                files[path.relative_to(self.directory).as_posix()] = path.read_text(
                    encoding="utf-8"
                )
        return files


class FixtureAdapter:
    identity = "deterministic-fixture; not a live AI agent"

    def __init__(self, files):
        self.submission = files

    def files(self):
        return dict(self.submission)


def stage(adapter: DevelopmentAdapter, workspace: Path):
    files = adapter.files()
    if not files or len(files) > 200:
        raise ValueError("A submission must contain 1..200 text files")
    if sum(len(text.encode()) for text in files.values()) > 2_000_000:
        raise ValueError("Submission exceeds the 2 MB limit")
    for name, content in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("Submission paths must stay within the workspace")
        if any(part.startswith(".") for part in path.parts) or not path.name:
            raise ValueError("Hidden paths are not accepted")
        target = workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def tree_digest(directory: Path):
    digest = hashlib.sha256()
    for file in sorted(directory.rglob("*")):
        if "__pycache__" in file.parts:
            continue
        if file.is_symlink():
            raise ValueError("Source tree contains a symlink")
        if file.is_file():
            digest.update(file.relative_to(directory).as_posix().encode() + b"\0")
            digest.update(file.read_bytes() + b"\0")
    return digest.hexdigest()


class StaticReviewer:
    """Inspect actual Python source; deliberately narrow and never called an AI review."""

    def review(self, workspace: Path):
        findings = []
        paths = sorted(workspace.rglob("*.py"))
        for path in paths:
            relative = path.relative_to(workspace).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                findings.append(
                    {
                        "file": relative,
                        "line": exc.lineno,
                        "disposition": "confirmed",
                        "message": "Python source cannot be parsed",
                    }
                )
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    findings.append(
                        {
                            "file": relative,
                            "line": node.lineno,
                            "disposition": "potential",
                            "message": "Bare except may conceal execution failures",
                        }
                    )
                if isinstance(node, ast.Call) and any(
                    k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                    for k in node.keywords
                ):
                    findings.append(
                        {
                            "file": relative,
                            "line": node.lineno,
                            "disposition": "potential",
                            "message": "shell=True requires owner review",
                        }
                    )
        return {
            "kind": "static-source-review; not AI or human review",
            "source_sha256": tree_digest(workspace),
            "files_inspected": len(paths),
            "outcome": "PASS" if paths and not findings else "INCONCLUSIVE",
            "findings": findings,
            "scope": "syntax, bare except, literal shell=True; does not establish semantic correctness",
        }
