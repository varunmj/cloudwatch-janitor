# cloudwatch-janitor 🧹

**Find the CloudWatch waste hiding in your AWS bill — in one read-only command.**

CloudWatch costs creep up silently: log groups that keep data forever, alarms watching resources that were deleted months ago, dashboards nobody has opened since 2024. `cloudwatch-janitor` scans your account, lists every finding, and estimates what it's costing you per month.

It never modifies anything. Four read-only API calls, that's it.

```
CHECK             RESOURCE                        ISSUE                                              EST. $/MO
----------------  ------------------------------  -------------------------------------------------  ---------
log-retention     /aws/lambda/etl-processor       No retention policy (312.40 GB stored, growing…)   9.37
log-retention     /aws/eks/prod-cluster/apps      No retention policy (88.10 GB stored, growing…)    2.64
idle-log-groups   /aws/lambda/old-webhook-fn      No incoming events in 90 days (12.33 GB stored)    0.37
stale-alarms      db-conn-alarm-legacy            INSUFFICIENT_DATA for 214 days (metric likely…)    0.10
stale-dashboards  team-x-dashboard                Not modified in 431 days                           3.00

5 finding(s), estimated savings: $15.48/month (rough estimate, standard pricing)
```

## Install

```bash
pip install git+https://github.com/YOUR_USERNAME/cloudwatch-janitor.git
```

Or clone and run directly:

```bash
git clone https://github.com/YOUR_USERNAME/cloudwatch-janitor.git
cd cloudwatch-janitor && pip install -e .
```

## Usage

```bash
# Scan the default profile/region
cloudwatch-janitor

# Specific profile and region
cloudwatch-janitor --profile prod --region us-west-2

# Only some checks
cloudwatch-janitor --checks log-retention,stale-alarms

# JSON output (pipe it, save it, alert on it)
cloudwatch-janitor --json > findings.json
```

## What it checks

| Check | What it finds | Why it matters |
|---|---|---|
| `log-retention` | Log groups with **no retention policy** | Logs are stored forever at ~$0.03/GB-month, growing every day |
| `idle-log-groups` | Log groups with **zero incoming events in 90 days** but data still stored | Usually left behind by deleted Lambdas/services — safe to remove |
| `stale-alarms` | Alarms in `INSUFFICIENT_DATA` for **30+ days** | The metric is probably gone; you're paying for monitoring that monitors nothing |
| `stale-dashboards` | Dashboards **not modified in 180+ days** | Dashboards beyond the first 3 cost $3/month each |

Cost estimates are deliberately rough (us-east-1 standard pricing) — they're there to help you prioritize, not to reconcile your bill.

## Permissions

Least privilege, read-only. Attach [`docs/iam-policy.json`](docs/iam-policy.json):

```json
{
  "Action": [
    "logs:DescribeLogGroups",
    "cloudwatch:DescribeAlarms",
    "cloudwatch:GetMetricData",
    "cloudwatch:ListDashboards"
  ]
}
```

## Contributing

New checks are the easiest way to contribute — each check is a single file in `cw_janitor/checks/` exposing `CHECK_ID`, `TITLE`, and `run(session, region) -> list[Finding]`. See [CONTRIBUTING.md](CONTRIBUTING.md) and the [open issues](../../issues) for ideas (unused custom metrics, orphaned metric filters, Contributor Insights rules...).

## License

MIT
