# Contributing

## Development prerequisites

1. Python 3.11+
2. `uv` installed
3. Docker (for Hydra and production compose scenarios)

## Workflow

1. Create a branch from `main`.
2. Make focused changes.
3. Add/adjust tests for behavior changes.
4. Run:

```bash
cd agent_idp_service
uv run --extra dev pytest
```

5. Submit a PR with:
- Problem statement
- Change summary
- Test evidence
- Security impact notes (if auth/policy/token logic changed)

## Code standards

1. Keep security-sensitive behavior explicit.
2. Preserve compatibility with claim structure documented in `JWT.md`.
3. Do not commit secrets, private keys, local env files, or generated data.
4. Use `uv` instead of `pip`.
