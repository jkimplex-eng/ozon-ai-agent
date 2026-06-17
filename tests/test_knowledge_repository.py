from __future__ import annotations

from ozon_agent.knowledge.models import (
    KnowledgeDomain,
    KnowledgeExperiment,
    KnowledgeRule,
    KnowledgeSource,
)
from ozon_agent.knowledge.repository import (
    list_domains,
    list_experiments,
    list_rules,
    load_rules,
    save_experiment,
    save_rule,
    search_experiments,
    search_rules,
)


def test_load_default_rules() -> None:
    rules = load_rules()
    domains = {rule.domain for rule in rules}

    assert KnowledgeDomain.SEO in domains
    assert KnowledgeDomain.RANKING in domains
    assert KnowledgeDomain.ADS in domains
    assert any("CTR" in rule.title or "CTR" in rule.condition for rule in rules)


def test_list_domains() -> None:
    assert KnowledgeDomain.SEO in list_domains()
    assert KnowledgeDomain.EXPERIMENTS in list_domains()


def test_search_rules() -> None:
    matches = search_rules("CTR")

    assert matches
    assert any(rule.domain in {KnowledgeDomain.RANKING, KnowledgeDomain.ADS} for rule in matches)


def test_save_rule_round_trip(tmp_path) -> None:
    rule = KnowledgeRule(
        id="test-rule",
        domain=KnowledgeDomain.SEO,
        title="Test rule",
        condition="Test condition",
        recommendation="Test recommendation",
        rationale="Test rationale",
        signals=["low_ctr"],
        source=KnowledgeSource(name="test", path="seo/rules.yaml"),
    )

    save_rule(rule, root=tmp_path)

    assert list_rules(KnowledgeDomain.SEO, root=tmp_path) == [rule]


def test_experiment_knowledge_round_trip(tmp_path) -> None:
    experiment = KnowledgeExperiment(
        id="exp-1",
        title="Photo CTR test",
        domain=KnowledgeDomain.EXPERIMENTS,
        hypothesis="Changing photo increases CTR",
        metric="CTR",
    )

    save_experiment(experiment, root=tmp_path)

    assert list_experiments(root=tmp_path) == [experiment]
    assert search_experiments("photo", root=tmp_path) == [experiment]
