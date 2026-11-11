# Gege CMs Revived

Unicode rework of dEgi's 1998 CMs Mongolian piece fonts. Read README.md and NOTICE.md first,
then docs/state.md (where it stands), docs/decisions.md (settled calls) and RELEASE.md (to-dos).

- `mapping/pieces.toml` is the source of truth. Change the mapping, never the build output; `dist/` is disposable.
- `cms/*.TTF` are dEgi's originals: never modify them. The `*DP.TTF` cuts are out of scope for the Gege (Unicode) fonts; only the legacy-keyed companion has dp cuts, flipped from the regular companion (docs/decisions.md).
- Targets come from the pinned mongfontbuilder (`cmsr/targets.py`); don't hand-maintain lists of forms or ligatures.
- Credits: dEgi first in every field; the rework (Batmend Ganbaatar, L'Atelier Gege LLC) second. Names and metadata live only in `cmsr/config.py`.
- Scope is Hudum (locale MNG) only. The Gege fonts are Unicode only: no legacy ASCII keys in their cmap. Old documents are served by the legacy-keyed companion (`cmsr/companion.py`), whose features-off check must keep passing.
- After any change to the build or mapping: `uv run cmsr check --cut all`.
- The user decides glyph shapes, mapping calls and naming; when a mapping is ambiguous, ask rather than guess.
- Never set `ok`/`fixed` in goldens.toml or `ok` in pieces.toml: fill keys, leave `pending`/`draft`; the user confirms in the editor. A status that changes while you work was the user: keep it.
- Don't draw or "derive" new letter shapes; compose only from dEgi's keys and contours. Join spacing is measured from his teeth per cut, never eyeballed; keep rules narrow (docs/decisions.md).
- Before regenerating anything the user edited by hand in `drawings/`, back it up and say which edits would go.
- dEgi's permission is not a release gate; NOTICE.md's good-faith terms cover releases.

## Working with the user

- One item at a time: open the editor on the entry (or a small HTML page for special cases), say in a line or two what to look at, and wait. No walls of info, no batched questions.
- They want to be involved in the essentials (shapes, scope, naming, licensing), not routine details: decide those and say what you chose.
- Show glyph work as real words set vertically, cuts side by side.
- Problems seen in production go in docs/feedback.md.
