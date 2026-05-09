"""Compute head-to-head win rates and best-value tallies from data/prices.json
and emit data/results.json.

Two operating modes:

  (a) "live"        — input prices.json was produced by fetch_prices.py and has
                      one row per (sku × retailer × status). Compute pairwise
                      win rates over rows where both retailers have status=ok
                      and a valid normalized_price.

  (b) "aggregated"  — input prices.json is the curated form (one row per SKU
                      with a `prices` map of retailer → {price, normalized_price,
                      source}). Same math, just a different in-memory shape.

The script auto-detects the format by looking at the top-level structure.

Usage:
    python scripts/build_results.py --in data/prices.json --out data/results.json
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

RETAILERS = ["costco", "sams_club", "aldi", "walmart", "amazon", "target", "kroger"]
TIE_TOLERANCE = 0.005  # ±0.5% normalized unit price counted as a tie


def load_prices(path: Path) -> dict[str, dict[str, float]]:
    """Return {sku_id: {retailer: normalized_price}}.

    Drops rows with no normalized_price.
    """
    raw = json.loads(path.read_text())
    by_sku: dict[str, dict[str, float]] = defaultdict(dict)

    if "rows" in raw and raw["rows"] and "prices" in raw["rows"][0]:
        # aggregated form
        for row in raw["rows"]:
            sku = row["sku_id"]
            for retailer, p in row.get("prices", {}).items():
                np = p.get("normalized_price")
                if np is not None:
                    by_sku[sku][retailer] = float(np)
    else:
        # live form (fetch_prices output)
        for row in raw.get("rows", []):
            if row.get("status") != "ok":
                continue
            np = row.get("normalized_price")
            if np is None:
                continue
            by_sku[row["sku_id"]][row["retailer"]] = float(np)

    return dict(by_sku)


def head_to_head(prices: dict[str, dict[str, float]]) -> dict:
    """For each ordered pair (A, B), count overlapping SKUs and how often A < B."""
    pairs = {a: {b: {"overlap_n": 0, "a_wins": 0, "b_wins": 0, "ties": 0} for b in RETAILERS if b != a} for a in RETAILERS}

    for sku, rp in prices.items():
        for a in RETAILERS:
            if a not in rp:
                continue
            for b in RETAILERS:
                if b == a or b not in rp:
                    continue
                cell = pairs[a][b]
                cell["overlap_n"] += 1
                pa, pb = rp[a], rp[b]
                if abs(pa - pb) / max(pa, pb) <= TIE_TOLERANCE:
                    cell["ties"] += 1
                elif pa < pb:
                    cell["a_wins"] += 1
                else:
                    cell["b_wins"] += 1

    matrix = {a: {} for a in RETAILERS}
    for a in RETAILERS:
        for b in RETAILERS:
            if b == a:
                matrix[a][b] = None
                continue
            cell = pairs[a][b]
            if cell["overlap_n"] == 0:
                matrix[a][b] = None
            else:
                # ties split half/half
                a_share = cell["a_wins"] + cell["ties"] * 0.5
                matrix[a][b] = round(100.0 * a_share / cell["overlap_n"])
    return matrix, pairs


def best_value(prices: dict[str, dict[str, float]]) -> dict:
    """Two views of 'best value':
       - strict: denominator = all SKUs in the basket
       - carried_only: denominator = SKUs the retailer prices
    """
    n_total = len(prices)
    cheapest_count = defaultdict(int)
    carried_count = defaultdict(int)

    for sku, rp in prices.items():
        if not rp:
            continue
        for r in rp:
            carried_count[r] += 1
        min_price = min(rp.values())
        winners = [r for r, p in rp.items() if abs(p - min_price) / max(p, min_price) <= TIE_TOLERANCE]
        # tied winners share the win
        for r in winners:
            cheapest_count[r] += 1.0 / len(winners)

    return {
        "strict": {r: round(100.0 * cheapest_count.get(r, 0) / n_total) for r in RETAILERS},
        "carried_only": {
            r: round(100.0 * cheapest_count.get(r, 0) / carried_count[r]) if carried_count.get(r) else 0
            for r in RETAILERS
        },
        "coverage_pct": {r: round(100.0 * carried_count.get(r, 0) / n_total) for r in RETAILERS},
    }


def by_category(basket_path: Path, prices: dict[str, dict[str, float]]) -> dict:
    """Best-value % within each category, using basket.json's category map."""
    basket = json.loads(basket_path.read_text())
    cat_of = {s["sku_id"]: s["category"] for s in basket["skus"]}
    by_cat_skus: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for sku, rp in prices.items():
        cat = cat_of.get(sku)
        if cat:
            by_cat_skus[cat][sku] = rp

    out = {}
    for cat, sub in by_cat_skus.items():
        bv = best_value(sub)
        out[cat] = {"n_skus": len(sub), "best_value_pct": bv["strict"]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/prices.json")
    ap.add_argument("--out", default="data/results.json")
    ap.add_argument("--basket", default="data/basket.json")
    args = ap.parse_args()

    prices = load_prices(Path(args.inp))
    if not prices:
        raise SystemExit(f"No usable prices in {args.inp}")

    matrix, raw_pairs = head_to_head(prices)
    bv = best_value(prices)
    cats = by_category(Path(args.basket), prices)

    out = {
        "_comment": "Generated by scripts/build_results.py",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_skus": len(prices),
        "retailers": RETAILERS,
        "head_to_head": matrix,
        "head_to_head_overlap": raw_pairs,
        "overall_best_value": bv,
        "by_category": cats,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}: n_skus={len(prices)}")
    print("Best-value (strict):", bv["strict"])
    print("Coverage:", bv["coverage_pct"])


if __name__ == "__main__":
    main()
