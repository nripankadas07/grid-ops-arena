"""Command-line interface for Grid Ops Arena."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .model import Scenario
from .policies import POLICIES, get_policy
from .reporting import write_reports
from .simulator import build_demo_scenario, simulate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grid-ops-arena", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run the deterministic synthetic demo")
    demo.add_argument("--seed", type=int, default=17)
    demo.add_argument("--hours", type=int, default=48)
    demo.add_argument("--policy", choices=sorted(POLICIES), default="balanced")
    demo.add_argument("--output-dir", type=Path, default=Path("reports"))
    run = sub.add_parser("run", help="evaluate a versioned scenario JSON file")
    run.add_argument("--scenario", type=Path, required=True)
    run.add_argument("--policy", choices=sorted(POLICIES), default="balanced")
    run.add_argument("--output-dir", type=Path, default=Path("reports"))
    sub.add_parser("policies", help="list built-in policies")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "policies":
            print("\n".join(sorted(POLICIES)))
            return 0
        if args.command == "demo":
            scenario = build_demo_scenario(args.seed, args.hours)
        else:
            scenario = Scenario.from_artifact(json.loads(args.scenario.read_text(encoding="utf-8")))
        result = simulate(scenario, get_policy(args.policy))
        paths = write_reports(result, args.output_dir)
        print("Synthetic demo data only; not current grid facts.")
        print("Composite score: {0:.2f}".format(result["metrics"]["composite_score"]))
        for kind, path in paths.items():
            print("{0}: {1}".format(kind, path.resolve()))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("grid-ops-arena: error: {0}".format(exc), file=sys.stderr)
        return 2
