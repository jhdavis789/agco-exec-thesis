---
name: falfurrias-cim-eval
description: Evaluate a CIM (Confidential Information Memorandum) through Falfurrias Capital Partners' "Industry First" lens. Trigger when the user asks to "evaluate this CIM", "review this teaser", "screen this deal for Falfurrias", "would Falfurrias do this deal", "rate this CIM", or drops a PDF in `cims/` and asks for a workup. Produces a 1-page teaser screen and a Falfurrias-style IC memo, both grounded in an audited extraction with page-cited quotes.
---

# Falfurrias CIM Evaluation

You are evaluating a CIM the way **Falfurrias Capital Partners** would — operationally-focused lower-middle market PE, $5–60M EBITDA (FCP) or $1–7M EBITDA / $5M+ ARR (FGP), control or large-minority, founder/family-owned bias, "Industry First" thesis-driven sourcing.

## When to invoke

- A PDF appears in `cims/` and the user wants a workup
- The user pastes CIM text and asks for a Falfurrias screen
- The user asks "would Falfurrias do this deal?" or "score this for Falfurrias"

## Inputs

1. **CIM PDF** in `cims/<TargetCompany>_<Year>_<Banker>.pdf`, OR
2. **Pasted CIM text** in the chat

If no CIM is identified, stop and ask the user to drop one in `cims/` or paste it.

## Outputs (default)

Write both to `cims/<TargetCompany>_workup/`:

1. **`teaser-screen.md`** — 1-page pass/track/pursue screen
2. **`ic-memo.md`** — Falfurrias-style investment memo (3–5 pages)
3. **`extraction.json`** — audited structured extraction with page-cited quotes
4. **`audit-log.md`** — every discrepancy the auditor caught and how it was resolved

## Workflow

The workflow is a **strict two-pass extract → audit → write pipeline**. Skipping the audit is forbidden: this is the "never makes mistakes" guardrail.

### Pass 1 — Ingest
1. Read the CIM with `Read` (PDFs auto-OCR up to 20 pages per call; use `pages:` to chunk large CIMs).
2. Note total page count.
3. Identify section boundaries (Executive Summary, Company Overview, Industry, Financials, Management, etc.) by table of contents or section headers.

### Pass 2 — Parallel extraction (sub-agents)
Spawn extractor sub-agents in parallel — one per schema section — each with:
- The full CIM path (or relevant page range)
- The fields it must populate from `references/extraction-schema.md`
- The non-negotiable rule: **every value carries `quote`, `page`, and `source_type`**

Sections (each = one sub-agent, all dispatched in one message):
- `company_and_transaction`
- `business_model`
- `financials`
- `market_and_competition`
- `customers_and_concentration`
- `management_and_employees`
- `risks_and_legal`

### Pass 3 — Audit (independent sub-agent)
Spawn ONE audit sub-agent with:
- The full extraction JSON
- The CIM
- `references/audit-protocol.md`

The audit agent does NOT see the extractor's reasoning. For every field it independently re-locates the cited quote and verifies the value. It produces a discrepancy log.

### Pass 4 — Deterministic cross-checks
After audit, run the deterministic checks listed in `references/audit-protocol.md` (margin math, year-over-year sums, concentration sums, TAM sanity). These are LLM-free arithmetic checks.

### Pass 5 — Falfurrias evaluation
Only after audit is clean (or all discrepancies logged + resolved), load:
- `references/firm-profile.md`
- `references/partners-and-champions.md`
- `references/portfolio-pattern-bank.md`
- `references/sector-fit-rubric.md`
- `references/red-flags.md`

Then produce the **teaser screen** and **IC memo** using templates in `templates/`.

### Pass 6 — Style match
Apply `references/writeup-style-guide.md` for tone, structure, and density. The writeup style is dense, sourced, contrarian-when-warranted, and avoids vague hedging.

## Audit philosophy (read this before extracting)

The goal is **zero invented numbers**. Every quantity in the IC memo must trace back to:
1. A verbatim quote from the CIM with page number, OR
2. A computed value whose primitives are themselves cited, OR
3. An explicitly flagged inference or unknown

The extractor's job is fast, broad coverage. The auditor's job is to assume the extractor is sloppy and prove every line. Discrepancies are not failures — silently passing a discrepancy is the failure.

Read `references/audit-protocol.md` for the full protocol before processing any CIM.

## File map

```
.claude/skills/falfurrias-cim-eval/
├── SKILL.md                          # this file
├── references/
│   ├── firm-profile.md               # Falfurrias strategy, funds, themes
│   ├── partners-and-champions.md     # roster + sector → champion routing
│   ├── portfolio-pattern-bank.md     # 12+ reference deals as comparables
│   ├── sector-fit-rubric.md          # per-sector hurdle / fit checklist
│   ├── extraction-schema.md          # canonical fields, types, citation rules
│   ├── audit-protocol.md             # two-pass extract+audit pipeline + checks
│   ├── red-flags.md                  # auto-disqualify signals
│   └── writeup-style-guide.md        # tone, structure, density
└── templates/
    ├── ic-memo.md                    # IC memo skeleton
    ├── teaser-screen.md              # 1-pager skeleton
    └── extraction.schema.json        # JSON schema for extracted data
```
