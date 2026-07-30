# Contributing

Thanks for stopping by! The easiest contribution is a **new check**.

## Adding a check

1. Create `cw_janitor/checks/your_check.py` exposing:
   - `CHECK_ID` (kebab-case string)
   - `TITLE` (one line)
   - `run(session, region) -> list[Finding]`
2. Register it in `ALL_CHECKS` in `cw_janitor/cli.py`.
3. Add a Stubber-based test in `tests/` (see `tests/test_checks_stubbed.py` — no AWS account needed).
4. If the check needs a new IAM permission, add it to `docs/iam-policy.json` and the README table.

Rules of the house:
- **Read-only, always.** No check may modify anything.
- **boto3 only.** No new runtime dependencies.
- Cost estimates are rough by design — document your pricing assumption in the module docstring.

## Dev setup

```bash
pip install -e . ruff pytest
ruff check .
pytest
```

CI runs the same two commands on Python 3.10 and 3.12.

## Check ideas (help wanted)

- Unused custom metrics (namespaces with no alarms/dashboards referencing them)
- Orphaned metric filters on deleted log groups
- Contributor Insights rules nobody queries
- Dashboards whose widgets reference metrics that no longer exist
- Log groups with Infrequent Access class candidates
