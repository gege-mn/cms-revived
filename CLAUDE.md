# Gege CMs Revived

Unicode rework of dEgi's 1998 CMs Mongolian piece fonts. Read README.md and NOTICE.md first.

- `mapping/pieces.toml` is the source of truth. Change the mapping, never the build output; `dist/` is disposable.
- `cms/*.TTF` are dEgi's originals: never modify them. The `*DP.TTF` cuts are out of scope.
- Targets come from the pinned mongfontbuilder (`cmsr/targets.py`); don't hand-maintain lists of forms or ligatures.
- Credits: dEgi first in every field; the rework (Batmend Ganbaatar, L'Atelier Gege LLC) second. Names and metadata live only in `cmsr/config.py`.
- Scope is Hudum (locale MNG) only.
- After any change to the build or mapping: `uv run cmsr check --cut all`.
- The user decides glyph shapes, mapping calls and naming; when a mapping is ambiguous, ask rather than guess.
