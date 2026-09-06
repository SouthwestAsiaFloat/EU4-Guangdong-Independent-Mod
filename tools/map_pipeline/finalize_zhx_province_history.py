#!/usr/bin/env python3
"""Run the terminal province-history projections after all map replay writers.

This is the formal final step for a replay which can recreate province history.
It restores the frozen B79 map transaction when present, then reviewed 1444
religion geography and named academies, and
immediately runs both non-mutating checks.  Earlier geometry, polity, culture,
development and toponym writers must have finished before this entry point.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELIGIOUS_GEOGRAPHY = ROOT / "tools/apply_zhx_religious_geography.py"
ACADEMIES = ROOT / "tools/apply_zhx_academies.py"
B79 = ROOT / "tools/map_pipeline/apply_b79_suizhu_xianhuang.py"
B80 = ROOT / "tools/map_pipeline/apply_b80_yiling_hanshang_merge.py"
B81 = ROOT / "tools/map_pipeline/apply_b81_yangtze_four_crossings.py"
B82 = ROOT / "tools/map_pipeline/apply_b82_regions_mountain_discovery.py"


def call(script: Path, check: bool) -> None:
    command = [sys.executable, str(script)]
    if check:
        command.append("--check")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="check both terminal projections without rewriting province history",
    )
    args = parser.parse_args()

    if (ROOT / "planning/suizhu_xianhuang_b79/batch_manifest.json").exists():
        subprocess.run(
            [sys.executable, str(B79), "--check" if args.check else "--apply"],
            cwd=ROOT, check=True,
        )

    call(B80, check=args.check)
    call(B81, check=args.check)
    call(B82, check=args.check)

    if args.check:
        call(RELIGIOUS_GEOGRAPHY, check=True)
        call(ACADEMIES, check=True)
    else:
        call(RELIGIOUS_GEOGRAPHY, check=False)
        call(RELIGIOUS_GEOGRAPHY, check=True)
        call(ACADEMIES, check=False)
        call(ACADEMIES, check=True)

    print("ZHX terminal province-history projections: PASS")


if __name__ == "__main__":
    main()
