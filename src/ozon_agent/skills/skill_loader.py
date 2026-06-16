from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from ozon_agent.skills.skill_registry import (
    clear_registry,
    get_registered_skill,
    list_registered_skills,
    register_skill,
)


@dataclass(slots=True)
class SkillDefinition:
    name: str
    path: Path
    skill_md_path: Path
    rules_md_path: Path
    examples_md_path: Path
    skill_md: str
    rules_md: str
    examples_md: str


class SkillLoaderError(ValueError):
    pass


class SkillNotFoundError(LookupError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Skill {name} not found")
        self.name = name


def load_skills(
    index_path: Path | None = None,
    skills_root: Path | None = None,
) -> list[SkillDefinition]:
    resolved_skills_root = _resolve_skills_root(skills_root)
    resolved_index_path = index_path or resolved_skills_root / "index.yaml"
    skill_names = _load_index(resolved_index_path)
    loaded_skills = [_load_skill(skill_name, resolved_skills_root) for skill_name in skill_names]
    clear_registry()
    for skill in loaded_skills:
        register_skill(skill)
    return list_registered_skills()


def get_skill(name: str) -> SkillDefinition:
    skill = get_registered_skill(name)
    if skill is None:
        raise SkillNotFoundError(name)
    return skill


def list_skills() -> list[SkillDefinition]:
    return list_registered_skills()


def reload_skills(
    index_path: Path | None = None,
    skills_root: Path | None = None,
) -> list[SkillDefinition]:
    return load_skills(index_path=index_path, skills_root=skills_root)


def _resolve_skills_root(skills_root: Path | None) -> Path:
    if skills_root is not None:
        return skills_root
    return Path(__file__).resolve().parents[3] / "skills"


def _load_index(index_path: Path) -> list[str]:
    if not index_path.exists():
        raise SkillLoaderError(f"Skills index not found: {index_path}")
    payload = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise SkillLoaderError("skills/index.yaml must contain a mapping")
    skill_names = payload.get("skills")
    if not isinstance(skill_names, list) or not all(isinstance(item, str) for item in skill_names):
        raise SkillLoaderError("skills/index.yaml must contain skills: list[str]")
    return [item.strip() for item in skill_names if item.strip()]


def _load_skill(name: str, skills_root: Path) -> SkillDefinition:
    skill_path = skills_root / name
    if not skill_path.exists() or not skill_path.is_dir():
        raise SkillLoaderError(f"Skill directory missing for {name}: {skill_path}")

    skill_md_path = skill_path / "SKILL.md"
    rules_md_path = skill_path / "rules.md"
    examples_md_path = skill_path / "examples.md"

    missing_files = [
        str(path.name)
        for path in (skill_md_path, rules_md_path, examples_md_path)
        if not path.exists()
    ]
    if missing_files:
        joined = ", ".join(missing_files)
        raise SkillLoaderError(f"Skill {name} is missing required files: {joined}")

    return SkillDefinition(
        name=name,
        path=skill_path,
        skill_md_path=skill_md_path,
        rules_md_path=rules_md_path,
        examples_md_path=examples_md_path,
        skill_md=skill_md_path.read_text(encoding="utf-8"),
        rules_md=rules_md_path.read_text(encoding="utf-8"),
        examples_md=examples_md_path.read_text(encoding="utf-8"),
    )
