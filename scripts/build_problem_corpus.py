#!/usr/bin/env python3
"""Materialize or verify deterministic problem-family bundles."""
import argparse
from pathlib import Path
import shutil
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from corpus_factory import build_corpus  # noqa: E402


def render(records: list[dict]) -> str:
    return yaml.safe_dump({"schema_version": 1, "problems": records}, allow_unicode=True,
                          sort_keys=False, width=1000)


def write_to(root: Path) -> None:
    for relative, records in build_corpus().items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render(records), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated_root = ROOT / "problems"
    expected = set(build_corpus())
    if args.write:
        for directory in generated_root.glob("*/generated"):
            shutil.rmtree(directory)
        write_to(generated_root)
        print(f"Materialized {sum(map(len, build_corpus().values()))} problems in {len(expected)} family bundles.")
        return 0
    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        write_to(scratch)
        actual = {str(path.relative_to(generated_root)) for path in generated_root.glob("*/generated/*.yaml")}
        if actual != expected:
            print(f"Generated bundle set differs (missing={sorted(expected-actual)}, stale={sorted(actual-expected)}).", file=sys.stderr)
            return 1
        drift = [relative for relative in sorted(expected)
                 if (generated_root / relative).read_bytes() != (scratch / relative).read_bytes()]
        if drift:
            print("Generated corpus drift: " + ", ".join(drift), file=sys.stderr)
            return 1
    print(f"Generated corpus is reproducible: {len(expected)} families, {sum(map(len, build_corpus().values()))} problems.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
