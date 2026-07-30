"""cloudwatch-janitor CLI — find CloudWatch waste, read-only, no infrastructure."""

from __future__ import annotations

import argparse
import sys

import boto3

from cw_janitor.checks import idle_log_groups, log_retention, stale_alarms, stale_dashboards
from cw_janitor.report import render_json, render_table

ALL_CHECKS = {
    log_retention.CHECK_ID: log_retention,
    idle_log_groups.CHECK_ID: idle_log_groups,
    stale_alarms.CHECK_ID: stale_alarms,
    stale_dashboards.CHECK_ID: stale_dashboards,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudwatch-janitor",
        description="Audit an AWS account for CloudWatch waste. 100% read-only.",
    )
    parser.add_argument("--profile", help="AWS profile to use (default: environment)")
    parser.add_argument("--region", help="AWS region (default: profile/environment region)")
    parser.add_argument(
        "--checks",
        help=f"Comma-separated checks to run (default: all). Available: {', '.join(ALL_CHECKS)}",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a table")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    session = boto3.Session(profile_name=args.profile)
    region = args.region or session.region_name
    if not region:
        print("No region configured. Pass --region or set AWS_DEFAULT_REGION.", file=sys.stderr)
        return 2

    if args.checks:
        requested = [c.strip() for c in args.checks.split(",")]
        unknown = [c for c in requested if c not in ALL_CHECKS]
        if unknown:
            print(f"Unknown check(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        checks = {name: ALL_CHECKS[name] for name in requested}
    else:
        checks = ALL_CHECKS

    findings = []
    for name, module in checks.items():
        if not args.json:
            print(f"Running {name}...", file=sys.stderr)
        try:
            findings.extend(module.run(session, region))
        except Exception as exc:  # noqa: BLE001 - keep going if one check fails (e.g. missing permission)
            print(f"  {name} failed: {exc}", file=sys.stderr)

    print(render_json(findings) if args.json else render_table(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
