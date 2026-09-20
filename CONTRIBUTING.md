# Contributing

Thank you for helping improve FREELY.

## Before opening a change

1. Create a branch from the latest default branch.
2. Keep changes focused and add tests for changed behavior.
3. Use only synthetic data in fixtures and examples.
4. Do not include credentials, personal data, private job alerts, client messages, or marketplace
   session data.
5. Preserve the manual review boundary: no automatic bidding, client messaging, or control bypass.

## Local checks

```bash
python -m pip install -e ".[dev]"
pytest
ruff check app tests
```

Pull requests should explain the problem, the approach, the tests performed, and any security or
platform-policy implications.
