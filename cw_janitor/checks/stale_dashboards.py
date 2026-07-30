"""Flag dashboards that haven't been modified in a long time.

Dashboards beyond the first 3 cost $3/month each. A dashboard untouched for
6+ months is a candidate for review. (Detecting dashboards whose widgets
reference metrics that no longer exist is a planned improvement — see issues.)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cw_janitor.report import Finding

DASHBOARD_PRICE_PER_MONTH = 3.00
FREE_DASHBOARDS = 3
STALE_AFTER_DAYS = 180

CHECK_ID = "stale-dashboards"
TITLE = f"Dashboards not modified in {STALE_AFTER_DAYS}+ days"


def run(session, region: str) -> list[Finding]:
    cw = session.client("cloudwatch", region_name=region)
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_AFTER_DAYS)

    dashboards = []
    for page in cw.get_paginator("list_dashboards").paginate():
        dashboards.extend(page["DashboardEntries"])

    # Only dashboards beyond the free tier actually cost money, but stale ones
    # are worth reviewing regardless. We attribute cost only past the free tier.
    billable_count = max(0, len(dashboards) - FREE_DASHBOARDS)
    findings: list[Finding] = []

    stale = [d for d in dashboards if d.get("LastModified") and d["LastModified"] < cutoff]
    for i, dash in enumerate(sorted(stale, key=lambda d: d["LastModified"])):
        days = (datetime.now(timezone.utc) - dash["LastModified"]).days
        # Attribute $3/mo to as many stale dashboards as there are billable ones.
        cost = DASHBOARD_PRICE_PER_MONTH if i < billable_count else 0.0
        findings.append(
            Finding(
                check=CHECK_ID,
                resource=dash["DashboardName"],
                issue=f"Not modified in {days} days",
                est_monthly_cost=cost,
                recommendation=(
                    "Review whether this dashboard is still used; if not, delete: "
                    f"aws cloudwatch delete-dashboards --dashboard-names '{dash['DashboardName']}'"
                ),
                details={"last_modified": dash["LastModified"].isoformat()},
            )
        )
    return findings
