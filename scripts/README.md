# scripts/

| Script | What it's for | Run |
|---|---|---|
| `create_test_accounts.py` | Signs up the README's two test logins through the normal sign-up endpoint. Safe to re-run | `.venv/bin/python scripts/create_test_accounts.py [--base URL]` |
| `security_check.sh` | 30 curl checks (S1–S30) of the access rules against a running server; PASS/FAIL per check | `BASE=http://127.0.0.1:8000 scripts/security_check.sh` → `30 passed, 0 failed` |
| `browser_check/` | Drives the real pages in headless Chrome: 52 checks plus screenshots | see [browser_check/README.md](browser_check/README.md) |
| `data_audit/` | The scripts that found the problems in the two CSVs | see [data_audit/README.md](data_audit/README.md) |

`security_check.sh` needs `bash`, `curl` and `python3` only. It creates the test logins if they're missing and signs
up `ruth.grant@brightline.example` (password `frontdesk-test`) for S11. What each check does:
[../docs/SECURITY_TESTS.md](../docs/SECURITY_TESTS.md) section 8. The same checks walked through by hand:
[../docs/TESTING_WITH_CURL.md](../docs/TESTING_WITH_CURL.md).
