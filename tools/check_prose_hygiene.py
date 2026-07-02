#!/usr/bin/env python3
"""Prose-hygiene gate (vendored, stdlib-only, no AI).

VENDORED FILE: do not edit by hand; regenerate from the upstream generator.
Self-contained: scans tracked text files for the AI-generated-prose tells this
project bans -- em/en-dashes, decorative emoji, stock AI-speak phrases, and
narration comments that restate the next statement -- and fails if any remain.
Run as a pre-commit / pre-push / CI gate so the cruft can never accrete again.

Two modes:
  (default)  report offenders and exit non-zero if any are found  (the GATE)
  --fix      deterministically repair the auto-fixable ones in place
             (dashes -> hyphen, decorative emoji removed); AI-speak phrases and
             narration comments are reported for manual fixing, never
             auto-rewritten (deleting a comment is a judgment call).

A file may opt out of fixing/checking with a line containing the marker
``prose-hygiene: allow`` (for the rare file that legitimately carries the
characters -- e.g. the detector that defines these very patterns).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_ALLOW_MARKER = "prose-hygiene: allow"

# Dash family that reads as AI-generated punctuation: em-dash, en-dash,
# horizontal bar, figure dash. All collapse to a plain hyphen. Built from
# codepoints, never literal glyphs, so a `--fix` pass over a repo carrying this
# vendored gate cannot rewrite the detector's own match characters into hyphens
# and silently disarm it (that corruption already bit the central rules once).
_DASHES = "".join(chr(c) for c in (0x2014, 0x2013, 0x2015, 0x2012))
_DASH_RE = re.compile(f"[{_DASHES}]")

# Decorative emoji ranges. Only flagged/stripped where DECORATIVE -- in a
# comment or a docs file -- never in UI markup (HTML/astro/jsx elements) or
# code strings, where emoji are functional (menu glyphs, status marks, icons)
# and removing them would break the product.
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f1e6-\U0001f1ff\U00002b00-\U00002bff]"
)
_COMMENT_PREFIXES = ("#", "//", "*", "<!--", "--", ";")
_DOCS_SUFFIXES = {".md", ".rst", ".txt"}


def _emoji_is_decorative(rel: str, line: str) -> bool:
    """Emoji counts as decorative AI-speak only in a docs file or a comment."""
    if Path(rel).suffix.lower() in _DOCS_SUFFIXES:
        return True
    return line.lstrip().startswith(_COMMENT_PREFIXES)


# Stock AI-speak phrases / hype / explanatory openers. Tuned to fire on the
# genuine tells, not ordinary technical prose. NOT auto-fixed (needs rewording).
_AISPEAK_RES = [
    re.compile(
        r"\b(delve|leverage|seamless(?:ly)?|cutting[- ]edge|state[- ]of[- ]the[- ]art|"
        r"game[- ]changer|best[- ]in[- ]class|world[- ]class|ever[- ]evolving|"
        r"it'?s worth noting|in conclusion|at the end of the day|when it comes to|"
        r"a testament to|plays? a (?:crucial|vital|key|pivotal) role|navigating the|"
        r"in today'?s|unlock(?:ing)? the|elevate your|harness(?:ing)? the power|"
        r"dive into|embark on|realm of|tapestry|treasure trove|boasts)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(blazing(?:ly)?[- ]fast|lightning[- ]fast|effortless(?:ly)?|simply put|"
        r"incredibl[ey]|amazing|awesome|magical|supercharge|next[- ]gen(?:eration)?|"
        r"revolutionary|seamlessly integrate)\b",
        re.IGNORECASE,
    ),
    re.compile(
        # contractions only ("Here's"/"Let's" the AI opener) -- the apostrophe is
        # mandatory so the ordinary verbs "lets"/"heres" never match.
        r"^\s*(?:#|//|\*|<!--)?\s*(here['’]s|let['’]s|now,? let['’]s|first,? we['’]ll|"
        r"in this (?:section|guide|tutorial|article))\b",
        re.IGNORECASE,
    ),
]

# Narration comments: a full-line comment that restates the next action
# ("# Build the payload") instead of saying why. Same shape as the central
# noise-comment.narration audit rule: Capitalized verb, lowercase object, no
# why-content (because / so that / a colon'd explanation / CAPS emphasis /
# negation / a second sentence), at most ~60 chars. The indented-'#' and '//'
# form applies to any non-docs file; the unindented-'#' form as well, since
# outside docs a column-0 '#' cannot be a Markdown heading. Docs files are
# fully exempt (headings and fenced code examples are illustrative).
_NARRATION_VERBS = (
    "Build|Check|Create|Get|Set|Setup|Load|Parse|Run|Start|Stop|Read|Write|Add|"
    "Extract|Send|Make|Fetch|Find|Update|Initiali[sz]e|Init|Compute|Convert|"
    "Generate|Prepare|Process|Validate|Verify|Remove|Delete|Save|Store|Print|Log|"
    "Wait|Loop|Iterate|Return|Call|Open|Close|Clean|Clear|Reset|Show|Display|"
    "Handle|Apply|Filter|Sort|Merge|Split|Copy|Move|Determine|Collect|Register|"
    "Install|Import|Define|Try|Attempt|Ensure|Combine|Join|Retrieve|Query|Launch|"
    "Spawn|Execute|Invoke|Emit|Schedule|Retry|Refresh|Reload|Restore|Map|Match|"
    "Compare|Select|Pick|Sleep|Pause|Resume|Kill|Terminate|Format|Render|Encode|"
    "Decode|Strip|Append|Insert|Search|Skip|Mark|Count|Fill|Populate|Assign|"
    "Attach|Bind|Connect|Enumerate|Scan|Walk|Grab|Pull|Push|Use"
)
_NARRATION_WHY = (
    r"\bbecause\b|\bso that\b|\bso the\b|\bso we\b|\bsince\b|\botherwise\b|"
    r"\bavoid|\bprevent|\bmust\b|\bnever\b|\bnot\b|\bdon'?t\b|\bonly\b|\beven\b|"
    r"\bcrucial|\bworkaround\b|\bgotcha\b|\bdeliberat|\bintentional|\binstead\b|"
    r"\brather than\b|"
    r"\b(?:NOT|NEVER|ONLY|MUST|ALWAYS|BEFORE|AFTER|WHY)\b|"
    r"[:;?]|\. "
)
_NARRATION_RE = re.compile(
    rf"^(?:\s+#|\s*//)\s+(?:{_NARRATION_VERBS}) "
    rf"(?!of\b)(?!.*(?:{_NARRATION_WHY}))[a-z].{{0,60}}$"
)
_NARRATION_TOPLEVEL_RE = re.compile(
    rf"^#\s+(?:{_NARRATION_VERBS}) "
    rf"(?!of\b)(?!.*(?:{_NARRATION_WHY}))[a-z].{{0,60}}$"
)
_COMMENT_BLOCK_RE = re.compile(r"^(\s*)(#|//)")


def _narration_hits(rel: str, lines: list[str], i: int) -> bool:
    """Standalone narration comments only, and never in docs files.

    Docs are exempt because '#' is a heading there and fenced examples are
    illustrative. A line inside a multi-line comment block (a neighbour shares
    its indent + marker) is an explanation, not narration - flagging just its
    first line would orphan the continuation when deleted."""
    if Path(rel).suffix.lower() in _DOCS_SUFFIXES:
        return False
    line = lines[i]
    if not (_NARRATION_RE.match(line) or _NARRATION_TOPLEVEL_RE.match(line)):
        return False
    m = _COMMENT_BLOCK_RE.match(line)
    prefix = m.group(1) + m.group(2)
    if i > 0 and lines[i - 1].startswith(prefix):
        return False
    return not (i + 1 < len(lines) and lines[i + 1].startswith(prefix))


# Binary / media / data / generated suffixes that never carry prose. Everything
# else (incl. extensionless scripts, dotfiles, .service/.tpl/.rules/.env.example)
# is scanned - a denylist, so no human-authored text type is silently missed; the
# UTF-8 decode in scan()/apply_fix() drops anything binary that slips through.
_SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".xz",
    ".zst",
    ".bz2",
    ".7z",
    ".wav",
    ".mp3",
    ".pcm",
    ".ogg",
    ".flac",
    ".m4a",
    ".mp4",
    ".mov",
    ".webm",
    ".pptx",
    ".docx",
    ".xlsx",
    ".odp",
    ".odt",
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".o",
    ".a",
    ".onnx",
    ".safetensors",
    ".bin",
    ".pt",
    ".pth",
    ".gguf",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".efi",
    ".wasm",
    ".node",
    ".lock",
}
_SKIP_NAMES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    "composer.lock",
    "go.sum",
    "uv.lock",
}
_SKIP_DIR_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "build",
    ".wrangler",
    ".repo-audit",
    "datasets",
    "wiki-site",
    "vendor",
}
# Generated LLM-wiki markdown (mirrors walk.py's skip): machine output, not
# hand-authored prose, and present in the publish clone the release gate scans.
_SKIP_PREFIXES = ("docs/wiki/",)


def _skip(rel: str) -> bool:
    p = Path(rel)
    if set(p.parts) & _SKIP_DIR_PARTS:
        return True
    if rel.startswith(_SKIP_PREFIXES):
        return True
    if p.name in _SKIP_NAMES:
        return True
    if p.suffix.lower() in _SKIP_SUFFIXES:
        return True
    return p.name.endswith((".min.js", ".min.css"))


def _tracked_files(root: Path) -> list[str]:
    res = subprocess.run(
        # -z: NUL-separated, unquoted output. Without it git C-style-quotes
        # paths with special chars (spaces, unicode), and a naive splitlines()
        # would yield the quoted form (which does not exist on disk) and the
        # file would be silently skipped.
        ["git", "ls-files", "-z"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        # Fail closed: a gate that cannot enumerate files must not pass.
        print(
            f"check_prose_hygiene: git ls-files failed in {root}: {res.stderr.strip()}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return [ln for ln in res.stdout.split("\0") if ln.strip()]


def _aispeak_hits(line: str) -> bool:
    return any(rx.search(line) for rx in _AISPEAK_RES)


def scan(root: Path) -> dict[str, list[tuple[int, str, str]]]:
    """Return ``{relpath: [(lineno, kind, snippet), ...]}`` for every offender."""
    out: dict[str, list[tuple[int, str, str]]] = {}
    for rel in sorted(f for f in _tracked_files(root) if not _skip(f)):
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _ALLOW_MARKER in text:
            continue
        hits: list[tuple[int, str, str]] = []
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if _DASH_RE.search(line):
                hits.append((i, "dash", line.strip()[:100]))
            if _EMOJI_RE.search(line) and _emoji_is_decorative(rel, line):
                hits.append((i, "emoji", line.strip()[:100]))
            if _aispeak_hits(line):
                hits.append((i, "ai-speak", line.strip()[:100]))
            if _narration_hits(rel, lines, i - 1):
                hits.append((i, "narration", line.strip()[:100]))
        if hits:
            out[rel] = hits
    return out


def fix_line(rel: str, line: str) -> str:
    """Deterministic per-line repair: dashes -> hyphen; decorative emoji removed."""
    line = _DASH_RE.sub("-", line)
    if _emoji_is_decorative(rel, line):
        before = line
        line = _EMOJI_RE.sub("", line)
        if line != before:
            # Collapse only the gap an emoji removal left behind; a line with
            # no emoji keeps its intentional spacing (markdown table padding).
            line = re.sub(r"(?<=\S)  +(?=\S)", " ", line)
    return line


def apply_fix(root: Path) -> tuple[list[str], dict[str, list[tuple[int, str, str]]]]:
    """Fix dashes + decorative emoji in place. Returns (changed, remaining_aispeak)."""
    changed: list[str] = []
    for rel in sorted(f for f in _tracked_files(root) if not _skip(f)):
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _ALLOW_MARKER in text:
            continue
        lines = text.splitlines(keepends=True)
        new_lines = []
        for ln in lines:
            body, sep = (ln[:-1], ln[-1]) if ln.endswith("\n") else (ln, "")
            new_lines.append(fix_line(rel, body) + sep)
        new = "".join(new_lines)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    # re-scan for what fix can't touch (ai-speak phrases, narration comments)
    remaining = {
        rel: [h for h in hits if h[1] in ("ai-speak", "narration")]
        for rel, hits in scan(root).items()
    }
    return changed, {rel: hs for rel, hs in remaining.items() if hs}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    do_fix = "--fix" in argv
    rest = [a for a in argv if a != "--fix"]
    root = Path(rest[0]).resolve() if rest else Path.cwd()

    if do_fix:
        changed, remaining = apply_fix(root)
        print(f"prose-hygiene --fix: repaired {len(changed)} file(s)")
        for rel in changed:
            print(f"  fixed {rel}")
        if remaining:
            n = sum(len(v) for v in remaining.values())
            print(
                f"prose-hygiene: {n} AI-speak / narration line(s) need MANUAL fixing:",
                file=sys.stderr,
            )
            for rel, hits in sorted(remaining.items()):
                for lineno, _kind, snip in hits:
                    print(f"  {rel}:{lineno}  {snip}", file=sys.stderr)
            return 1
        return 0

    offenders = scan(root)
    if not offenders:
        print("prose-hygiene: clean (no dashes / emoji / AI-speak / narration)")
        return 0
    total = sum(len(v) for v in offenders.values())
    print(
        f"prose-hygiene: {total} offender(s) across {len(offenders)} file(s):",
        file=sys.stderr,
    )
    for rel, hits in sorted(offenders.items()):
        for lineno, kind, snip in hits:
            print(f"  {rel}:{lineno}  [{kind}]  {snip}", file=sys.stderr)
    print(
        "run `python tools/check_prose_hygiene.py --fix` (dashes/emoji); "
        "reword AI-speak and delete narration comments by hand.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
