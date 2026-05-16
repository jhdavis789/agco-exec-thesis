# CIM Extraction Schema

Canonical fields every CIM extraction must attempt. Each field is owned by one of the seven extractor sub-agents (see `audit-protocol.md`).

Every field is an object: `{value, quote, page, source_type, confidence}` — see `audit-protocol.md` for the contract. `not_found` is a valid `source_type` and is required when the CIM doesn't answer the field (silent absence is forbidden).

The machine-readable JSON Schema lives in `../templates/extraction.schema.json`. This file is the human-readable index.

## 1. `company_and_transaction` (Agent 1)

| Field | Type | Notes |
|---|---|---|
| `target.legal_name` | string | Exact legal entity name |
| `target.dba` | string\|null | DBA if different |
| `target.hq_city_state` | string | Headquarters |
| `target.founded_year` | int | |
| `target.ownership` | enum | founder / family / sponsor / public / corporate-carveout |
| `target.current_owners` | string[] | List with % if disclosed |
| `transaction.advisor` | string | Sell-side banker |
| `transaction.process_type` | enum | broad-auction / targeted / proprietary / continuation |
| `transaction.process_timeline.iol_due` | date\|null | Indication of interest |
| `transaction.process_timeline.lol_due` | date\|null | Letter of intent / next round |
| `transaction.process_timeline.expected_close` | date\|null | |
| `transaction.asking_range` | string\|null | Range or single number, raw quote |
| `transaction.proposed_structure` | enum | 100% sale / recap / minority / cv / other |
| `transaction.rollover_expectation` | string\|null | % equity sellers will roll |
| `transaction.management_rollover` | string\|null | Management's stake post-close |

## 2. `business_model` (Agent 2)

| Field | Type | Notes |
|---|---|---|
| `business.description_one_sentence` | string | Verbatim or near-verbatim from CIM exec summary |
| `business.products_services` | string[] | Top-level offering list |
| `business.revenue_model` | enum[] | subscription / transactional / project / license / hardware / consumable / hybrid |
| `business.recurring_revenue_pct` | number | 0–100. Distinguish contractually-recurring from re-occurring |
| `business.recurring_definition` | string | The CIM's own definition of "recurring" — capture verbatim |
| `business.avg_contract_length_months` | number\|null | |
| `business.pricing_model` | string | e.g. "per-seat", "%-of-spend", "per-unit", "flat fee" |
| `business.customer_segments` | string[] | E.g. enterprise / SMB / govt / consumer |
| `business.gtm_channels` | string[] | E.g. direct sales / channel / digital / inside |
| `business.geography_pct.us` | number | |
| `business.geography_pct.international` | number | Break down if material |
| `business.seasonality` | string\|null | Quarterly skew description |
| `business.unit_economics` | object\|null | CAC, LTV, payback, gross margin per unit/seat if disclosed |

## 3. `financials` (Agent 3) — the most fact-dense section

For each year `Y ∈ {Y-3, Y-2, Y-1, LTM, FY+1E, FY+2E, FY+3E}` (at minimum 3 historical + 1 projection):

| Field | Type | Notes |
|---|---|---|
| `financials.revenue.<Y>` | number | $ in actual units; record CIM's stated units in `quote` |
| `financials.gross_profit.<Y>` | number\|null | |
| `financials.gross_margin_pct.<Y>` | number\|null | |
| `financials.ebitda.<Y>` | number | Capture **whether** it's "Adjusted EBITDA" — the word "Adjusted" must be in the quote |
| `financials.ebitda_adjustments.<Y>` | object[]\|null | Each addback: `{type, amount, justification_quote}` |
| `financials.ebitda_margin_pct.<Y>` | number | |
| `financials.capex.<Y>` | number\|null | |
| `financials.fcf.<Y>` | number\|null | Unlevered or levered — note which |
| `financials.working_capital.<Y>` | number\|null | |
| `financials.debt.<Y>` | number\|null | |
| `financials.cash.<Y>` | number\|null | |
| `financials.fiscal_year_end` | string | e.g. "December 31" — required to interpret all years |

Also:

| Field | Type | Notes |
|---|---|---|
| `financials.revenue_bridge.<Y>.components` | object[] | Volume / price / mix / new logos / churn — when CIM provides |
| `financials.kpis` | object | Sector-specific (e.g. ARR, NRR, gross retention, units shipped, contracted backlog) |
| `financials.projection_assumptions` | string[] | Each major driver as a quote |
| `financials.projection_credibility_signals` | string[] | E.g. backlog coverage, contracted revenue, signed LOIs |

## 4. `market_and_competition` (Agent 4)

| Field | Type | Notes |
|---|---|---|
| `market.tam_usd` | number\|null | Capture year of TAM source |
| `market.tam_source` | string | Banker estimate vs. third-party — capture which |
| `market.sam_usd` | number\|null | |
| `market.growth_rate_cagr_pct` | number | Forward CAGR |
| `market.growth_horizon` | string | e.g. "2024–2029" |
| `market.target_share_pct` | number\|null | |
| `market.top_competitors` | object[] | `{name, revenue_or_share, positioning_quote}` |
| `market.competitive_themes` | string[] | What banker claims as differentiation |
| `market.disruption_risks` | string[] | Any disruptions the CIM acknowledges |

## 5. `customers_and_concentration` (Agent 5)

| Field | Type | Notes |
|---|---|---|
| `customers.top10` | object[] | Each: `{name_or_label, pct_revenue, tenure_years, contract_type, contract_remaining}` |
| `customers.top1_pct` | number | Must equal top10[0].pct |
| `customers.top10_total_pct` | number | Sum check vs. Pass 4 deterministic |
| `customers.churn.gross_pct` | number\|null | |
| `customers.churn.net_pct` | number\|null | (NRR if applicable) |
| `customers.avg_tenure_years` | number\|null | |
| `customers.contract_renewal_rate` | number\|null | |
| `customers.named_anchors` | string[] | Marquee logos disclosed |
| `customers.customer_acquisition_costs` | number\|null | If disclosed |

## 6. `management_and_employees` (Agent 6)

| Field | Type | Notes |
|---|---|---|
| `management.key_execs` | object[] | `{name, title, tenure_years, prior_roles, equity_rollover_signal}` |
| `management.ceo_will_stay` | enum | confirmed / likely / unclear / departing |
| `management.equity_rollover` | string | Aggregate management roll expectation |
| `employees.total_fte` | int | |
| `employees.attrition_pct` | number\|null | |
| `employees.union_status` | string\|null | |
| `employees.geography_concentration` | string | Where the FTE base sits |
| `employees.key_dependencies` | string[] | Single points of failure |

## 7. `risks_and_legal` (Agent 7)

| Field | Type | Notes |
|---|---|---|
| `risks.litigation` | object[] | Each material case: `{description, status, exposure}` |
| `risks.regulatory` | string[] | Regulatory exposures (FDA, FAR, etc.) |
| `risks.customer_concentration` | string | Restated risk language |
| `risks.supplier_concentration` | string\|null | |
| `risks.ip_status` | string | Patents, trademarks, contested IP |
| `risks.cyber_incidents` | object[] | Disclosed incidents |
| `risks.environmental` | string[] | Phase 1/2/contamination notes |
| `risks.kpi_deltas` | string[] | Any KPI that has materially deteriorated — Falfurrias cares about negative trends |

## Output file layout

After all 7 extractors return, the main session merges into `cims/<TargetCompany>_workup/extraction.json`. The auditor reads from there.

## Quote rules (read again)

- Quotes must be **verbatim**. Allow whitespace normalization. No paraphrasing.
- If the quote is long (>40 words), capture only the load-bearing clause — but still verbatim.
- If a quote spans a page break, record the higher page number and note `quote_continues_from_prior_page = true`.
- Captions, footnotes, and chart annotations are valid quote sources — record the figure/chart number too.

## Fields that are common pitfalls (be careful)

- **EBITDA**: always note Adjusted vs. unadjusted. Capture every addback line.
- **Recurring**: contractually-recurring (subscription) ≠ re-occurring (repeat buyers). Capture the CIM's definition.
- **Pro forma**: revenue numbers may include synergies or acquired-company contribution. Flag explicitly.
- **TAM**: bottom-up vs. top-down — capture which.
- **Customer #**: customers vs. accounts vs. logos vs. seats — capture which.
- **FY vs CY**: every year must carry the FY end. A 6/30 FY2024 ≠ 12/31 CY2024.
