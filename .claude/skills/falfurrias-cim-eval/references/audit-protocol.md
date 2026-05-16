# Audit Protocol — "Never Make Mistakes" Pipeline

This is the centerpiece of the skill. The goal: **zero invented numbers, zero unsourced claims, zero silent discrepancies**.

The design assumes the LLM extracting from the CIM will sometimes be sloppy, hallucinate, mis-attribute a quote, or compute incorrectly. So we never trust extraction alone — we always audit.

## The pipeline at a glance

```
CIM PDF
   │
   ▼
[Pass 1: Ingest]                Read PDF, page-tag, identify sections
   │
   ▼
[Pass 2: Parallel extractors]   7 sub-agents, one per section, JSON output
   │
   ▼
[Pass 3: Independent auditor]   Re-verifies every field against the CIM
   │
   ▼
[Pass 4: Deterministic checks]  Pure arithmetic, no LLM
   │
   ▼
[Pass 5: Triangulation]         Cross-source any critical claim
   │
   ▼
[Pass 6: Resolved extraction]   Final extraction.json + audit-log.md
```

Only after Pass 6 do we touch the IC memo or teaser screen.

## Pass 1 — Ingest

1. Read the CIM with the `Read` tool. PDFs >10 pages **must** use the `pages:` parameter.
2. Build a page map: `{section_name → page_range}` from the table of contents or section headers.
3. Record `total_pages` and a hash/filename of the source. The extraction JSON carries these as provenance.

## Pass 2 — Parallel extraction

Spawn **7 extractor sub-agents in a single message** (use `Agent(subagent_type="Explore")` for each — they only need read access). Each is given:

- Path to CIM PDF
- Page range to focus on
- The specific fields it owns (from `extraction-schema.md`)
- The non-negotiable contract below

### Extractor contract

Every field returned must be an object:

```json
{
  "value": <typed value>,
  "quote": "<verbatim quote from the CIM>",
  "page": <integer page number>,
  "source_type": "stated" | "computed" | "inferred" | "not_found",
  "confidence": "high" | "medium" | "low"
}
```

Rules:
- `source_type = "stated"` → `quote` must be verbatim text that appears on the cited page. The `value` must be either identical to or a trivial transformation of (e.g. number reformatted, unit normalized) what the quote says.
- `source_type = "computed"` → the field is derived from other extracted fields. Include a `derivation` string like `"revenue_2024 / revenue_2023 - 1"`. Every primitive used must itself appear in the extraction.
- `source_type = "inferred"` → reasonable inference from CIM context. `quote` should still cite the supporting passage. `confidence` must be `medium` or `low`.
- `source_type = "not_found"` → field genuinely absent from CIM. `value = null`, `quote = ""`, `confidence = "high"` (high confidence it's absent).
- Never invent. Never compute without showing derivation. Never report `"high"` confidence for `inferred`.

### Section ownership (the 7 extractors)

| Agent | Owns these schema sections |
|---|---|
| `company_and_transaction` | Target legal name, HQ, founding, ownership, advisor, process timeline, ask, structure |
| `business_model` | Products/services, revenue model, customer segments, pricing, contract length, recurring %, GTM channels, geography of sales |
| `financials` | Revenue, EBITDA, EBITDA margin, growth, capex, working capital, debt, projections, customer/SKU economics, by year — minimum 3y historical + projection |
| `market_and_competition` | TAM, SAM, market growth rate, share, top competitors, positioning, win/loss themes |
| `customers_and_concentration` | Top 10 customers (named if available), revenue % each, average tenure, churn / NRR, contract terms |
| `management_and_employees` | Key execs, tenure, comp structure, equity rollover, headcount, attrition, union status |
| `risks_and_legal` | Litigation, regulatory, customer concentration, supplier concentration, IP, cyber incidents, ESG, KPI deltas vs prior periods |

## Pass 3 — Independent auditor

Spawn ONE auditor sub-agent. It receives:

- The full extraction JSON
- The CIM
- This audit protocol

It does **NOT** receive the extractors' reasoning, chain-of-thought, or scratchpads.

For every field with `source_type` ∈ `{stated, inferred}`:

1. Go to the cited `page`.
2. Locate the `quote` verbatim (allow whitespace normalization but no rewording).
3. If quote not found → **discrepancy: quote_not_present**.
4. If quote found but doesn't support the `value` → **discrepancy: quote_mismatch**.
5. If quote supports a different value → **discrepancy: value_drift**, record correct value.
6. If `value` is unit-ambiguous (e.g. "$5M" but unclear if revenue or gross profit) → **discrepancy: unit_ambiguous**.

For every field with `source_type = "computed"`:

1. Re-derive from the cited primitives.
2. If recomputation ≠ stated value (allow rounding tolerance: 0.5% relative or 1 unit absolute, whichever is larger) → **discrepancy: computation_error**.

For every field with `source_type = "not_found"`:

1. Sanity-check by searching the CIM index, executive summary, and adjacent sections for the field name and 2–3 synonyms.
2. If a candidate is found → **discrepancy: missed_extraction**, record where.

Output: `audit-log.md` with one row per discrepancy and a `resolution` column. Resolutions:
- **fix** → update extraction.json with correct value
- **flag** → leave in audit log; surface in IC memo as "[unverified — see audit log]"
- **keep** → discrepancy was a false positive (rare; must justify)

## Pass 4 — Deterministic cross-checks

Pure arithmetic — no LLM judgment. Implement in the writeup pass by doing the math yourself and comparing.

Mandatory checks:

1. **EBITDA margin reconciliation:** for every year, `EBITDA / Revenue ≈ EBITDA_margin` (tolerance 0.2pp).
2. **Growth rate consistency:** YoY growth recomputed from levels must match stated growth (tolerance 0.5pp).
3. **Customer concentration ceiling:** `sum(top10_customer_pct) ≤ 100%` and `top1_customer_pct ≤ top10_sum`.
4. **TAM × penetration sanity:** if `market_share` claimed, then `revenue / TAM ≈ market_share` (tolerance 1pp at low share, 5pp at high share).
5. **Headcount × revenue/FTE sanity:** if revenue/FTE is materially out of line for the sector, flag.
6. **Projection growth realism:** if projected growth >2x trailing growth, flag.
7. **Bridge integrity:** revenue bridge components sum to total within 1%.
8. **Working capital sanity:** `(receivables + inventory − payables)` movement reconciles with cash flow statement.
9. **Debt + ask sanity:** `enterprise_value = ask + assumed_debt − cash` — verify if both halves stated.
10. **Year alignment:** every year referenced is the same fiscal-year basis (calendar vs FY).

Any deterministic-check failure goes in `audit-log.md` and forces a `flag` (cannot be silently `kept`).

## Pass 5 — Triangulation for critical claims

For these claims specifically, require **≥2 independent supporting passages in the CIM**, OR explicitly tag as `single_source`:

- Market growth rate (TAM CAGR)
- Competitive position / market share
- Recurring revenue % / NRR
- Customer churn
- "First/largest/leading" superlatives

If only one source exists, the IC memo must say: *"Banker claim; not independently triangulated in the CIM."*

## Pass 6 — Resolved extraction

Outputs:

```
cims/<TargetCompany>_workup/
├── extraction.json          # final, audited
├── audit-log.md             # every discrepancy + resolution
└── unknowns.md              # fields the CIM does not answer (questions for management)
```

## How to spawn the agents (concrete pattern)

In SKILL.md execution, send **one message** with seven `Agent` calls (parallel):

```python
# Pseudocode — actual calls are tool invocations
Agent(subagent_type="Explore", description="Extract company+transaction",
      prompt="Read cims/<file>.pdf pages 1-15. Extract the fields owned by `company_and_transaction` "
             "in extraction-schema.md. Return strict JSON per the extractor contract in audit-protocol.md. "
             "Every field needs quote+page+source_type+confidence.")
# ...six more, one per section
```

Then **separately**, after all 7 return, send the audit agent:

```python
Agent(subagent_type="Explore", description="Audit CIM extraction",
      prompt="You are the auditor. Read cims/<file>.pdf and the extraction JSON at "
             "cims/<TargetCompany>_workup/extraction.json. Follow audit-protocol.md Pass 3. "
             "Produce audit-log.md. Do NOT trust the extractors; verify everything.")
```

Then do Passes 4–6 in the main session (no sub-agent — keep arithmetic local).

## Common failure modes (and how the audit catches them)

| Failure | How it slips into extraction | Caught by |
|---|---|---|
| Banker hype quote treated as fact | "leading provider of X" extracted as `market_position` | Pass 5 triangulation — single-source claim flagged |
| Mis-bucketed year | FY2023 vs CY2023 confusion | Pass 4 check 10 |
| Recurring-revenue inflation | "85% recurring" pulled from chart legend, but CIM body shows 60% | Pass 3 quote re-location |
| EBITDA margin invented | Reported as % but no underlying levels | Pass 4 check 1 |
| Pro forma vs actual confusion | "Adjusted EBITDA" applied as if actual | Extractor must capture the qualifier in `quote`; auditor verifies |
| TAM hallucination | "$50B TAM" with no support | Pass 3 + Pass 5 |
| Top-customer % overcounted | Top 1 reported as 50% of revenue but top 10 also said to be 60% | Pass 4 check 3 |

## Audit log format

`audit-log.md` should be human-readable and editable. One section per discrepancy:

```markdown
### Discrepancy 3 — value_drift on `financials.revenue_2024.value`

- **Extracted:** $48.2M
- **CIM says (p. 14):** "$48.2 million" — but this is FY ending June 2024
- **Resolution:** fix — relabeled as `revenue_fy2024_jun`. Calendar 2024 revenue not provided.
- **Affects:** YoY growth calc, projection bridge

```

## Why this is the right design

- **Parallelism** keeps wall-clock time low even on 100+ page CIMs.
- **Schema-driven extraction** makes "missing fields" visible instead of invisible.
- **Independent auditor** breaks the extractor's confirmation bias.
- **Deterministic checks** catch the failures LLMs are worst at (arithmetic, unit-bucketing).
- **Triangulation** stops banker hype from becoming our thesis.
- **Audit log on disk** creates a record the deal team can review without re-running.
