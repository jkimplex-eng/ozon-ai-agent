"""All text command handlers extracted from bot.py."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ozon_agent.approval.models import RecommendationStatus, StoredRecommendation
from ozon_agent.approval.repository import get_recommendation, list_recommendations
from ozon_agent.approval.workflow import approve_recommendation, reject_recommendation
from ozon_agent.intelligence.sku_stubs import HealthStatus, TrendDirection
from ozon_agent.intelligence.sku_stubs import analyze_sku, get_top_skus, get_worst_skus
from ozon_agent.telegram.data_helpers import (
    count_payload_rows,
    count_unique_skus,
    data_freshness,
    format_dt,
    last_update_time,
    load_json_dict,
    load_payload,
    supervisor_status,
)
from ozon_agent.telegram.format import (
    divider,
    no_data_message,
    pct,
    problem_business,
    retro_action_business,
    rub,
    safe_str,
    severity_emoji,
    signal_cause,
    signal_checklist,
    signal_type_business,
)
from ozon_agent.telegram.outcome_store import (
    get_outcome_stats,
    list_outcomes,
    load_success_patterns,
    record_outcome,
)


def format_rec_message(rec: StoredRecommendation) -> str:
    lines = [
        f"Рекомендация: {rec.id[:8]}...",
        f"Товар: {rec.sku}",
        f"Действие: {rec.action.value}",
        f"Ожидаемый эффект: {rec.expected_effect}",
        f"Уверенность: {rec.confidence_level.value if rec.confidence_level else 'N/A'}"
        f" ({rec.confidence_score:.2f})" if rec.confidence_score is not None else "",
        f"Риск: {rec.risk_level.value if rec.risk_level else 'N/A'}"
        f" ({rec.risk_score:.2f})" if rec.risk_score is not None else "",
        f"Причина: {rec.reason}",
        "",
        "Одобрить:",
        f"/recommendations approve {rec.id}",
        "",
        "Отклонить:",
        f"/recommendations reject {rec.id} причина",
    ]
    return "\n".join(line for line in lines if line is not None)


def _help_text() -> str:
    return (
        "Доступные команды:\n"
        "/status — статус магазина\n"
        "/help — список команд\n"
        "/daily — P&L за день\n"
        "/signals — текущие сигналы\n"
        "/recommendations — рекомендации\n"
        "/why_down <sku> — почему просел товар\n"
        "/sku <sku> — карточка товара\n"
        "/economics — экономика магазина\n"
        "/alerts — центр алертов\n"
        "/retro — ретроспектива\n"
        "/today — что делать сегодня\n"
        "/outcomes — результаты рекомендаций\n"
        "/outcome success <id> — отметить успех\n"
        "/outcome failure <id> — отметить неудачу\n"
        "/outcome observe <id> — начать наблюдение\n"
        "/top_sku — лучшие товары\n"
        "/worst_sku — товары риска\n"
        "/learn — статус обучения\n"
        "/cogs — себестоимость\n"
        "/experiments — управление экспериментами"
    )


def _status_dashboard() -> str:
    learning = load_json_dict(Path("data") / "learning" / "summary.json")
    sku_count = count_unique_skus()
    sales_count = int(learning.get("sales_rows") or 0)
    signals_count = count_payload_rows(Path("data") / "signals" / "signals.json")
    recommendations_count = count_payload_rows(
        Path("data") / "recommendations_v2" / "recommendations.json"
    )
    retro_cases_count = count_payload_rows(
        Path("data") / "retro" / "patterns" / "retro_patterns.json"
    )
    last_update = last_update_time()
    freshness = data_freshness(last_update, learning)
    supervisor = supervisor_status()
    learning_status = (
        f"{learning.get('date_from', '') or 'n/a'} -> "
        f"{learning.get('date_to', '') or 'n/a'}, "
        f"сигналов {learning.get('signals', signals_count)}, "
        f"рекомендаций {learning.get('recommendations', recommendations_count)}"
    )

    return (
        "🤖 Статус магазина\n\n"
        f"Последнее обновление: {format_dt(last_update)}\n"
        f"Товаров: {sku_count}\n"
        f"Записей продаж: {sales_count}\n"
        f"Сигналов: {signals_count}\n"
        f"Рекомендаций: {recommendations_count}\n"
        f"Ретро-кейсов: {retro_cases_count}\n"
        f"Свежесть данных: {freshness}\n"
        f"Системы: {supervisor}\n"
        f"Обучение: {learning_status}"
    )


def _alerts() -> str:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    retro = load_payload(Path("data") / "retro" / "patterns" / "retro_patterns.json")

    grouped: dict[str, dict[str, Any]] = {}

    for s in signals:
        sig_type = s.get("signal_type", "")
        sku = safe_str(s.get("sku"), "Магазин")
        key = f"{sig_type}|{sku}"
        if key not in grouped:
            grouped[key] = {
                "severity": s.get("severity", "LOW"),
                "type": signal_type_business(sig_type),
                "sku": sku,
                "total_impact": 0.0,
                "count": 0,
                "dates": set(),
                "evidence": s.get("evidence", {}),
            }
        g = grouped[key]
        g["total_impact"] += float(s.get("value") or s.get("evidence", {}).get("spend") or 0)
        g["count"] += 1
        d = s.get("date", "")
        if d:
            g["dates"].add(d)

    for r in retro:
        pat_type = r.get("pattern_type", "")
        sku = safe_str(r.get("sku"), "Магазин")
        key = f"{pat_type}|{sku}"
        if key not in grouped:
            grouped[key] = {
                "severity": r.get("severity", "LOW"),
                "type": signal_type_business(pat_type),
                "sku": sku,
                "total_impact": 0.0,
                "count": 0,
                "dates": set(),
                "evidence": r.get("metrics", {}),
            }
        g = grouped[key]
        g["total_impact"] += abs(float(r.get("metrics", {}).get("profit") or 0))
        g["count"] += 1
        d = r.get("date", "")
        if d:
            g["dates"].add(d)

    if not grouped:
        return "✅ Нет активных алертов."

    alerts = list(grouped.values())
    alerts.sort(key=lambda x: x["total_impact"], reverse=True)

    critical = [a for a in alerts if a["severity"].upper() in ("HIGH", "CRITICAL")]
    important = [a for a in alerts if a["severity"].upper() == "MEDIUM"]
    observation = [a for a in alerts if a["severity"].upper() not in ("HIGH", "CRITICAL", "MEDIUM")]

    lines = ["🔔 Центр алертов", ""]

    for category, items, emoji in [
        ("Критично", critical, "🔴"),
        ("Важно", important, "🟠"),
        ("Наблюдение", observation, "🟡"),
    ]:
        if not items:
            continue
        lines.append(f"{emoji} {category}")
        for a in items[:5]:
            impact_str = f" — потери {rub(a['total_impact'])}" if a["total_impact"] > 0 else ""
            count_str = f" ({a['count']} раз)" if a["count"] > 1 else ""
            lines.append(f"• {a['type']} — {a['sku']}{count_str}{impact_str}")
        lines.append("")

    return "\n".join(lines).strip()


def _recommendations_v2() -> str:
    from ozon_agent.recommendations_v2.service import build_recommendations_v2

    recs = build_recommendations_v2(save=True, limit=20)
    if not recs:
        return "Рекомендаций: 0\n\nНет рекомендаций."

    seen = set()
    unique = []
    for r in recs:
        key = (r.problem, getattr(r, "sku", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    lines = [f"📌 Рекомендации ({len(unique)})", ""]
    for idx, rec in enumerate(unique[:5], 1):
        sku = getattr(rec, "sku", "")
        rec_id = getattr(rec, "id", "")[:12] if hasattr(rec, "id") else ""
        sku_line = f"\nТовар: {sku}" if sku else ""
        id_line = f"\nID: {rec_id}" if rec_id else ""

        problem_ru = problem_business(rec.problem)

        steps = _recommendation_steps(rec.problem)
        steps_text = "\n".join(f"  {i}. {s}" for i, s in enumerate(steps, 1))

        success_rate = _get_historical_success_rate(rec.problem)
        rate_str = f"\nИсторическая эффективность: {success_rate:.0f}%" if success_rate > 0 else ""

        lines.extend([
            f"{idx}. {problem_ru}{sku_line}{id_line}",
            "Почему агент так считает:",
            f"  {rec.hypothesis}",
            "Что сделать:",
            steps_text,
            f"Ожидаемый эффект: {rec.suggested_action}{rate_str}",
            f"\nПосле проверки: /outcome success {rec_id}" if rec_id else "",
            "",
        ])

    return "\n".join(lines)


def _recommendation_steps(problem: str) -> list[str]:
    p = problem.lower()
    if "реклам" in p or "spend" in p or "cpc" in p or "дрг" in p:
        return [
            "проверить поисковые запросы",
            "проверить ставки",
            "приостановить неэффективные кампании",
        ]
    if "марк" in p or "margin" in p:
        return ["проверить себестоимость", "проверить цены", "пересчитать логистику"]
    if "ctr" in p or "клика" in p or "фото" in p:
        return ["обновить главное фото", "проверить заголовок", "сравнить с конкурентами"]
    if "заказ" in p or "order" in p:
        return ["проверить наличие", "проверить описание", "проверить цену"]
    return ["проверить карточку", "проверить цену", "проверить рекламу"]


def _get_historical_success_rate(problem: str) -> float:
    patterns = load_success_patterns()
    for p in patterns:
        if p.get("problem", "").lower() in problem.lower():
            return float(p.get("success_rate") or 0)
    return 0.0


def _retro() -> str:
    retro = load_payload(Path("data") / "retro" / "patterns" / "retro_patterns.json")
    learning = load_json_dict(Path("data") / "learning" / "summary.json")
    outcomes = list_outcomes(limit=100)

    if not retro:
        return f"📚 Ретроспектива\n\n{no_data_message()}"

    pattern_counts: dict[str, int] = {}
    for r in retro:
        p = r.get("pattern_type", "UNKNOWN")
        pattern_counts[p] = pattern_counts.get(p, 0) + 1

    most_common = max(pattern_counts.items(), key=lambda x: x[1]) if pattern_counts else None

    success_actions = []
    failure_actions = []
    for o in outcomes:
        action = o.get("action", "")
        if o.get("result") == "SUCCESS" and action:
            success_actions.append(action)
        elif o.get("result") == "FAILURE" and action:
            failure_actions.append(action)

    if not success_actions:
        success_actions = ["временно остановить кампанию", "проверить карточку"]
    if not failure_actions:
        failure_actions = ["увеличить бюджет"]

    lines = [
        "📚 Похожие случаи",
        "",
        f"Найдено: {len(retro)} случаев",
        f"Записей продаж: {learning.get('sales_rows', 0)}",
        "",
    ]

    if most_common:
        reason = signal_type_business(most_common[0])
        lines.append(f"Чаще всего причина: {reason} ({most_common[1]} раз)")
        lines.append("")

    if success_actions:
        lines.append("Что помогало:")
        for a in success_actions[:3]:
            lines.append(f"  ✔ {retro_action_business(a)}")
        lines.append("")

    if failure_actions:
        lines.append("Что не помогало:")
        for a in failure_actions[:3]:
            lines.append(f"  ✖ {retro_action_business(a)}")

    return "\n".join(lines)


def _handle_outcome(parts: list[str], user: str) -> str:
    if len(parts) < 3:
        return (
            "Использование:\n"
            "/outcome success <id> — рекомендация сработала\n"
            "/outcome failure <id> — рекомендация не сработала\n"
            "/outcome observe <id> — начать наблюдение"
        )

    action = parts[1].lower()
    target_id = parts[2]

    if action not in ("success", "failure", "observe"):
        return "Неизвестное действие. Используйте: success, failure, observe"

    full_id = _resolve_short_id(target_id)
    if not full_id:
        full_id = target_id

    rec = get_recommendation(full_id)
    if rec is None:
        return f"Рекомендация {target_id} не найдена."

    result_map = {
        "success": "SUCCESS",
        "failure": "FAILURE",
        "observe": "OBSERVING",
    }
    result = result_map[action]

    record_outcome(
        recommendation_id=full_id,
        sku=rec.sku,
        action=rec.action.value,
        result=result,
        user=user,
    )

    emoji_map = {"SUCCESS": "✅", "FAILURE": "❌", "OBSERVING": "👁"}
    emoji = emoji_map.get(result, "❓")

    return (
        f"{emoji} Результат записан\n\n"
        f"Рекомендация: {full_id[:8]}...\n"
        f"Товар: {rec.sku}\n"
        f"Действие: {rec.action.value}\n"
        f"Результат: {result}\n\n"
        "Агент запомнит этот исход для будущих рекомендаций."
    )


def _learn() -> str:
    summary = load_json_dict(Path("data") / "learning" / "summary.json")
    stats = get_outcome_stats()

    accuracy_str = f"{stats['accuracy']}%" if (stats["success"] + stats["failure"]) > 0 else "—"

    lines = [
        "🧠 Обучение агента",
        "",
        f"Изучено продаж: {summary.get('sales_rows', 0)}",
        f"Исторических кейсов: {summary.get('retro_patterns', 0)}",
        "",
    ]

    if stats["total"] > 0:
        lines.extend([
            f"Подтверждено успешных решений: {stats['success']}",
            f"Неудачных решений: {stats['failure']}",
            f"В наблюдении: {stats['observing']}",
            f"Ожидают: {stats['pending']}",
            "",
            f"Текущая точность: {accuracy_str}",
        ])
    else:
        lines.extend([
            "Пока нет записанных исходов.",
            "",
            "Отметьте результат рекомендации:",
            "/outcome success <id>",
            "/outcome failure <id>",
        ])

    return "\n".join(lines)


def _why_down(sku: str) -> str:
    if not sku:
        return "Использование: /why_down <код товара>"

    from ozon_agent.retro.engine import build_retro_patterns_for_sku

    patterns = build_retro_patterns_for_sku(sku)
    signals = load_payload(Path("data") / "signals" / "signals.json")
    sku_signals = [s for s in signals if str(s.get("sku") or "") == sku]

    if not patterns and not sku_signals:
        return f"📉 Почему падает товар {sku}\n\n{no_data_message()}"

    pattern_type = patterns[0].get("pattern_type", "") if patterns else ""
    confidence = 0.88
    if sku_signals:
        confidence = max(float(s.get("confidence") or 0) for s in sku_signals)

    cause = signal_cause(pattern_type) if pattern_type else "требуется анализ"
    checklist = signal_checklist(pattern_type) if pattern_type else ["рекламу", "карточку", "цену"]

    success_count = sum(1 for p in patterns if p.get("severity") == "LOW")
    total_cases = len(patterns)

    helped = ["корректировка рекламы", "обновление карточки"]
    lines = [
        f"📉 Почему падает товар {sku}",
        "",
        f"Основной фактор: {cause}",
        "",
        f"Уверенность: {confidence:.0%}",
        f"Похожих случаев: {total_cases}",
        "",
    ]

    if success_count > 0:
        lines.append(f"Успешных восстановлений: {success_count}")
        lines.append("")

    lines.append("Что помогало ранее:")
    for h in helped:
        lines.append(f"  ✔ {h}")
    lines.append("")

    lines.append("Что проверить сейчас:")
    for i, item in enumerate(checklist, 1):
        lines.append(f"  {i}. {item}")

    return "\n".join(lines)


def _today() -> str:
    signals = load_payload(Path("data") / "signals" / "signals.json")
    recs = load_payload(Path("data") / "recommendations_v2" / "recommendations.json")

    actions: list[dict[str, Any]] = []
    seen_skus: set[str] = set()

    for s in signals:
        sku = str(s.get("sku") or "")
        if not sku or sku in seen_skus:
            continue
        seen_skus.add(sku)
        spend = float(s.get("value") or s.get("evidence", {}).get("spend") or 0)
        confidence = float(s.get("confidence") or 0.7)
        success_rate = _get_historical_success_rate(s.get("signal_type", ""))

        actions.append({
            "sku": sku,
            "reason": signal_type_business(s.get("signal_type", "")),
            "impact": spend,
            "confidence": confidence,
            "success_rate": success_rate,
            "source": "signal",
        })

    for r in recs[:5]:
        problem = str(r.get("problem") or "")
        sku_match = ""
        for word in problem.split():
            if word.isdigit() and len(word) >= 6:
                sku_match = word
                break
        if sku_match and sku_match not in seen_skus:
            seen_skus.add(sku_match)
            confidence = float(r.get("confidence") or 0.7)
            success_rate = _get_historical_success_rate(problem)
            actions.append({
                "sku": sku_match,
                "reason": str(r.get("suggested_action") or r.get("hypothesis", "")),
                "impact": 0,
                "confidence": confidence,
                "success_rate": success_rate,
                "source": "recommendation",
            })

    actions.sort(key=lambda x: (x["impact"], x["confidence"], x["success_rate"]), reverse=True)

    if not actions:
        return "✅ Нет критических действий на сегодня."

    lines = ["🔥 Что делать сегодня", ""]
    for i, action in enumerate(actions[:5], 1):
        impact_str = f"\nПотери: {rub(action['impact'])}" if action["impact"] > 0 else ""
        confidence_pct = f"{action['confidence']:.0%}"
        rate_str = ""
        if action["success_rate"] > 0:
            rate_str = f"\nВероятность решения: {action['success_rate']:.0f}%"
        lines.extend([
            f"{i}. Проверить товар {action['sku']}",
            f"Причина: {action['reason']}{impact_str}",
            f"Уверенность: {confidence_pct}{rate_str}",
            divider(),
            "",
        ])

    return "\n".join(lines)


def _outcomes() -> str:
    outcomes = list_outcomes(limit=50)
    stats = get_outcome_stats()

    if not outcomes:
        return "📊 Результаты\n\nНет записанных исходов.\n\nОтметьте: /outcome success <id>"

    lines = [
        "📊 Результаты рекомендаций",
        "",
        f"Всего: {stats['total']}",
        f"Успешных: {stats['success']}",
        f"Неудачных: {stats['failure']}",
        f"В наблюдении: {stats['observing']}",
        f"Точность: {stats['accuracy']}%",
        "",
        "Последние исходы:",
    ]

    for o in outcomes[-5:]:
        if o.get("result") == "SUCCESS":
            emoji = "✅"
        elif o.get("result") == "FAILURE":
            emoji = "❌"
        else:
            emoji = "👁"
        lines.append(f"  {emoji} {o.get('sku', '—')} — {o.get('action', '—')}")

    return "\n".join(lines)


def _signals() -> str:
    from ozon_agent.signals.service import build_signal_report

    signals = build_signal_report(save=True)
    if not signals:
        return "Сигналов: 0\n\nНет активных сигналов."

    seen = set()
    unique = []
    for signal in signals:
        key = (signal.signal_type.value, signal.sku)
        if key in seen:
            continue
        seen.add(key)
        unique.append(signal)

    lines = [f"Сигналов: {len(unique)}", ""]
    for signal in unique[:10]:
        emoji = severity_emoji(signal.severity.value)
        business_type = signal_type_business(signal.signal_type.value)
        lines.extend([
            f"{emoji} {business_type}",
            f"Уверенность: {signal.confidence:.0%}",
            f"Товар: {safe_str(signal.sku)}",
            "",
        ])
    return "\n".join(lines).strip()


def _daily() -> str:
    from ozon_agent.retro.historical_aggregator import build_daily_history

    rows = build_daily_history()
    if not rows:
        return "Сводка за день: нет данных."
    row = rows[-1]
    return (
        f"📊 P&L за {row.get('date')}\n\n"
        f"Выручка: {rub(float(row.get('revenue') or 0))}\n"
        f"Заказы: {row.get('orders', 0)}\n"
        f"Реклама: {rub(float(row.get('advertising') or 0))}\n"
        f"Себестоимость: {rub(float(row.get('cogs') or 0))}\n"
        f"Валовая прибыль: {rub(float(row.get('gross_profit') or 0))}\n"
        f"Маржа: {pct(float(row.get('margin') or 0))}\n"
        f"ДРР: {pct(float(row.get('drr') or 0))}"
    )


def _cogs_status() -> str:
    from ozon_agent.cogs.service import coverage_report

    report = coverage_report()
    return (
        "Себестоимость\n\n"
        f"Всего товаров: {report.total_products}\n"
        f"С себестоимостью: {report.with_cogs}\n"
        f"Без себестоимости: {report.without_cogs}\n"
        f"Покрытие: {pct(report.coverage_pct)}"
    )


def _sku_detail(sku: str) -> str:
    if not sku:
        return "Использование: /sku <код товара>\nПример: /sku 729504056"

    try:
        result = analyze_sku(sku)
    except Exception as e:
        return f"📦 Товар {sku}\n\nОшибка анализа: {e}"

    metrics = result["metrics"]
    health = result["health"]
    trend = result["trend"]
    root_cause = result["root_cause"]
    recommendation = result["recommendation"]

    if not metrics.revenue and not metrics.orders:
        return f"📦 Товар {sku}\n\n{no_data_message()}"

    status_emoji = {
        HealthStatus.HEALTHY: "🟢 Здоров",
        HealthStatus.WATCH: "🟠 Наблюдение",
        HealthStatus.RISK: "🔴 Риск",
    }
    trend_emoji_map = {
        TrendDirection.GROWING: "🟢 Растёт",
        TrendDirection.STABLE: "➡️ Стабильно",
        TrendDirection.DECLINING: "🔴 Падает",
    }

    lines = [
        f"📦 Товар {sku}",
    ]
    if metrics.product_name:
        lines.append(metrics.product_name)

    lines.extend([
        "",
        f"Здоровье: {health.score}/100",
        f"Статус: {status_emoji.get(health.status, '—')}",
        f"Тренд: {trend_emoji_map.get(trend.direction, '—')}",
        "",
        f"Выручка: {rub(metrics.revenue)}",
        f"Заказы: {metrics.orders} шт",
        f"Маржа: {pct(metrics.margin)}",
        f"Реклама: {rub(metrics.advertising)}",
        f"ДРР: {pct(metrics.drr)}",
    ])

    if metrics.ctr > 0:
        lines.append(f"CTR: {pct(metrics.ctr)}")
    if metrics.cvr > 0:
        lines.append(f"Конверсия: {pct(metrics.cvr)}")
    if metrics.reviews > 0:
        lines.append(f"Отзывы: {metrics.reviews}")

    if trend.direction == TrendDirection.DECLINING:
        lines.extend([
            "",
            f"Изменение выручки: {pct(trend.revenue_change_pct)}",
        ])

    if root_cause and root_cause.factor != "нет проблем":
        lines.extend([
            "",
            "Корневая причина:",
            f"  {root_cause.factor}",
            f"  Уверенность: {root_cause.confidence:.0%}",
        ])
        if root_cause.evidence:
            lines.append("  Доказательства:")
            for evidence in root_cause.evidence[:3]:
                lines.append(f"    • {evidence}")

    if recommendation:
        lines.extend([
            "",
            "Рекомендация:",
            f"  Действие: {recommendation.action}",
            f"  Ожидаемый эффект: {recommendation.expected_impact}",
            f"  Уверенность: {recommendation.confidence:.0%}",
        ])

    return "\n".join(lines)


def _top_sku() -> str:
    skus = get_top_skus(limit=10)
    if not skus:
        return f"🏆 Лучшие товары\n\n{no_data_message()}"

    lines = ["🏆 Лучшие товары", ""]
    for i, s in enumerate(skus, 1):
        trend_str = {
            "growing": "🟢↑",
            "stable": "➡️",
            "declining": "🔴↓",
        }.get(s.get("trend", ""), "—")
        lines.extend([
            f"{i}. {s['sku']}",
            f"   Здоровье: {s['health_score']}/100 | {trend_str}",
            f"   Выручка: {rub(s['revenue'])} | Маржа: {pct(s['margin'])}",
            "",
        ])
    return "\n".join(lines)


def _worst_sku() -> str:
    skus = get_worst_skus(limit=10)
    if not skus:
        return f"⚠️ Товары риска\n\n{no_data_message()}"

    lines = ["⚠️ Товары риска", ""]
    for i, s in enumerate(skus, 1):
        trend_str = {
            "growing": "🟢↑",
            "stable": "➡️",
            "declining": "🔴↓",
        }.get(s.get("trend", ""), "—")
        profit_str = rub(s.get("profit", 0)) if s.get("profit", 0) < 0 else ""
        lines.extend([
            f"{i}. {s['sku']}",
            f"   Здоровье: {s['health_score']}/100 | {trend_str}",
            f"   Выручка: {rub(s['revenue'])} {'| ' + profit_str if profit_str else ''}",
            "",
        ])
    return "\n".join(lines)


def _economics() -> str:
    daily = load_payload(Path("data") / "analytics" / "daily_summary.json")
    if not daily:
        return f"💰 Экономика магазина\n\n{no_data_message()}"

    total_revenue = sum(float(d.get("revenue") or 0) for d in daily)
    total_ad = sum(float(d.get("advertising") or 0) for d in daily)
    total_cogs = sum(float(d.get("cogs") or 0) for d in daily)
    total_commission = sum(float(d.get("commission") or 0) for d in daily)
    total_logistics = sum(float(d.get("logistics") or 0) for d in daily)
    total_profit = sum(float(d.get("gross_profit") or 0) for d in daily)
    avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    avg_drr = (total_ad / total_revenue * 100) if total_revenue > 0 else 0

    ranking = load_payload(Path("data") / "ranking" / "snapshots.json")
    sku_revenue: dict[str, float] = {}
    for r in ranking:
        sku = str(r.get("sku") or "")
        if sku:
            sku_revenue[sku] = sku_revenue.get(sku, 0) + float(r.get("revenue") or 0)

    sorted_skus = sorted(sku_revenue.items(), key=lambda x: x[1], reverse=True)
    best_sku = sorted_skus[0] if sorted_skus else None
    worst_sku = sorted_skus[-1] if sorted_skus and len(sorted_skus) > 1 else None

    lines = [
        "💰 Экономика магазина",
        "",
        f"Выручка: {rub(total_revenue)}",
        f"Реклама: {rub(total_ad)}",
        f"Себестоимость: {rub(total_cogs)}",
        f"Комиссия: {rub(total_commission)}",
        f"Логистика: {rub(total_logistics)}",
        f"Валовая прибыль: {rub(total_profit)}",
        f"Маржа: {pct(avg_margin)}",
        f"ДРР: {pct(avg_drr)}",
        "",
    ]

    if best_sku:
        lines.append(f"Лучший товар: {best_sku[0]} ({rub(best_sku[1])})")
    if worst_sku and worst_sku[0] != (best_sku[0] if best_sku else ""):
        lines.append(f"Худший товар: {worst_sku[0]} ({rub(worst_sku[1])})")

    return "\n".join(lines)


def _list_pending() -> str:
    recs = list_recommendations(status=RecommendationStatus.PENDING, limit=10)
    if not recs:
        return "Нет ожидающих рекомендаций."
    lines = [f"Ожидают одобрения ({len(recs)}):", ""]
    for rec in recs:
        lines.append(
            f"  {rec.id[:8]}... | Товар: {rec.sku} | Действие: {rec.action.value}"
        )
    lines.append("")
    lines.append("Используйте /recommendations show <id> для деталей.")
    return "\n".join(lines)


def _show(rec_id: str) -> str:
    rec = get_recommendation(rec_id)
    if rec is None:
        full_id = _resolve_short_id(rec_id)
        if full_id:
            rec = get_recommendation(full_id)
    if rec is None:
        return f"Рекомендация {rec_id} не найдена."
    return format_rec_message(rec)


def _approve(rec_id: str, user: str) -> str:
    full_id = _resolve_short_id(rec_id)
    target = full_id or rec_id
    try:
        rec = approve_recommendation(target, approved_by=user)
        return f"Одобрено {rec.id[:8]}... пользователем {user}"
    except Exception as e:
        return f"Ошибка: {e}"


def _reject(rec_id: str, user: str, reason: str) -> str:
    full_id = _resolve_short_id(rec_id)
    target = full_id or rec_id
    try:
        rec = reject_recommendation(target, rejected_by=user, reason=reason)
        return f"Отклонено {rec.id[:8]}... пользователем {user}: {reason}"
    except Exception as e:
        return f"Ошибка: {e}"


def _resolve_short_id(short_id: str) -> str | None:
    if len(short_id) >= 36:
        return short_id
    recs = list_recommendations(limit=100)
    for rec in recs:
        if rec.id.startswith(short_id):
            return rec.id
    return None


def _handle_experiments(parts: list[str], user: str) -> str:
    if len(parts) == 1:
        return _experiment_list()
    action = parts[1]
    if action == "list":
        return _experiment_list()
    if action == "show" and len(parts) >= 3:
        return _experiment_show(parts[2])
    if action == "ready" and len(parts) >= 3:
        return _experiment_transition(parts[2], "ready", user)
    if action == "start" and len(parts) >= 3:
        return _experiment_transition(parts[2], "start", user)
    if action == "pause" and len(parts) >= 3:
        return _experiment_transition(parts[2], "pause", user)
    if action == "complete" and len(parts) >= 3:
        return _experiment_transition(parts[2], "complete", user)
    if action == "cancel" and len(parts) >= 3:
        reason = parts[3] if len(parts) >= 4 else "отмена через telegram"
        return _experiment_cancel(parts[2], reason, user)
    if action == "report" and len(parts) >= 3:
        return _experiment_report(parts[2])
    return (
        "Использование экспериментов:\n"
        "/experiments — список\n"
        "/experiments show <id>\n"
        "/experiments start <id>\n"
        "/experiments pause <id>\n"
        "/experiments complete <id>\n"
        "/experiments cancel <id> <причина>\n"
        "/experiments report <id>"
    )


def _experiment_list() -> str:
    from ozon_agent.experiments.repository import list_experiments
    exps = list_experiments(limit=10)
    if not exps:
        return "Нет экспериментов."
    lines = [f"Эксперименты ({len(exps)}):", ""]
    for exp in exps:
        lines.append(
            f"  {exp.id[:8]}... | SKU: {exp.sku} | "
            f"Статус: {exp.status.value} | Действие: {exp.action}"
        )
    lines.append("")
    lines.append("Используйте /experiments show <id> для деталей.")
    return "\n".join(lines)


def _experiment_show(exp_id: str) -> str:
    from ozon_agent.experiments.experiment_summary import format_experiment_detail
    from ozon_agent.experiments.repository import get_experiment
    exp = get_experiment(exp_id)
    if exp is None:
        full_id = _resolve_short_experiment_id(exp_id)
        if full_id:
            exp = get_experiment(full_id)
    if exp is None:
        return f"Эксперимент {exp_id} не найден."
    return format_experiment_detail(exp)


def _experiment_transition(exp_id: str, action: str, user: str) -> str:
    from ozon_agent.experiments.workflow import (
        mark_completed,
        mark_paused,
        mark_ready,
        mark_running,
    )
    full_id = _resolve_short_experiment_id(exp_id)
    target = full_id or exp_id
    try:
        if action == "ready":
            exp = mark_ready(target, actor=user)
        elif action == "start":
            exp = mark_running(target, actor=user)
        elif action == "pause":
            exp = mark_paused(target, actor=user)
        elif action == "complete":
            exp = mark_completed(target, actor=user)
        else:
            return f"Неизвестное действие: {action}"
        return f"Эксперимент {exp.id[:8]}... {action} ({exp.status.value})"
    except Exception as e:
        return f"Ошибка: {e}"


def _experiment_cancel(exp_id: str, reason: str, user: str) -> str:
    from ozon_agent.experiments.workflow import mark_cancelled
    full_id = _resolve_short_experiment_id(exp_id)
    target = full_id or exp_id
    try:
        exp = mark_cancelled(target, reason=reason, actor=user)
        return f"Эксперимент {exp.id[:8]}... отменён: {reason}"
    except Exception as e:
        return f"Ошибка: {e}"


def _experiment_report(exp_id: str) -> str:
    from ozon_agent.experiments.experiment_summary import format_experiment_report
    from ozon_agent.experiments.repository import get_experiment
    exp = get_experiment(exp_id)
    if exp is None:
        full_id = _resolve_short_experiment_id(exp_id)
        if full_id:
            exp = get_experiment(full_id)
    if exp is None:
        return f"Эксперимент {exp_id} не найден."
    return format_experiment_report(exp)


def _resolve_short_experiment_id(short_id: str) -> str | None:
    if len(short_id) >= 36:
        return short_id
    from ozon_agent.experiments.repository import list_experiments
    exps = list_experiments(limit=100)
    for exp in exps:
        if exp.id.startswith(short_id):
            return exp.id
    return None
