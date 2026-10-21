# CMs Revived

dEgi's 1998 CMs fonts (Urga, Ulaanbaatar, Huree) rebuilt as Unicode Mongolian
fonts, from his own outlines. See [NOTICE.md](NOTICE.md) for authorship and the
state of permission.

## How it works

The 1998 fonts are piece fonts: each ASCII key draws one stroke piece, and
words are typed piece by piece. Unicode Hudum shaping (mongfontbuilder,
following UTN #57 and Unicode 16) is built from the same idea: every letter
form is a sequence of *written units* in a joining position. So the rework is a
mapping:

```
mapping/pieces.toml     written unit (A.init, M.fina, BA.init…) → CMs keys
        +  cms/*.TTF    the 1998 outlines, used as they are
        →  dist/*.ttf   Unicode fonts: cmap, shaping and every variant, generated
```

The mapping is the only hand-made part. Everything else is derived, so a
change there reaches all three cuts and all 216 letter forms.

## Commands

```sh
uv run cmsr editor --open   # map and review pieces, see real shaping live
                            # /specimen: all cuts setting real text
                            # /goldens: words checked against how CMs typed them
uv run cmsr build           # build all three cuts into dist/
uv run cmsr check           # build, then run the 3,689 shaping cases
uv run cmsr status          # progress, conflicts, problems
```

## Layout

| Path | What |
|---|---|
| `cms/` | the 1998 fonts, read-only |
| `mapping/pieces.toml` | the mapping, written by the editor and by hand |
| `mapping/goldens.toml` | words and the CMs keys that type them; `cmsr check` holds the build to them |
| `drawings/<CUT>.ufo` | glyphs drawn new (status `new`): missing from CMs, or fixed; optional |
| `cmsr/` | targets, build, shaping check, editor server |
| `editor/` | the editor page |
| `reference/` | Noto Sans Mongolian, for comparison only |
| `reference/corpora/` | mongfontbuilder's news corpora, fetched on demand, not in git |

## What counts as done

- every piece is `ok` (or `new` and drawn), so `cmsr build --strict` passes;
- `cmsr check` passes for all cuts (it checks the shaping, which works even
  with placeholders: the drawings are checked by eye in the editor);
- required ligatures are reviewed: `auto` joins the pieces as they are, which
  is right only where the CMs pieces already join that way.
