# ENGINEERING_RULES.md

## Code Style

- **Line length:** 100 chars (ruff)
- **Target:** Python 3.11+
- **Type checking:** mypy strict
- **Linting:** ruff with E, F, I, N, W, UP rules
- **No comments** unless explicitly asked

## Conventions

- Dataclasses for internal data structures (not Pydantic for pure data)
- Pydantic for API boundaries and settings
- `click` for CLI commands
- `rich` for terminal output
- `subprocess.run` for git/tool commands (with timeout)
- SSH key auth only — never store passwords in code

## Testing

- pytest with `tests/` directory
- Unit tests for pure logic
- Integration tests mock external calls (subprocess, SSH)
- Run before commit:
  ```
  python -m ruff check src/ tests/
  python -m mypy src/
  python -m pytest tests/ -v
  ```

## Deployment Safety

- Default mode is dry-run
- Never deploy if supervisor status is FAIL
- Warn if tests were skipped
- Show exact commands before execution
- Require `--execute` flag for real deployment
- Health check after deploy
- Rollback command on health check failure
- VPS commands: SSH key only, no destructive operations

## Git

- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- One logical change per commit
- Never force-push to main
- Never amend published commits

## File Organization

```
src/ozon_agent/
  api/          # External API clients
  db/           # Database connections and queries
  etl/          # Data extraction and loading
  analytics/    # Data analysis and diagnostics
  forecast/     # Prediction models
  supervisor/   # Audit and deployment decisions
  deploy/       # VPS deployment execution
  models/       # Pydantic data models
  cli.py        # Click CLI entry point
```
