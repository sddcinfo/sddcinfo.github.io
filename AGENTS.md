# sddcinfo.github.io

The sddc.info landing page: an index of the public project wikis, served as
GitHub Pages.

## Writing conventions (enforced on every push)

Everything committed must read as human-written, in comments and docstrings as
much as in user-facing strings:

- No em-dashes or en-dashes. Use a comma, a colon, or parentheses.
- No AI-speak: skip stock hype words and filler openers; write plainly.
- No decorative emoji (functional UI glyphs are fine).
- No hand-authored code file over 1000 lines. Split into modules.
- No noise comments: never narrate the next line ("// Build the payload") and
  never commit commented-out code. Comments say why, not what.

Auto-fix dashes and emoji with `python tools/check_prose_hygiene.py --fix`;
reword AI-speak and delete narration by hand. A file that legitimately carries
the banned patterns opts out with the `prose-hygiene: allow` marker.
