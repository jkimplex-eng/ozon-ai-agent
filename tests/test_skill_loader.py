from pathlib import Path

from ozon_agent.skills.skill_loader import (
    SkillLoaderError,
    get_skill,
    list_skills,
    load_skills,
    reload_skills,
)
from ozon_agent.skills.skill_registry import skill_exists


def test_load_skills(tmp_path: Path) -> None:
    skills_root = _build_skills_fixture(tmp_path)
    loaded = load_skills(skills_root=skills_root)
    assert [skill.name for skill in loaded] == ["analyst", "forecasting"]
    assert skill_exists("analyst")
    assert get_skill("forecasting").skill_md.startswith("# forecasting")


def test_missing_skill_file_raises(tmp_path: Path) -> None:
    skills_root = _build_skills_fixture(tmp_path)
    (skills_root / "analyst" / "examples.md").unlink()
    try:
        load_skills(skills_root=skills_root)
    except SkillLoaderError as exc:
        assert "missing required files" in str(exc)
    else:
        raise AssertionError("Expected SkillLoaderError")


def test_invalid_structure_raises(tmp_path: Path) -> None:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "index.yaml").write_text("skills: analyst\n", encoding="utf-8")
    try:
        load_skills(skills_root=skills_root)
    except SkillLoaderError as exc:
        assert "skills: list[str]" in str(exc)
    else:
        raise AssertionError("Expected SkillLoaderError")


def test_reload_skills_refreshes_registry(tmp_path: Path) -> None:
    skills_root = _build_skills_fixture(tmp_path)
    load_skills(skills_root=skills_root)
    _write_skill(skills_root, "ozon_api")
    (skills_root / "index.yaml").write_text(
        "skills:\n  - analyst\n  - forecasting\n  - ozon_api\n",
        encoding="utf-8",
    )
    reloaded = reload_skills(skills_root=skills_root)
    assert [skill.name for skill in reloaded] == ["analyst", "forecasting", "ozon_api"]
    assert len(list_skills()) == 3


def _build_skills_fixture(tmp_path: Path) -> Path:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "index.yaml").write_text(
        "skills:\n  - analyst\n  - forecasting\n",
        encoding="utf-8",
    )
    _write_skill(skills_root, "analyst")
    _write_skill(skills_root, "forecasting")
    return skills_root


def _write_skill(skills_root: Path, name: str) -> None:
    skill_path = skills_root / name
    skill_path.mkdir()
    (skill_path / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    (skill_path / "rules.md").write_text(f"# {name} rules\n", encoding="utf-8")
    (skill_path / "examples.md").write_text(f"# {name} examples\n", encoding="utf-8")
