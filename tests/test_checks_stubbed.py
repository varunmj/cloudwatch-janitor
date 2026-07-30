"""Check logic tests using botocore Stubber — no AWS account needed."""
from datetime import datetime, timedelta, timezone

import boto3
from botocore.stub import Stubber

from cw_janitor.checks import log_retention, stale_alarms


class StubSession:
    """Minimal boto3.Session stand-in returning pre-stubbed clients."""

    def __init__(self, clients):
        self._clients = clients

    def client(self, name, region_name=None):
        return self._clients[name]


def test_log_retention_flags_only_unset_groups():
    logs = boto3.client("logs", region_name="us-east-1",
                        aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(logs)
    stub.add_response("describe_log_groups", {
        "logGroups": [
            {"logGroupName": "/keep/me", "retentionInDays": 30, "storedBytes": 10**9},
            {"logGroupName": "/flag/me", "storedBytes": 2 * 1024**3},
        ]
    }, {})
    stub.activate()

    findings = log_retention.run(StubSession({"logs": logs}), "us-east-1")
    assert len(findings) == 1
    assert findings[0].resource == "/flag/me"
    assert findings[0].est_monthly_cost == 0.06  # 2 GB * $0.03


def test_stale_alarms_respects_cutoff():
    cw = boto3.client("cloudwatch", region_name="us-east-1",
                      aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(cw)
    old = datetime.now(timezone.utc) - timedelta(days=90)
    recent = datetime.now(timezone.utc) - timedelta(days=2)
    stub.add_response("describe_alarms", {
        "MetricAlarms": [
            {"AlarmName": "very-stale", "StateUpdatedTimestamp": old},
            {"AlarmName": "just-flapping", "StateUpdatedTimestamp": recent},
        ]
    }, {"StateValue": "INSUFFICIENT_DATA"})
    stub.activate()

    findings = stale_alarms.run(StubSession({"cloudwatch": cw}), "us-east-1")
    assert [f.resource for f in findings] == ["very-stale"]
