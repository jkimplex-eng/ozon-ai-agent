"""Tests for supervisor module."""
from ozon_agent.supervisor.collectors import (
    detect_architecture_risks,
    get_changed_files,
    get_git_status,
    get_roadmap_alignment,
    get_test_results,
    recommend_next_task,
)
from ozon_agent.supervisor.report import AuditReport, format_report_text


def test_audit_report_dataclass():
    """Test AuditReport holds data correctly."""
    report = AuditReport(
        builder_type="codex",
        task_goal="Implement Phase 3",
        timestamp="2026-06-13T00:00:00",
        git_status="clean",
        changed_files=["src/file.py"],
        test_results={"total": 10, "passed": 10, "failed": 0},
        roadmap_alignment={"completed": ["Phase 1"], "remaining": ["Phase 2"]},
        architecture_risks=["risk1"],
        recommended_next_task="Phase 2",
        summary="All good",
    )
    assert report.builder_type == "codex"
    assert report.task_goal == "Implement Phase 3"
    assert len(report.changed_files) == 1


def test_audit_report_to_dict():
    """Test AuditReport serialization."""
    report = AuditReport(
        builder_type="mimo",
        task_goal="test",
        timestamp="2026-01-01",
        git_status="clean",
        changed_files=[],
        test_results={},
        roadmap_alignment={},
        architecture_risks=[],
        recommended_next_task="none",
        summary="test",
    )
    d = report.to_dict()
    assert d["builder_type"] == "mimo"
    assert "changed_files" in d
    assert "deploy_decision" not in d


def test_audit_report_with_deploy_decision():
    """Test AuditReport includes deploy_decision when provided."""
    report = AuditReport(
        builder_type="mimo",
        task_goal="deploy",
        timestamp="2026-01-01",
        git_status="clean",
        changed_files=[],
        test_results={},
        roadmap_alignment={},
        architecture_risks=[],
        recommended_next_task="none",
        summary="test",
        deploy_decision={
            "deploy_allowed": True,
            "reason": "All checks passed",
            "risk_level": "low",
        },
    )
    d = report.to_dict()
    assert "deploy_decision" in d
    assert d["deploy_decision"]["deploy_allowed"] is True


def test_format_report_text():
    """Test report text formatting."""
    report = AuditReport(
        builder_type="cursor",
        task_goal="Fix bug",
        timestamp="2026-06-13",
        git_status="2 files modified",
        changed_files=["a.py", "b.py"],
        test_results={
            "total": 5, "passed": 5, "failed": 0,
            "lint_status": "pass", "type_status": "pass",
        },
        roadmap_alignment={
            "current_phase": "Phase 3",
            "completed": ["Phase 1", "Phase 2"],
            "remaining": ["Phase 4"],
        },
        architecture_risks=[],
        recommended_next_task="Phase 4",
        summary="Done",
    )
    text = format_report_text(report)
    assert "cursor" in text
    assert "Fix bug" in text
    assert "a.py" in text
    assert "Phase 4" in text


def test_get_git_status():
    """Test git status collector returns string."""
    status = get_git_status()
    assert isinstance(status, str)


def test_get_changed_files():
    """Test changed files collector returns list."""
    files = get_changed_files()
    assert isinstance(files, list)


def test_get_test_results():
    """Test test results collector returns dict."""
    results = get_test_results()
    assert "total" in results
    assert "passed" in results
    assert "lint_status" in results


def test_get_roadmap_alignment():
    """Test roadmap alignment returns current state."""
    alignment = get_roadmap_alignment()
    assert "current_phase" in alignment
    assert "completed" in alignment
    assert "remaining" in alignment
    assert len(alignment["completed"]) > 0


def test_detect_architecture_risks():
    """Test risk detection returns list."""
    risks = detect_architecture_risks()
    assert isinstance(risks, list)


def test_recommend_next_task():
    """Test next task recommendation."""
    task = recommend_next_task(["Data Warehouse", "Analytics & Diagnostics", "Forecasting"])
    assert "Decision Engine" in task

    task2 = recommend_next_task(["Data Warehouse", "Analytics & Diagnostics"])
    assert "Forecasting" in task2

    task3 = recommend_next_task(["Data Warehouse"])
    assert "Analytics" in task3
