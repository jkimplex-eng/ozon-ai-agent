"""Tests for deploy module."""
from ozon_agent.deploy.deploy_plan import (
    DeployDecision,
    build_deploy_plan,
    detect_pending_migrations,
    evaluate_deploy_readiness,
    format_plan_text,
    scan_approval_telegram_forbidden,
    scan_decision_modules_forbidden,
)
from ozon_agent.deploy.rollback import format_rollback_text, generate_rollback_commands


def test_deploy_decision_dataclass():
    """Test DeployDecision holds data correctly."""
    decision = DeployDecision(
        deploy_allowed=True,
        reason="All checks passed",
        required_steps=["npm test"],
        risk_level="low",
        supervisor_status="pass",
    )
    assert decision.deploy_allowed is True
    assert decision.risk_level == "low"


def test_deploy_decision_to_dict():
    """Test DeployDecision serialization."""
    decision = DeployDecision(
        deploy_allowed=False,
        reason="Tests failed",
        required_steps=[],
        risk_level="blocked",
        supervisor_status="fail",
    )
    d = decision.to_dict()
    assert d["deploy_allowed"] is False
    assert d["risk_level"] == "blocked"


def test_evaluate_deploy_readiness_pass():
    """Test deployment allowed when all checks pass."""
    results = {
        "total": 10, "passed": 10, "failed": 0,
        "lint_status": "pass", "type_status": "pass",
    }
    decision = evaluate_deploy_readiness("pass", results)
    assert decision.deploy_allowed is True
    assert decision.risk_level == "low"


def test_evaluate_deploy_readiness_fail():
    """Test deployment blocked when supervisor fails."""
    decision = evaluate_deploy_readiness("fail", {"failed": 0})
    assert decision.deploy_allowed is False
    assert decision.risk_level == "blocked"


def test_evaluate_deploy_readiness_test_failures():
    """Test deployment blocked when tests fail."""
    decision = evaluate_deploy_readiness("pass", {"failed": 3})
    assert decision.deploy_allowed is False
    assert decision.risk_level == "blocked"


def test_evaluate_deploy_readiness_medium_risk():
    """Test medium risk when lint fails."""
    decision = evaluate_deploy_readiness("pass", {"failed": 0, "lint_status": "fail"})
    assert decision.deploy_allowed is True
    assert decision.risk_level == "medium"


def test_evaluate_deploy_readiness_tests_skipped():
    """Test medium risk when tests were skipped."""
    decision = evaluate_deploy_readiness("pass", {"total": 0, "passed": 0, "failed": 0})
    assert decision.deploy_allowed is True
    assert decision.risk_level == "medium"
    assert "skipped" in decision.reason


def test_evaluate_deploy_readiness_tests_skipped_with_lint_fail():
    """Test medium risk when tests skipped and lint fails."""
    decision = evaluate_deploy_readiness(
        "pass",
        {"total": 0, "passed": 0, "failed": 0, "lint_status": "fail"},
    )
    assert decision.deploy_allowed is True
    assert decision.risk_level == "medium"
    assert "skipped" in decision.reason
    assert "lint" in decision.reason


def test_build_deploy_plan():
    """Test deploy plan generation."""
    decision = DeployDecision(
        deploy_allowed=True,
        reason="OK",
        required_steps=[],
        risk_level="low",
        supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="vps", branch="main", dry_run=True)
    assert plan.dry_run is True
    assert plan.target == "vps"
    assert len(plan.commands) > 0
    assert len(plan.health_check_commands) > 0
    assert len(plan.rollback_commands) > 0


def test_build_deploy_plan_execute():
    """Test deploy plan in execute mode."""
    decision = DeployDecision(
        deploy_allowed=True,
        reason="OK",
        required_steps=[],
        risk_level="low",
        supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="myhost", branch="dev", dry_run=False)
    assert plan.dry_run is False
    assert "myhost" in plan.commands[0]
    assert "dev" in plan.commands[0]


def test_format_plan_text():
    """Test plan text formatting."""
    decision = DeployDecision(
        deploy_allowed=True,
        reason="All checks passed",
        required_steps=[],
        risk_level="low",
        supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="vps", branch="main", dry_run=True)
    text = format_plan_text(plan, decision)
    assert "DRY RUN" in text
    assert "vps" in text
    assert "main" in text


def test_format_plan_text_execute():
    """Test plan text in execute mode."""
    decision = DeployDecision(
        deploy_allowed=True,
        reason="OK",
        required_steps=[],
        risk_level="low",
        supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="vps", branch="main", dry_run=False)
    text = format_plan_text(plan, decision)
    assert "EXECUTE" in text


def test_generate_rollback_commands():
    """Test rollback command generation."""
    commands = generate_rollback_commands("vps")
    assert len(commands) > 0
    assert "vps" in commands[0]
    assert "HEAD~1" in commands[1]


def test_format_rollback_text():
    """Test rollback text formatting."""
    text = format_rollback_text("myhost")
    assert "myhost" in text
    assert "ROLLBACK" in text


def test_deploy_plan_to_dict():
    """Test DeployPlan serialization."""
    decision = DeployDecision(
        deploy_allowed=True, reason="OK", required_steps=[],
        risk_level="low", supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="vps", branch="main")
    d = plan.to_dict()
    assert d["target"] == "vps"
    assert "commands" in d


def test_evaluate_deploy_readiness_all_warnings():
    """Test medium risk when multiple warnings present."""
    decision = evaluate_deploy_readiness(
        "pass",
        {"total": 0, "passed": 0, "failed": 0, "lint_status": "fail", "type_status": "fail"},
    )
    assert decision.deploy_allowed is True
    assert decision.risk_level == "medium"
    assert "skipped" in decision.reason
    assert "lint" in decision.reason
    assert "type" in decision.reason


def test_scan_decision_modules_forbidden():
    """Test forbidden keyword scan returns list."""
    found = scan_decision_modules_forbidden()
    assert isinstance(found, list)


def test_scan_decision_modules_clean():
    """Test decision modules have no forbidden keywords."""
    found = scan_decision_modules_forbidden()
    assert found == []


def test_evaluate_deploy_readiness_blocks_forbidden():
    """Test deploy blocked when decision modules contain forbidden keywords."""
    from unittest.mock import patch

    with patch(
        "ozon_agent.deploy.deploy_plan.scan_decision_modules_forbidden",
        return_value=["requests.post", "httpx.post"],
    ):
        decision = evaluate_deploy_readiness("pass", {"failed": 0, "total": 10})
        assert decision.deploy_allowed is False
        assert decision.risk_level == "blocked"
        assert "forbidden" in decision.reason.lower()


def test_scan_approval_telegram_forbidden():
    """Test approval/telegram forbidden keyword scan returns list."""
    found = scan_approval_telegram_forbidden()
    assert isinstance(found, list)


def test_scan_approval_telegram_clean():
    """Test approval/telegram modules have no forbidden keywords."""
    found = scan_approval_telegram_forbidden()
    assert found == []


def test_detect_pending_migrations():
    """Test migration detection returns list."""
    migrations = detect_pending_migrations()
    assert isinstance(migrations, list)


def test_detect_pending_migrations_finds_approval():
    """Test migration detection finds approval migration."""
    migrations = detect_pending_migrations()
    has_approval = any("approval" in m.lower() or "recommendation" in m.lower() for m in migrations)
    assert has_approval


def test_format_plan_text_shows_migration():
    """Test deploy plan text shows migration info."""
    decision = DeployDecision(
        deploy_allowed=True, reason="OK", required_steps=[],
        risk_level="low", supervisor_status="pass",
    )
    plan = build_deploy_plan(decision, target="vps", branch="main", dry_run=True)
    text = format_plan_text(plan, decision)
    assert "Migration" in text or "migration" in text
