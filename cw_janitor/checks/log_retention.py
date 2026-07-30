"""Flag log groups with no retention policy (logs are kept forever = silent cost)."""

from __future__ import annotations

from cw_janitor.report import Finding

# CloudWatch Logs standard storage price (us-east-1). Rough on purpose.
STORAGE_PRICE_PER_GB_MONTH = 0.03

CHECK_ID = "log-retention"
TITLE = "Log groups without a retention policy"


def run(session, region: str) -> list[Finding]:
    logs = session.client("logs", region_name=region)
    findings: list[Finding] = []

    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate():
        for group in page["logGroups"]:
            if group.get("retentionInDays") is not None:
                continue
            stored_gb = group.get("storedBytes", 0) / 1024**3
            findings.append(
                Finding(
                    check=CHECK_ID,
                    resource=group["logGroupName"],
                    issue=f"No retention policy ({stored_gb:.2f} GB stored, growing forever)",
                    est_monthly_cost=round(stored_gb * STORAGE_PRICE_PER_GB_MONTH, 2),
                    recommendation=(
                        "Set a retention policy, e.g.: aws logs put-retention-policy "
                        f"--log-group-name '{group['logGroupName']}' --retention-in-days 30"
                    ),
                    details={"stored_bytes": group.get("storedBytes", 0)},
                )
            )
    return findings
