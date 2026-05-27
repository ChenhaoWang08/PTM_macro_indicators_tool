# AGENTS.md

- This is a local-first macroeconomic research dashboard.
- Do not add trading, broker, order execution, or investment-advice features.
- Do not fetch live data in tests.
- Use fixture CSV files for tests.
- Every indicator must expose source, frequency, unit, and status.
- If data is missing, return Insufficient Data instead of fake values.
- Keep changes small and reviewable.
- Before reporting completion, run pytest.
- Report files changed, implementation summary, tests run, limitations, and next suggested PR.

