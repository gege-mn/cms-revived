from __future__ import annotations

import argparse
from collections import Counter

from . import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="cmsr", description="CMs Revived font tooling.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build fonts into dist/")
    build.add_argument("--cut", choices=[*config.CUTS, "all"], default="all")
    build.add_argument("--strict", action="store_true", help="fail while any target is unmapped")

    check = commands.add_parser("check", help="build, then run the shaping suites")
    check.add_argument("--cut", choices=[*config.CUTS, "all"], default=config.DEFAULT_CUT)

    commands.add_parser("status", help="mapping progress and problems")

    editor = commands.add_parser("editor", help="run the mapping editor")
    editor.add_argument("--port", type=int, default=8787)
    editor.add_argument("--open", action="store_true", help="open it in the browser")

    args = parser.parse_args()
    {"build": _build, "check": _check, "status": _status, "editor": _editor}[args.command](args)


def _cuts(choice: str) -> list[str]:
    return list(config.CUTS) if choice == "all" else [choice]


def _build(args: argparse.Namespace) -> None:
    from .build import build

    for cut_id in _cuts(args.cut):
        result = build(cut_id, strict=args.strict)
        print(
            f"{result.path.relative_to(config.ROOT)}  keyed {len(result.keyed)}, "
            f"drawn {len(result.drawn)}, placeholders {len(result.placeholders)}"
        )


def _check(args: argparse.Namespace) -> None:
    from . import goldens
    from .build import build
    from .check import run
    from .legacy import LegacyFont

    failed = False
    all_goldens = goldens.load()
    for cut_id in _cuts(args.cut):
        path = build(cut_id).path
        total, failures = run(path)
        unexpected = [failure for failure in failures if not failure.expected]
        print(f"{cut_id}: {total - len(failures)}/{total} pass, {len(failures) - len(unexpected)} expected failures")
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
    raise SystemExit(1 if failed else 0)


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


def _editor(args: argparse.Namespace) -> None:
    from .editor import serve

    serve(port=args.port, open_browser=args.open)
