from __future__ import annotations

import argparse
from collections import Counter

from . import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="cmsr", description="Gege CMs Revived font tooling.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build fonts into dist/")
    build.add_argument("--cut", choices=[*config.CUTS, "all"], default="all")
    build.add_argument("--strict", action="store_true", help="fail while any target is unmapped")

    check = commands.add_parser("check", help="build, then run the shaping suites")
    check.add_argument("--cut", choices=[*config.CUTS, "all"], default=config.DEFAULT_CUT)

    commands.add_parser("status", help="mapping progress and problems")

    golden = commands.add_parser("goldens", help="golden coverage of real text; --add picks the next batch")
    golden.add_argument("--add", type=int, metavar="N", help="add N pending goldens that cover new joins")
    golden.add_argument("--min-frequency", type=int, default=20, help="only words seen this often in the corpora")

    release = commands.add_parser("release", help="build a labelled snapshot into releases/, e.g. \"Alpha 1\"")
    release.add_argument("label", help="added to the family name, so a snapshot installs beside later builds")
    release.add_argument("--final-name", action="store_true", help="keep the family name; the label goes in the version string")

    editor = commands.add_parser("editor", help="run the mapping editor")
    editor.add_argument("--port", type=int, default=8787)
    editor.add_argument("--open", action="store_true", help="open it in the browser")

    args = parser.parse_args()
    commands_ = {"build": _build, "check": _check, "status": _status, "goldens": _goldens, "release": _release, "editor": _editor}
    commands_[args.command](args)


def _cuts(choice: str) -> list[str]:
    return list(config.CUTS) if choice == "all" else [choice]


def _build(args: argparse.Namespace) -> None:
    from .build import build

    for cut_id in _cuts(args.cut):
        result = build(cut_id, strict=args.strict)
        print(
            f"{result.path.relative_to(config.ROOT)}  keyed {len(result.keyed)}, "
            f"drawn {len(result.drawn)}, left out {len(result.left_out)}"
        )


def _check(args: argparse.Namespace) -> None:
    from . import goldens
    from .build import build
    from .check import run
    from .legacy import LegacyFont

    failed = False
    all_goldens = goldens.load()
    for cut_id in _cuts(args.cut):
        built = build(cut_id)
        path = built.path
        total, failures, skipped = run(path, built.left_out)
        unexpected = [failure for failure in failures if not failure.expected]
        print(
            f"{cut_id}: {total - len(failures)}/{total} pass, {len(failures) - len(unexpected)} expected failures, "
            f"{skipped} skipped (letters left out)"
        )
        for failure in unexpected:
            failed = True
            print(f"  {failure.case.index}  {failure.case.letters}")
            print(f"    got  {failure.result}\n    want {failure.case.goal}")
        confirmed = [golden for golden in all_goldens if golden.status in ("ok", "fixed")]
        broken = [
            (golden, result)
            for golden in confirmed
            if not (result := goldens.check(golden, path, LegacyFont.open(cut_id))).passed
        ]
        pending = len(all_goldens) - len(confirmed)
        print(f"  goldens: {len(confirmed) - len(broken)}/{len(confirmed)} confirmed pass, {pending} pending")
        for golden, result in broken:
            failed = True
            if golden.status == "fixed":
                print(f"    {golden.latin}: no longer draws the snapshot accepted as a fix (now {result.produced!r})")
            else:
                print(f"    {golden.latin}: typed {golden.keys!r}, the font draws {result.produced!r}")
    try:
        from .editor import _goldens, _mapping_state, _static_data
        from .mapping import Mapping

        _static_data(), _mapping_state(Mapping.load()), _goldens()
        print("editor data: ok")
    except Exception as error:  # the editor would fail to load: say so here, not in the browser
        failed = True
        print(f"editor data: {type(error).__name__}: {error}")
    raise SystemExit(1 if failed else 0)


def _release(args: argparse.Namespace) -> None:
    import datetime
    import subprocess

    from . import goldens
    from .build import build
    from .check import run
    from .legacy import LegacyFont
    from .mapping import Mapping

    slug = args.label.lower().replace(" ", "-")
    # Names and paths are read from config when each cut builds, so the label reaches every name table.
    if args.final_name:
        config.VERSION_LABEL = args.label
    else:
        config.FAMILY_SUFFIX = f"{config.FAMILY_SUFFIX} {args.label}"
    config.DIST_DIR = config.ROOT / "releases" / slug
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=config.ROOT).stdout.strip()
    mapping = Mapping.load()
    counts = Counter(entry.status for entry in mapping.all() if entry.kind in ("piece", "char"))
    all_goldens = goldens.load()
    lines = [
        f"# {config.FAMILY_PREFIX} CMs Revived {args.label}",
        "",
        f"Built {datetime.date.today().isoformat()} from commit {commit}. A snapshot of the work, not a release.",
        "",
        f"Pieces and punctuation: {', '.join(f'{status} {count}' for status, count in sorted(counts.items()))}.",
        "",
    ]
    for cut_id, cut in config.CUTS.items():
        result = build(cut_id, mapping)
        total, failures, _ = run(result.path, result.left_out)
        legacy = LegacyFont.open(cut_id)
        confirmed = [golden for golden in all_goldens if golden.status != "pending"]
        broken = [golden.latin for golden in confirmed if not goldens.check(golden, result.path, legacy).passed]
        lines += [
            f"## {cut.family}",
            "",
            f"- `{result.path.name}`",
            f"- shaping: {total - len(failures)}/{total} cases pass",
            f"- goldens: {len(confirmed) - len(broken)}/{len(confirmed)} confirmed match" + (f" (not: {', '.join(broken)})" if broken else ""),
            f"- left out (not drawn yet): {len(result.left_out)}" + (f" ({', '.join(result.left_out)})" if result.left_out else ""),
            "",
        ]
        print(f"{result.path.relative_to(config.ROOT)}  shaping {total - len(failures)}/{total}, left out {len(result.left_out)}")
    (config.DIST_DIR / "NOTES.md").write_text("\n".join(lines), encoding="utf-8")


def _status(args: argparse.Namespace) -> None:
    from .mapping import Mapping

    mapping = Mapping.load()
    by_kind: dict[str, Counter] = {}
    for entry in mapping.all():
        by_kind.setdefault(entry.kind, Counter())[entry.status] += 1
    for kind, counts in by_kind.items():
        summary = ", ".join(f"{status} {count}" for status, count in sorted(counts.items()))
        print(f"{kind:<9} {sum(counts.values()):>4}  {summary}")
    conflicts = [entry.name for entry in mapping.all() if "CONFLICT" in entry.note and entry.status != "ok"]
    if conflicts:
        print(f"\nconflicts to settle: {' '.join(conflicts)}")
    problems = mapping.problems()
    if problems:
        print("\nproblems:")
        for problem in problems:
            print(f"  {problem}")


def _goldens(args: argparse.Namespace) -> None:
    from . import coverage, goldens
    from .build import build
    from .legacy import LegacyFont

    cut = config.CUTS[config.DEFAULT_CUT]
    if not cut.output_path.exists():
        build(cut.id)
    if not coverage.corpus_words():
        raise SystemExit("no corpora in reference/corpora/: see README for how to fetch them")
    if args.add:
        items = goldens.load()
        added = 0
        # Ask for spares: a word the font still draws with a placeholder can't be typed in CMs.
        for word, roman, new, frequency in coverage.suggest(cut.output_path, args.add * 2, min_frequency=args.min_frequency):
            golden = goldens.Golden(word, roman)
            golden.keys = goldens.check(golden, cut.output_path, LegacyFont.open(cut.id)).produced
            if goldens.PLACEHOLDER in golden.keys:
                continue
            items.append(golden)
            print(f"added {roman:12} +{new} new joins, {frequency}x in the corpora")
            added += 1
            if added == args.add:
                break
        goldens.save(items)
    glyphs, joins = coverage.report(cut.output_path)
    pending = sum(golden.status == "pending" for golden in goldens.load())
    print(f"confirmed goldens check {glyphs:.0%} of real-text glyphs and {joins:.0%} of joins; {pending} pending")


def _editor(args: argparse.Namespace) -> None:
    from .editor import serve

    serve(port=args.port, open_browser=args.open)
