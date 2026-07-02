"""Enforce prose hygiene (no dashes, decorative emoji, AI-speak, or narration).

VENDORED FILE: do not edit by hand; regenerate from the upstream generator.
Fails if any tracked text file carries the AI-generated-prose tells this project
bans, so CI / pre-push blocks a regression. See tools/check_prose_hygiene.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    res = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(res.stdout.strip())


def test_no_dashes_emoji_or_ai_speak() -> None:
    root = _repo_root()
    checker = root / "tools" / "check_prose_hygiene.py"
    assert checker.exists(), f"vendored prose-hygiene checker missing: {checker}"
    proc = subprocess.run(
        [sys.executable, str(checker), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_narration_pattern_precision() -> None:
    import importlib.util

    root = _repo_root()
    spec = importlib.util.spec_from_file_location(
        "prose_gate", root / "tools" / "check_prose_hygiene.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def fire(rel, text):
        lines = text.splitlines()
        return any(mod._narration_hits(rel, lines, i) for i in range(len(lines)))

    assert fire("a.py", "    # Build the request body")
    assert fire("a.sh", "# Check for stale locks")
    assert fire("a.ts", "// Fetch the remote manifest")
    assert not fire("a.md", "# Install dependencies")
    assert not fire("a.md", "    # Build the request body")
    assert not fire("a.py", "    # Build lazily because the import costs 2s")
    assert not fire("a.py", "x = 1  # Build the cache key")
    # wrapped comment blocks are explanations, not narration
    assert not fire(
        "a.py",
        "    # Copy talosconfig and inject endpoints, then\n    # rewrite the node list",
    )
