# Gege CMs Revived

**Gege CMs Ulaanbaatar Revived**, **Gege CMs Urga Revived** and **Gege CMs Huree Revived**.
Latest: [Alpha 5](https://github.com/gege-mn/cms-revived/releases/tag/alpha-5). Where it
stands: [docs/state.md](docs/state.md).

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

The fonts are Unicode only: the 1998 keys are not encoded at their ASCII
positions, so documents typed the old way still need dEgi's originals.
Where the Unicode part needs something no 1998 key draws, it is drawn by hand in
`drawings/<cut>.ufo` (any UFO editor; the team uses Fontra).

## Setting up

Needs [uv](https://docs.astral.sh/uv/) and git. uv fetches a suitable Python (3.12 or
later) and the pinned dependencies from `uv.lock`, mongfontbuilder 0.15.3 among them.

```sh
git clone git@github.com:gege-mn/cms-revived.git && cd cms-revived
uv sync
uv run cmsr check --cut all   # should end with "editor data: ok"
```

Optional: [Fontra Pak](https://fontra.xyz) to edit `drawings/<CUT>.ufo`, the GitHub CLI
`gh` to publish releases, and the corpora (below) for the goldens tools.

### Corpora

`cmsr goldens` (coverage and `--add`) reads real text from `reference/corpora/*.md`, which
is not in git. Building and checking don't need it. The two files used so far are scrapes of
500 articles each, with no Private Use Area characters:

- `nmg-2026-10.md`: the Mongolian portal of the Inner Mongolia government,
  https://mgl.nmg.gov.cn, and its sub-sites
- `mgyxw-2026-10.md`: China Mongolian News Network, https://www.mgyxw.cn/

Any Markdown files of Unicode Mongolian text will do: words are counted from every `*.md`
in that folder.

## Commands

```sh
uv run cmsr editor --open   # map and review pieces, see real shaping live
                            # /specimen: all cuts setting real text
                            # /goldens: words checked against how CMs typed them
uv run cmsr build           # build all three cuts into dist/
uv run cmsr check           # build, then run the 3,689 shaping cases
uv run cmsr status          # progress, conflicts, problems
uv run cmsr goldens --add 10  # next goldens: common words with joins no golden checks yet
uv run cmsr release "Alpha 6" --final-name  # snapshot into releases/ (docs/workflow.md)
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
| `reference/corpora/` | news text for the goldens tools, not in git (see Corpora) |
| `releases/` | labelled snapshots, one folder each, with NOTES.md |
| `docs/` | [state](docs/state.md), [decisions](docs/decisions.md), [workflow](docs/workflow.md), [feedback](docs/feedback.md) |

## What counts as done

- every piece is `ok` (or `new` and drawn), so `cmsr build --strict` passes;
- `cmsr check` passes for all cuts (it checks the shaping, skipping letters
  the build leaves out because nothing draws them yet: the drawings are
  checked by eye in the editor);
- required ligatures are reviewed: `auto` joins the pieces as they are, which
  is right only where the CMs pieces already join that way.
