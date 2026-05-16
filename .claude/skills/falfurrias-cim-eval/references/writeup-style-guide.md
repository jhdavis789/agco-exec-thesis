# Writeup Style Guide

The user will refine this with examples. Until then, use the patterns below — they're modeled on the AGCO Executive Thesis already in this repo (`/index.html`), which reads like a Falfurrias "Industry First" workup.

## Voice

- **Dense, sourced, numerate.** Every paragraph either delivers a fact with a citation or names a thesis that the prior facts support.
- **Contrarian when warranted.** State explicitly where the consensus or banker pitch is wrong. Don't hedge with "potentially" / "could" / "may."
- **Crisp framings.** Each thesis gets a one-line headline: *"Customers are generationally locked in"* — not *"Customer retention may be a factor."*
- **No filler.** Cut anything that doesn't change the recommendation.

## Structure (IC memo)

Mirror the AGCO thesis structure:

1. **At a glance** — 4–6 metric tiles (Revenue, EBITDA, Margin, Growth, EV ask / multiple)
2. **What it is** — one paragraph, business model
3. **The cycle / context** — sector tailwind, with sourced data
4. **Unit economics** — what one customer / unit / contract is worth over its lifetime
5. **Theses** — 2–3 numbered theses, each a section, each with a callout summary
6. **Risks & red flags** — table + callouts
7. **Recommendation** — Pass / Track / Pursue, named champion, key DD priorities

## Density signals

- **Tables for comparisons.** Peer multiples, customer cohorts, revenue bridges.
- **Color-coded callouts.** Green for "this is durable," gold for "watch this," red for "this is the risk."
- **Exhibit numbers.** Every meaningful chart / table earns an exhibit label.
- **Sources at the foot of each section.** Italic, small.

## Things that are NOT in scope (until the user refines)

- Final color palette / typography — assume the AGCO doc's palette for now if HTML is ever generated
- Whether the deliverable becomes HTML (currently markdown by user direction)
- Banker-quote pull-out treatment

## Words to avoid

- "Synergistic"
- "Leverage" (as a verb)
- "Best-in-class" (unless quoting the banker, and then mark it as a banker claim)
- "Robust" (most uses are filler)
- "Potentially" / "could" / "may" — pick a direction or omit
- "Headwinds / tailwinds" — name the specific driver instead

## Words to use

- Verbs of motion: "compounds," "lapses," "switches," "compresses," "expands"
- Specific quantities: "$1M per tractor over 20 years" beats "high lifetime value"
- Named comparisons: "Trades at 9.2x vs Deere at 18.5x" beats "trades at a discount"
- The pattern-match line: "This is the closest profile we have to [Sauer Brands / Crosslake / Oddball]"

## Banker-quote handling

Every banker claim gets one of three treatments:

1. **Triangulated** — supported by ≥2 independent CIM passages or third-party data → use as fact.
2. **Single-source** — appears once in the CIM → quote it and label `*Banker claim; not independently triangulated.*`
3. **Disputed** — contradicted by other CIM data or known benchmarks → quote it and explain the dispute.

## Citations

- Inline: `(p. 14)` for page references
- Footnote-style: `[CIM, p. 14]` if multiple sources per paragraph
- External: include URL and date for any non-CIM source

## TODO for user

- Provide 1–2 example IC memos in the desired final voice (paste or commit them; we'll calibrate the style guide off them)
- Confirm whether the deliverable should ever be HTML deck like AGCO/index.html or strictly markdown
- Confirm preferred memo length cap (3 pages? 5? 8?)
