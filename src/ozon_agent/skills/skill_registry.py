from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ozon_agent.skills.skill_loader import SkillDefinition

_REGISTRY: dict[str, SkillDefinition] = {}


def register_skill(skill: SkillDefinition) -> None:
    _REGISTRY[skill.name] = skill


def unregister_skill(name: str) -> None:
    _REGISTRY.pop(name, None)


def skill_exists(name: str) -> bool:
    return name in _REGISTRY


def get_registered_skill(name: str) -> SkillDefinition | None:
    return _REGISTRY.get(name)


def list_registered_skills() -> list[SkillDefinition]:
    return [_REGISTRY[name] for name in sorted(_REGISTRY)]


def clear_registry() -> None:
    _REGISTRY.clear()
