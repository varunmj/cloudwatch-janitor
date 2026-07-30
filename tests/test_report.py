from cw_janitor.report import Finding, render_json, render_table, total_savings


def _sample():
    return [
        Finding("log-retention", "/aws/lambda/old-fn", "No retention policy (4.20 GB stored)", 0.13,
                "Set retention"),
        Finding("stale-alarms", "orphan-alarm", "INSUFFICIENT_DATA for 90 days", 0.10,
                "Delete alarm"),
        Finding("stale-dashboards", "old-dash", "Not modified in 300 days", None, "Review"),
    ]


def test_total_savings_ignores_none():
    assert abs(total_savings(_sample()) - 0.23) < 1e-9


def test_render_table_contains_rows_and_total():
    out = render_table(_sample())
    assert "log-retention" in out
    assert "orphan-alarm" in out
    assert "$0.23/month" in out


def test_render_table_empty():
    assert "No waste found" in render_table([])


def test_render_json_shape():
    import json
    payload = json.loads(render_json(_sample()))
    assert payload["total_findings"] == 3
    assert payload["estimated_monthly_savings_usd"] == 0.23
    assert payload["findings"][0]["check"]
