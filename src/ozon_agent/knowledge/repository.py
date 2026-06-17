from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ozon_agent.knowledge.models import (
    KnowledgeDomain,
    KnowledgeExperiment,
    KnowledgeRule,
    KnowledgeSource,
)

DEFAULT_KNOWLEDGE_ROOT = Path("knowledge")


def knowledge_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("OZON_AGENT_KNOWLEDGE_ROOT")
    return Path(env_root) if env_root else DEFAULT_KNOWLEDGE_ROOT


def load_rules(root: str | Path | None = None) -> list[KnowledgeRule]:
    rules: list[KnowledgeRule] = []
    base = knowledge_root(root)
    if not base.exists():
        return []
    for path in sorted(base.glob("*/rules.yaml")):
        rules.extend(_load_rule_file(path, base))
    return sorted(rules, key=lambda rule: (rule.domain.value, rule.id))


def list_rules(
    domain: KnowledgeDomain | str | None = None,
    root: str | Path | None = None,
) -> list[KnowledgeRule]:
    rules = load_rules(root)
    if domain is None:
        return rules
    domain_value = _coerce_domain(domain)
    return [rule for rule in rules if rule.domain is domain_value]


def save_rule(rule: KnowledgeRule, root: str | Path | None = None) -> KnowledgeRule:
    base = knowledge_root(root)
    path = base / rule.domain.value.lower() / "rules.yaml"
    existing = list_rules(rule.domain, root=base)
    merged = [item for item in existing if item.id != rule.id]
    merged.append(rule)
    _write_rule_file(path, sorted(merged, key=lambda item: item.id))
    return rule


def search_rules(query: str, root: str | Path | None = None) -> list[KnowledgeRule]:
    normalized = query.strip().lower()
    if not normalized:
        return list_rules(root=root)
    return [
        rule
        for rule in load_rules(root)
        if normalized in _rule_search_text(rule)
    ]


def list_domains() -> list[KnowledgeDomain]:
    return list(KnowledgeDomain)


def save_experiment(
    experiment: KnowledgeExperiment,
    root: str | Path | None = None,
) -> KnowledgeExperiment:
    base = knowledge_root(root)
    path = base / "experiments" / "experiments.yaml"
    experiments = [item for item in list_experiments(root=base) if item.id != experiment.id]
    experiments.append(experiment)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"experiments": [_experiment_to_dict(item) for item in experiments]},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return experiment


def list_experiments(root: str | Path | None = None) -> list[KnowledgeExperiment]:
    path = knowledge_root(root) / "experiments" / "experiments.yaml"
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = payload.get("experiments", []) if isinstance(payload, dict) else []
    return [_experiment_from_dict(row) for row in rows if isinstance(row, dict)]


def search_experiments(query: str, root: str | Path | None = None) -> list[KnowledgeExperiment]:
    normalized = query.strip().lower()
    if not normalized:
        return list_experiments(root=root)
    return [
        experiment
        for experiment in list_experiments(root=root)
        if normalized in " ".join(
            [
                experiment.id,
                experiment.title,
                experiment.hypothesis,
                experiment.metric,
                experiment.domain.value,
            ]
        ).lower()
    ]


def _load_rule_file(path: Path, base: Path) -> list[KnowledgeRule]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = payload.get("rules", []) if isinstance(payload, dict) else []
    return [
        _rule_from_dict(row, source_path=path, base=base)
        for row in rows
        if isinstance(row, dict)
    ]


def _write_rule_file(path: Path, rules: list[KnowledgeRule]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"rules": [_rule_to_dict(rule) for rule in rules]},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _rule_from_dict(row: dict[str, Any], source_path: Path, base: Path) -> KnowledgeRule:
    domain = _coerce_domain(str(row.get("domain") or source_path.parent.name))
    source = KnowledgeSource(
        name=str(row.get("source") or source_path.parent.name),
        path=source_path.relative_to(base).as_posix(),
    )
    return KnowledgeRule(
        id=str(row["id"]),
        domain=domain,
        title=str(row.get("title", "")),
        condition=str(row.get("condition", "")),
        recommendation=str(row.get("recommendation", "")),
        rationale=str(row.get("rationale", "")),
        signals=[str(signal) for signal in row.get("signals", [])],
        source=source,
        metadata=row.get("metadata", {}) if isinstance(row.get("metadata", {}), dict) else {},
    )


def _rule_to_dict(rule: KnowledgeRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "domain": rule.domain.value,
        "title": rule.title,
        "condition": rule.condition,
        "recommendation": rule.recommendation,
        "rationale": rule.rationale,
        "signals": list(rule.signals),
        "source": rule.source.name if rule.source else "",
        "metadata": dict(rule.metadata),
    }


def _experiment_to_dict(experiment: KnowledgeExperiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "title": experiment.title,
        "domain": experiment.domain.value,
        "hypothesis": experiment.hypothesis,
        "metric": experiment.metric,
        "source": experiment.source,
        "metadata": dict(experiment.metadata),
    }


def _experiment_from_dict(row: dict[str, Any]) -> KnowledgeExperiment:
    return KnowledgeExperiment(
        id=str(row["id"]),
        title=str(row.get("title", "")),
        domain=_coerce_domain(str(row.get("domain", "EXPERIMENTS"))),
        hypothesis=str(row.get("hypothesis", "")),
        metric=str(row.get("metric", "")),
        source=str(row.get("source", "knowledge")),
        metadata=row.get("metadata", {}) if isinstance(row.get("metadata", {}), dict) else {},
    )


def _rule_search_text(rule: KnowledgeRule) -> str:
    return " ".join(
        [
            rule.id,
            rule.domain.value,
            rule.title,
            rule.condition,
            rule.recommendation,
            rule.rationale,
            " ".join(rule.signals),
        ]
    ).lower()


def _coerce_domain(domain: KnowledgeDomain | str) -> KnowledgeDomain:
    if isinstance(domain, KnowledgeDomain):
        return domain
    normalized = domain.strip().upper()
    return KnowledgeDomain(normalized)
