"""Flag alarms stuck in INSUFFICIENT_DATA for a long time.

An alarm that has had no data for 30+ days is usually watching a resource that
no longer exists. It costs money and, worse, gives false confidence that
something is being monitored.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cw_janitor.report import Finding

ALARM_PRICE_PER_MONTH = 0.10  # standard-resolution metric alarm
STALE_AFTER_DAYS = 30

CHECK_ID = "stale-alarms"
TITLE = f"Alarms in INSUFFICIENT_DATA for {STALE_AFTER_DAYS}+ days"


def run(session, region: str) -> list[Finding]:
    cw = session.client("cloudwatch", region_name=region)
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_AFTER_DAYS)
    findings: list[Finding] = []

    paginator = cw.get_paginator("describe_alarms")
    for page in paginator.paginate(StateValue="INSUFFICIENT_DATA"):
        for alarm in page["MetricAlarms"]:
            since = alarm["StateUpdatedTimestamp"]
            if since > cutoff:
                continue
            days = (datetime.now(timezone.utc) - since).days
            findings.append(
                Finding(
                    check=CHECK_ID,
                    resource=alarm["AlarmName"],
                    issue=f"INSUFFICIENT_DATA for {days} days (metric likely gone)",
                    est_monthly_cost=ALARM_PRICE_PER_MONTH,
                    recommendation=(
                        "Verify the monitored resource still exists; if not, delete: "
                        f"aws cloudwatch delete-alarms --alarm-names '{alarm['AlarmName']}'"
                    ),
                    details={
                        "state_updated": since.isoformat(),
                        "metric": alarm.get("MetricName"),
                        "namespace": alarm.get("Namespace"),
                    },
                )
            )
    return findings
