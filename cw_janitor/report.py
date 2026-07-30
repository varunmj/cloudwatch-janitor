"""Finding model and report rendering (terminal table + JSON)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass
class Finding:
    """A single piece of CloudWatch waste discovered by a check."""

    check: str                      # short check id, e.g. "log-retention"
    resource: str                   # ARN or name of the offending resource
    issue: str                      # one-line human description
    est_monthly_cost: float | None  # rough USD/month, None if unknown
    recommendation: str             # what to do about it
    details: dict = field(default_factory=dict)


def total_savings(findings: list[Finding]) -> float:
    return sum(f.est_monthly_cost or 0.0 for f in findings)


def render_json(findings: list[Finding]) -> str:
    payload = {
        "findings": [asdict(f) for f in findings],
        "total_findings": len(findings),
        "estimated_monthly_savings_usd": round(total_savings(findings), 2),
    }
    return json.dumps(payload, indent=2, default=str)


def render_table(findings: list[Finding]) -> str:
    """Render findings as a plain-text table. No dependencies, plays nice with pipes."""
    if not findings:
        return "\n  No waste found. Either your account is spotless or you should add more checks :)\n"

    headers = ["CHECK", "RESOURCE", "ISSUE", "EST. $/MO"]
    rows = []
    for f in sorted(findings, key=lambda f: -(f.est_monthly_cost or 0)):
        cost = f"{f.est_monthly_cost:.2f}" if f.est_monthly_cost is not None else "-"
        rows.append([f.check, _truncate(f.resource, 48), _truncate(f.issue, 60), cost])

    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    sep = "  "

    def fmt(row: list[str]) -> str:
        return sep.join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip()

    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    lines.extend(fmt(r) for r in rows)
    lines.append("")
    lines.append(
        f"{len(findings)} finding(s), estimated savings: "
        f"${total_savings(findings):.2f}/month (rough estimate, standard pricing)"
    )
    return "\n".join(lines)


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
