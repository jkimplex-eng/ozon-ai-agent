# NEXT_TASK.md

## Phase 5: Autonomous Experiments

**Status:** Implemented / Integrated

### Completed

- Experiment models, repository, workflow
- Experiment lifecycle with state machine
- Experiment events with audit trail
- Metrics tracking and evaluation
- CLI: all experiment commands with --json support
- Telegram: /experiments commands for state management
- Migration: 003_experiments.sql
- Supervisor scans experiments module for forbidden keywords
- Deploy plan detects experiments migration and module
- Create experiment from recommendation (APPROVED/EXECUTED only)
- Report formatter with baseline/current/result display
- Tests: experiment CLI, telegram experiments, smoke tests

### Remaining

1. **Experiment result automation** — auto-evaluate on completion
2. **Guarded auto-approval** — auto-approve low-risk experiments
3. **Experiment dashboard** — aggregate experiment data visualization
4. **Phase 6** — Advanced analytics and optimization
