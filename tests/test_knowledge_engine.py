from __future__ import annotations

from ozon_agent.decision.market_context import MarketContext
from ozon_agent.decision.models import DecisionFeature, Opportunity, OpportunityType
from ozon_agent.knowledge.engine import (
    build_knowledge_context,
    evaluate_rules,
    find_relevant_rules,
)
from ozon_agent.knowledge.models import KnowledgeDomain


def test_find_relevant_rules() -> None:
    rules = find_relevant_rules("CTR")

    assert rules
    assert any(rule.domain is KnowledgeDomain.RANKING for rule in rules)


def test_evaluate_rules_for_low_ctr() -> None:
    feature = DecisionFeature(sku="SKU-1", product_name="", ctr=1.2, clicks=100, ad_orders=1)

    recommendations = evaluate_rules(feature)

    rule_ids = {item.rule_id for item in recommendations}
    assert "seo-title-query" in rule_ids
    assert "ranking-ctr-position" in rule_ids


def test_build_knowledge_context_with_market_pressure() -> None:
    feature = DecisionFeature(sku="SKU-1", product_name="Product", price=1200)
    opportunity = Opportunity(
        opportunity_type=OpportunityType.PRICE_CONVERSION,
        sku="SKU-1",
        severity="high",
        impact_score=0.7,
        reason="conversion declined",
        metrics={},
    )
    context = build_knowledge_context(
        feature,
        opportunity,
        MarketContext(price_pressure="HIGH", review_pressure="HIGH"),
    )

    rule_ids = {rule["rule_id"] for rule in context["knowledge_rules"]}
    assert "pricing-market-premium" in rule_ids
    assert "reviews-competitor-surge" in rule_ids
    assert context["knowledge_sources"]
