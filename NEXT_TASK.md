# NEXT_TASK.md

## Phase 4.5: Approval Workflow

**Status:** Implemented / Integrated

### Completed

- Approval workflow with state machine (PENDING → APPROVED → EXECUTED → OBSERVED → CLOSED)
- Outcome tracking with forecast error and success scoring
- CLI: approvals list/show/approve/reject/mark-executed/mark-observed/close/outcomes
- CLI: recommendations --save-pending with duplicate prevention
- Telegram bot: /recommendations approve/reject/show
- Supervisor: forbidden keyword scanning for approval/telegram modules
- Deployer: migration detection, forbidden keyword blocking
- Migration: 002_recommendations_approval.sql

### Remaining

1. **Outcome learning** — use outcome data to improve recommendation confidence
2. **Low-risk auto-approval** — auto-approve HIGH confidence + LOW risk recommendations
3. **Notification system** — alert when new recommendations generated
4. **Historical analytics** — aggregate outcome data for model improvement

## Phase 5: Autonomous Experiments

**Status:** Pending

### Scope

- A/B testing framework for seller actions
- Automated experiment tracking
- Statistical significance evaluation
