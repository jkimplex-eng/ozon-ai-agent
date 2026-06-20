# Ozon Algorithm Hypotheses Framework

## Disclaimer

This document describes **working hypotheses** about how Ozon marketplace algorithms may operate, based on observable data patterns, public seller documentation, and empirical testing by the agent. It is NOT a confirmed description of Ozon's internal algorithms. Ozon does not publish algorithmic details.

All recommendations in this framework are **legitimate business actions**. No grey-hat, black-hat, or manipulative methods are included.

---

## 1. Search / SEO

### Hypothesis

Ozon search ranking is a multi-factor system that weighs relevance, engagement signals, and commercial performance. The algorithm appears to optimize for conversion probability and marketplace revenue.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Query relevance | title matches query | products.name | Keyword presence in title | Add relevant keywords to title (naturally) | Search position improvement in 7-14 days |
| Description match | description keywords | products.description | Keyword density | Enrich description with search terms | CTR improvement |
| Attribute completeness | filled attributes % | products.attributes | Attribute count vs max | Fill all available attributes | Search visibility increase |
| CTR by query | clicks / impressions | search_positions | CTR < 1% | Improve title/images for that query | CTR increase in 7 days |
| CR by query | orders / clicks | search_positions + orders | CR < 1% | Improve price/reviews/delivery | Order increase |
| Sales velocity by query | orders per day | sales + search_positions | Declining sales | Check price competitiveness | Sales recovery |
| Price vs competitors | price / avg_market_price | products + competitors | Price > market avg +15% | Reduce price or justify with value | Conversion improvement |
| Reviews count | total_reviews | reviews | < 10 reviews | Encourage organic reviews | Ranking improvement |
| Rating | avg_rating | review_stats | < 4.0 | Address quality issues | Ranking improvement |
| Stock availability | stock_total > 0 | stocks | stock = 0 | Restock immediately | Search visibility恢复 |

### Decision Engine Integration

```python
# From opportunity_detector.py
detect_ranking_opportunities(features):
    RANKING_RISK: ranking_trend > 0 (worsening) AND good CTR
    RANKING_GROWTH: high conversion + weak rank position
```

---

## 2. Ads Ranking (Performance API)

### Hypothesis

Ozon Ads ranking uses a modified GSP (Generalized Second Price) auction with quality score factors. Higher relevance and conversion probability lead to lower CPC at the same bid.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Impressions | impressions | performance_stats | Low impressions | Increase bid or improve targeting | Impressions increase |
| Clicks | clicks | performance_stats | Low clicks | Improve ad creative/title | Click increase |
| CTR | clicks / impressions | performance_stats | CTR < 1% | Improve product card | CTR increase |
| CPC | spend / clicks | performance_stats | CPC > target | Optimize bid or improve quality | CPC reduction |
| Spend | SUM(spend) | performance_stats | Spend > budget | Review bid strategy | Budget efficiency |
| Orders from ads | orders | performance_stats | 0 orders from ads | Check landing page/price | Order generation |
| Revenue from ads | revenue | performance_stats | Revenue < spend | Pause or decrease budget | ROAS improvement |
| DRR | spend / revenue * 100 | performance_stats | DRR > 30% | Optimize or pause campaign | DRR reduction |
| ROAS | revenue / spend | performance_stats | ROAS < 2.0 | Review campaign efficiency | ROAS improvement |
| SKU in campaign | campaign_id mapping | performance_campaigns | SKU missing from campaigns | Add SKU to relevant campaigns | Coverage expansion |

### Decision Engine Integration

```python
# From opportunity_detector.py
detect_ad_opportunities(features):
    AD_GROWTH: ROAS >= 4.0 AND DRR <= 20% (scale opportunity)
    AD_WASTE: ROAS <= 1.5 AND DRR >= 35% (reduce/pause)
```

---

## 3. Product Ranking (Organic)

### Hypothesis

Ozon organic ranking is heavily influenced by sales velocity, conversion rate, and fulfillment quality. The algorithm rewards products that convert well and deliver on time.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Sales velocity | orders per day | sales | Declining trend | Review price/ads/content | Sales recovery |
| Sales acceleration | sales_trend_pct | sales | Negative trend | Investigate root cause | Trend reversal |
| Price competitiveness | price / market_avg | products + competitors | Price above market | Competitive pricing | Conversion improvement |
| Stock levels | stock_total | stocks | Low stock (< 7 days) | Restock to avoid OOS | Maintain ranking |
| Delivery time | delivery_days_avg | logistics | > 3 days | Optimize warehouse/FBO | Ranking boost |
| Review quality | avg_rating | review_stats | < 4.0 stars | Address product issues | Ranking improvement |
| Review volume | total_reviews | review_stats | < 20 reviews | Encourage organic reviews | Social proof boost |
| Return rate | returns / orders | orders | > 10% | Investigate quality/mismatch | Ranking protection |
| Content quality | images_count, description_length | products | Low content score | Enhance product card | Conversion improvement |

### Decision Engine Integration

```python
# From opportunity_detector.py
detect_price_opportunities(features):
    PRICE_MARGIN: high margin + stable sales (maintain price)
    PRICE_CONVERSION: declining sales despite good margin (reduce price)
```

---

## 4. Conversion Optimization

### Hypothesis

Ozon conversion is driven by the complete product card experience: price, images, description, reviews, delivery speed, and stock availability. The conversion funnel is: Impression → Click → Add to Cart → Order.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Impression → Click (CTR) | clicks / impressions | advertising + search_positions | CTR < 2% | Improve title, main image, price display | CTR increase |
| Click → Cart (ATC rate) | add_to_cart / clicks | performance_stats | ATC < 20% | Improve description, reviews, delivery info | ATC increase |
| Cart → Order (checkout rate) | orders / add_to_cart | performance_stats | Checkout < 50% | Review pricing, shipping options | Order increase |
| Price perception | price vs perceived value | products + competitors | Price > value perception | Adjust price or enhance value proposition | Conversion improvement |
| Social proof | avg_rating * log(reviews) | review_stats | Low social proof score | Build review volume organically | Conversion improvement |
| Image quality | images_count | products | < 3 images | Add more product images | CTR and conversion improvement |
| Description completeness | description_length | products | < 200 chars | Enrich description | Conversion improvement |
| Stock availability | stock_total > 0 | stocks | stock = 0 | Restock | Conversion恢复 |
| Delivery speed | delivery_days_avg | logistics | > 3 days | Switch to FBO or closer warehouse | Conversion improvement |

### Funnel Metrics

```
Impressions (from ads/search)
    ↓ CTR
Clicks (from ads/search)
    ↓ ATC Rate
Add to Cart
    ↓ Checkout Rate
Orders
    ↓ Fulfillment
Delivered Orders
```

---

## 5. Economics

### Hypothesis

Ozon marketplace economics follow a predictable structure: Revenue → Commission → Logistics → Advertising → COGS = Gross Profit. Understanding this chain enables margin optimization.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Revenue | SUM(final_price) | postings | Declining | Review sales strategy | Revenue recovery |
| Commission rate | commission / revenue | finance | > 25% | Negotiate or adjust pricing structure | Margin improvement |
| Logistics cost | logistics / revenue | finance | > 15% | Optimize packaging, weight, warehouse | Cost reduction |
| Advertising cost | spend / revenue | advertising | DRR > 25% | Optimize campaigns or pause waste | DRR reduction |
| COGS | unit_cost * quantity | cogs + sales | COGS > 50% of revenue | Negotiate supplier prices or optimize | Margin improvement |
| Gross Profit | revenue - all_costs | calculated | GP < 0 | Urgent: review all cost components | Profitability restoration |
| Margin | GP / revenue * 100 | calculated | Margin < 15% | Cost optimization required | Margin improvement |
| Break-even point | fixed_costs / (price - variable_cost) | calculated | Selling below break-even | Increase price or reduce costs | Profitability |

### Decision Engine Integration

```python
# From confidence_engine.py and risk_engine.py
score_confidence():
    - High data freshness → higher confidence
    - Large sample size → higher confidence
    - Missing COGS → lower confidence

score_risk():
    - Negative gross profit → higher risk
    - High DRR → higher risk
    - No forecast → higher risk
```

---

## 6. Stock / Availability

### Hypothesis

Stock availability is critical for both organic ranking and ad performance. Out-of-stock events cause ranking drops that take 2-4 weeks to recover. The algorithm penalizes inconsistent availability.

### Factor Table

| Factor | Metric | Data Source | Signal | User-facing Recommendation | Outcome Check |
|--------|--------|-------------|--------|---------------------------|---------------|
| Current stock | stock_total | stocks | stock < 5 | Restock immediately | Stock replenishment |
| Stock days | stock / avg_daily_sales | stocks + sales | < 7 days | Plan replenishment | Stock coverage |
| Out-of-stock risk | stock / avg_daily_sales | stocks + sales | < 3 days | Emergency restock | OOS prevention |
| FBO availability | stock_fbo | stocks | FBO = 0 | Transfer to FBO warehouse | FBO stock availability |
| FBS availability | stock_fbs | stocks | FBS = 0 | Ensure FBS stock | FBS stock availability |
| In-transit stock | in_transit | stocks | in_transit > 0 | Monitor delivery timeline | Stock arrival |
| Reserved stock | reserved | stocks | reserved > stock | Review reservation policy | Stock allocation |
| Stockout history | days_since_last_stockout | stocks | Recent stockout | Increase safety stock | Availability improvement |

### Decision Engine Integration

```python
# From opportunity_detector.py
detect_stock_opportunities(features):
    STOCK_RISK: stockout_probability >= 0.6 OR stock_days <= 7
```

---

## 7. Learning Loop

### Hypothesis

The agent learns from each action's outcome to improve future recommendations. The learning loop follows: Signal → Recommendation → Action → Observation → Learning.

### Learning Loop Table

| Stage | Component | Data | Timing | Output |
|-------|-----------|------|--------|--------|
| **Signal** | Opportunity detector | DecisionFeature | Real-time | Opportunity object |
| **Recommendation** | Recommendation engine | Opportunity + context | Real-time | Recommendation with confidence |
| **Approval** | Approval workflow | Recommendation | Human input | Approved/rejected decision |
| **Action** | Execution (future) | Approved recommendation | On approval | Ozon API call (price/bid/stock change) |
| **Baseline** | Pre-action metrics | sales, revenue, DRR, stock | At action time | Baseline snapshot |
| **Observation** | Post-action metrics | sales, revenue, DRR, stock | 3/7/14 days | Current snapshot |
| **Evaluation** | Outcome tracker | Baseline vs current | After observation window | Success score, direction accuracy |
| **Learning** | Confidence calibration | Historical outcomes | Batch | Updated confidence factors |

### Outcome Evaluation Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| Success score | (actual_delta - expected_delta) / expected_delta | > 0.5 |
| Direction accuracy | correct_direction / total_directions | > 0.6 |
| Revenue impact | (current_revenue - baseline_revenue) / baseline_revenue | > 0% |
| Margin impact | current_margin - baseline_margin | > 0 p.p. |
| DRR impact | baseline_drr - current_drr | > 0 p.p. (lower is better) |

### Confidence Calibration

The agent adjusts confidence based on historical performance by action type and SKU:

```python
calibration_factor = historical_success_rate_for_action / overall_success_rate

if calibration_factor > 1.0:
    # Agent is overconfident for this action → reduce confidence
    adjusted_confidence = base_confidence * calibration_factor
elif calibration_factor < 1.0:
    # Agent is underconfident for this action → increase confidence
    adjusted_confidence = base_confidence * calibration_factor
```

### Experiment Tracking

Experiments validate hypotheses before full rollout:

```
Hypothesis → Experiment (DRAFT → READY → RUNNING)
    ↓
Baseline measurement (7-14 days)
    ↓
Action applied (single SKU or small group)
    ↓
Current measurement (7-14 days)
    ↓
Evaluation: success_score, direction_accuracy
    ↓
Decision: scale / iterate / kill
```

---

## Cross-Reference: Agent Modules → Algorithm Factors

| Agent Module | Algorithm Domain | Key Factors |
|-------------|-----------------|-------------|
| `decision/opportunity_detector.py` | Search + Ads + Ranking + Stock | Ranking trend, ROAS, DRR, stock days |
| `decision/confidence_engine.py` | All domains | Data freshness, sample size, forecast availability |
| `decision/risk_engine.py` | Economics + Ads | Gross profit, DRR, stockout, ranking deterioration |
| `knowledge/rules.py` | Search + Ads | CTR thresholds, conversion rates, ranking drops |
| `forecast/` | All domains | Sales velocity, demand prediction, stock forecasting |
| `analytics/metrics.py` | Economics | Revenue, margin, DRR, gross profit |
| `learning/` | Learning Loop | Outcome tracking, confidence calibration, backtesting |
| `experiments/` | Experiment Tracking | Hypothesis validation, A/B testing |

---

## Data Sources Summary

| Source | API | Frequency | Data |
|--------|-----|-----------|------|
| Products | Seller API /v2/product/list | Daily | SKU, price, attributes |
| Stocks | Seller API /v4/product/info/stocks | Daily | Stock levels by warehouse |
| Orders | Seller API /v3/posting/fbo\|fbs/list | Daily | Orders, quantities, prices |
| Finance | Seller API /v3/finance/transaction/list | Daily | Commission, logistics, services |
| Advertising | Performance API /statistics | Daily | Impressions, clicks, spend, orders |
| Campaigns | Performance API /campaign | Weekly | Campaign metadata |
| Reviews | Seller API /v1/review/list | Daily | Ratings, text |
| Search positions | Agent tracking | Weekly | Position by query |

---

## Limitations

1. **No confirmed algorithm details** — all hypotheses based on observable patterns
2. **Algorithm changes** — Ozon updates algorithms periodically; hypotheses may become outdated
3. **Regional differences** — algorithms may vary by marketplace region
4. **Category differences** — ranking factors may differ by product category
5. **Time sensitivity** — some factors (sales velocity) are time-window dependent
6. **Data lag** — some metrics have 1-3 day reporting delay
