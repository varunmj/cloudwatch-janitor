"""Flag log groups that store data but have received no events recently.

These usually belong to deleted Lambdas/services and can often be deleted outright.
Uses the AWS/Logs IncomingBytes metric over a lookback window, batched through
get_metric_data (up to 500 series per call).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cw_janitor.report import Finding

STORAGE_PRICE_PER_GB_MONTH = 0.03
LOOKBACK_DAYS = 90
BATCH_SIZE = 500

CHECK_ID = "idle-log-groups"
TITLE = f"Log groups with no incoming events in {LOOKBACK_DAYS} days"


def run(session, region: str) -> list[Finding]:
    logs = session.client("logs", region_name=region)
    cw = session.client("cloudwatch", region_name=region)

    groups = []
    for page in logs.get_paginator("describe_log_groups").paginate():
        for g in page["logGroups"]:
            if g.get("storedBytes", 0) > 0:
                groups.append(g)

    idle_names = set()
    for batch_start in range(0, len(groups), BATCH_SIZE):
        batch = groups[batch_start : batch_start + BATCH_SIZE]
        idle_names.update(_idle_in_batch(cw, batch))

    findings = []
    for g in groups:
        if g["logGroupName"] not in idle_names:
            continue
        stored_gb = g.get("storedBytes", 0) / 1024**3
        findings.append(
            Finding(
                check=CHECK_ID,
                resource=g["logGroupName"],
                issue=f"No incoming events in {LOOKBACK_DAYS} days ({stored_gb:.2f} GB still stored)",
                est_monthly_cost=round(stored_gb * STORAGE_PRICE_PER_GB_MONTH, 2),
                recommendation=(
                    "Confirm the producing service is gone, then delete: "
                    f"aws logs delete-log-group --log-group-name '{g['logGroupName']}'"
                ),
                details={"stored_bytes": g.get("storedBytes", 0)},
            )
        )
    return findings


def _idle_in_batch(cw, batch: list[dict]) -> set[str]:
    """Return names of log groups in this batch with zero IncomingBytes in the window."""
    now = datetime.now(timezone.utc)
    queries = []
    id_to_name = {}
    for i, g in enumerate(batch):
        qid = f"q{i}"
        id_to_name[qid] = g["logGroupName"]
        queries.append(
            {
                "Id": qid,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Logs",
                        "MetricName": "IncomingBytes",
                        "Dimensions": [
                            {"Name": "LogGroupName", "Value": g["logGroupName"]}
                        ],
                    },
                    "Period": LOOKBACK_DAYS * 24 * 3600,
                    "Stat": "Sum",
                },
                "ReturnData": True,
            }
        )

    idle = set()
    paginator = cw.get_paginator("get_metric_data")
    for page in paginator.paginate(
        MetricDataQueries=queries,
        StartTime=now - timedelta(days=LOOKBACK_DAYS),
        EndTime=now,
    ):
        for result in page["MetricDataResults"]:
            total = sum(result.get("Values", []))
            if total == 0:
                idle.add(id_to_name[result["Id"]])
    return idle
