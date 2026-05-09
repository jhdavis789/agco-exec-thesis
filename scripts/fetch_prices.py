"""Best-effort live fetch of retailer prices for every SKU in data/basket.json.

Writes data/prices.json. Each row carries:
  sku_id, retailer, status, price, normalized_price, source_url, fetched_at

Per-retailer adapters use the strategy with the best chance of working without
a headless browser:
  - Walmart   : product page __NEXT_DATA__ JSON
  - Target    : redsky.target.com aggregations API (publicly accessible)
  - Kroger    : kroger.com /atlas/v1/product/v2/products (guest session token)
  - Aldi      : shop.aldi.us /api/v3/store-context + /products/search
  - Costco    : costco.com search + product page (membership-walled SKUs return walled)
  - Sam's Club: samsclub.com search + product page (membership-walled)
  - Amazon    : amazon.com/dp/<asin> if hint contains an ASIN (mostly bot-blocked)

Run from repo root:
    python scripts/fetch_prices.py --basket data/basket.json --out data/prices.json
Optional flags:
    --zip 30309               (default delivery zone)
    --concurrency 4           (per-retailer parallel requests)
    --retailers walmart,target  (subset)
    --skus 50                 (cap for smoke-testing)

This script is the LIVE side of the pipeline. Sandboxed environments and
datacenter IPs are typically blocked at retailer WAFs — the script will still
run, every adapter will log a status (ok/blocked/not_found/parse_error/etc),
and the coverage report at the end tells you what worked. When run from a
residential IP the success rate is materially higher.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{2})?)")
PER_UNIT_RE = re.compile(r"\$?([0-9]+(?:\.[0-9]+)?)\s*(?:¢|cents?)?\s*/\s*([a-zA-Z][a-zA-Z. ]{0,5})", re.I)


@dataclass
class PriceRow:
    sku_id: str
    retailer: str
    status: str
    price: float | None = None
    normalized_price: float | None = None
    normalization: str | None = None
    canonical_name: str | None = None
    source_url: str | None = None
    error: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    if extra:
        h.update(extra)
    return h


def normalize(price: float | None, normalization: str, canonical_name: str) -> float | None:
    """Convert list price to per-pound / per-oz / per-count etc.

    Sizes are inferred from the SKU's canonical_name (e.g., '5lb', '92oz', '24ct').
    Returns None if size can't be parsed; analysis layer drops these from win-rate math.
    """
    if price is None:
        return None
    name = canonical_name.lower()

    def find_unit(pattern: str) -> float | None:
        m = re.search(pattern, name)
        return float(m.group(1)) if m else None

    if normalization == "per_lb":
        lb = find_unit(r"(\d+(?:\.\d+)?)\s*lb")
        oz = find_unit(r"(\d+(?:\.\d+)?)\s*oz")
        if lb:
            return round(price / lb, 4)
        if oz:
            return round(price / (oz / 16.0), 4)
        return price
    if normalization == "per_oz":
        oz = find_unit(r"(\d+(?:\.\d+)?)\s*oz")
        if oz:
            return round(price / oz, 4)
        return None
    if normalization == "per_fl_oz":
        oz = find_unit(r"(\d+(?:\.\d+)?)\s*(?:fl\.?\s*)?oz")
        gal = find_unit(r"(\d+(?:\.\d+)?)\s*gal")
        liter = find_unit(r"(\d+(?:\.\d+)?)\s*l\b")
        if oz:
            return round(price / oz, 4)
        if gal:
            return round(price / (gal * 128.0), 4)
        if liter:
            return round(price / (liter * 33.814), 4)
        return None
    if normalization == "per_ct":
        ct = find_unit(r"(\d+)\s*(?:ct|count|pk|pack)")
        if ct:
            return round(price / ct, 4)
        return price
    if normalization == "per_load":
        loads = find_unit(r"(\d+)\s*loads?")
        if loads:
            return round(price / loads, 4)
        return None
    if normalization == "per_sheet":
        sh = find_unit(r"(\d+)\s*sheets?")
        if sh:
            return round(price / sh, 5)
        return None
    return price


# ---------- adapters ----------

async def fetch_walmart(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    q = quote_plus(sku["search_query"])
    url = f"https://www.walmart.com/search?q={q}"
    try:
        r = await client.get(url, headers=headers({"Referer": "https://www.walmart.com/"}))
        if r.status_code == 403 or r.status_code == 412:
            return PriceRow(sku["sku_id"], "walmart", "blocked", source_url=url, error=f"http {r.status_code}")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "walmart", "http_error", source_url=url, error=f"http {r.status_code}")

        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', r.text, re.DOTALL)
        if not m:
            return PriceRow(sku["sku_id"], "walmart", "parse_error", source_url=url, error="no NEXT_DATA")
        data = json.loads(m.group(1))
        items = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialData", {})
            .get("searchResult", {})
            .get("itemStacks", [{}])[0]
            .get("items", [])
        )
        for it in items:
            price = it.get("priceInfo", {}).get("linePrice") or it.get("price", {}).get("price")
            if isinstance(price, str):
                m2 = PRICE_RE.search(price)
                price = float(m2.group(1)) if m2 else None
            if price:
                p = float(price)
                norm = normalize(p, sku["normalization"], sku["canonical_name"])
                return PriceRow(
                    sku["sku_id"], "walmart", "ok",
                    price=p, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=it.get("name", sku["canonical_name"]),
                    source_url=f"https://www.walmart.com{it.get('canonicalUrl', '')}",
                )
        return PriceRow(sku["sku_id"], "walmart", "not_found", source_url=url)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "walmart", "timeout", source_url=url, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "walmart", "exception", source_url=url, error=f"{type(e).__name__}: {e}")


async def fetch_target(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    """Target's redsky aggregation API. The 'key' is rotated periodically by Target;
    extract a fresh one from a real target.com PLP page if this stops working."""
    q = quote_plus(sku["search_query"])
    api = (
        "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2"
        "?key=9f36aeafbe60771e321a7cc95a78140772ab3e96"
        f"&keyword={q}&channel=WEB&count=24&default_purchasability_filter=true"
        f"&page=%2Fs%2F{q}"
        "&platform=desktop&pricing_store_id=3991&visitor_id=00000000000000000000000000000000"
    )
    try:
        r = await client.get(api, headers=headers({"Referer": "https://www.target.com/", "Origin": "https://www.target.com"}))
        if r.status_code == 403:
            return PriceRow(sku["sku_id"], "target", "blocked", source_url=api, error="http 403 — rotate API key")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "target", "http_error", source_url=api, error=f"http {r.status_code}")
        data = r.json()
        products = data.get("data", {}).get("search", {}).get("products", [])
        for p in products:
            price = p.get("price", {}).get("current_retail")
            if price:
                pr = float(price)
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                tcin = p.get("tcin")
                return PriceRow(
                    sku["sku_id"], "target", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=p.get("item", {}).get("product_description", {}).get("title"),
                    source_url=f"https://www.target.com/p/-/A-{tcin}",
                )
        return PriceRow(sku["sku_id"], "target", "not_found", source_url=api)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "target", "timeout", source_url=api, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "target", "exception", source_url=api, error=f"{type(e).__name__}: {e}")


async def fetch_kroger(client: httpx.AsyncClient, sku: dict, store_id: str = "01400376") -> PriceRow:
    q = quote_plus(sku["search_query"])
    api = f"https://www.kroger.com/atlas/v1/product/v2/products?filter.locationId={store_id}&filter.term={q}&filter.tab=0&page.offset=0&page.size=24"
    try:
        r = await client.get(api, headers=headers({"Referer": "https://www.kroger.com/", "Origin": "https://www.kroger.com"}))
        if r.status_code == 403:
            return PriceRow(sku["sku_id"], "kroger", "blocked", source_url=api, error="http 403 — needs guest session cookie")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "kroger", "http_error", source_url=api, error=f"http {r.status_code}")
        data = r.json()
        for p in (data.get("data", []) or [])[:5]:
            item = p.get("item", {}) if isinstance(p, dict) else {}
            price = item.get("price", {}).get("regular") or item.get("price", {}).get("promo")
            if price:
                pr = float(price)
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                return PriceRow(
                    sku["sku_id"], "kroger", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=p.get("description"),
                    source_url=f"https://www.kroger.com/p/.../{p.get('upc', '')}",
                )
        return PriceRow(sku["sku_id"], "kroger", "not_found", source_url=api)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "kroger", "timeout", source_url=api, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "kroger", "exception", source_url=api, error=f"{type(e).__name__}: {e}")


async def fetch_aldi(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    q = quote_plus(sku["search_query"])
    api = f"https://shop.aldi.us/api/v3/product-search/{q}?currency=USD&servicePoint=470-021&serviceType=pickup&offset=0&limit=24"
    try:
        r = await client.get(api, headers=headers({"Referer": "https://shop.aldi.us/", "Accept": "application/json"}))
        if r.status_code == 403:
            return PriceRow(sku["sku_id"], "aldi", "blocked", source_url=api, error="http 403")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "aldi", "http_error", source_url=api, error=f"http {r.status_code}")
        data = r.json()
        for p in data.get("data", []) or []:
            price = p.get("price", {}).get("amountRelevantDisplay")
            if isinstance(price, str):
                m = PRICE_RE.search(price)
                price = float(m.group(1)) if m else None
            if price:
                pr = float(price)
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                return PriceRow(
                    sku["sku_id"], "aldi", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=p.get("name"),
                    source_url=f"https://shop.aldi.us{p.get('urlSlug', '')}",
                )
        return PriceRow(sku["sku_id"], "aldi", "not_found", source_url=api)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "aldi", "timeout", source_url=api, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "aldi", "exception", source_url=api, error=f"{type(e).__name__}: {e}")


async def fetch_costco(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    q = quote_plus(sku["search_query"])
    url = f"https://www.costco.com/CatalogSearch?dept=All&keyword={q}"
    try:
        r = await client.get(url, headers=headers({"Referer": "https://www.costco.com/"}))
        if r.status_code == 403:
            return PriceRow(sku["sku_id"], "costco", "blocked", source_url=url, error="http 403")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "costco", "http_error", source_url=url, error=f"http {r.status_code}")
        tree = HTMLParser(r.text)
        for tile in tree.css(".product"):
            price_el = tile.css_first(".price")
            if not price_el:
                continue
            price_txt = price_el.text(strip=True)
            if "Sign In" in price_txt or "Member" in price_txt:
                return PriceRow(sku["sku_id"], "costco", "membership_walled", source_url=url)
            m = PRICE_RE.search(price_txt)
            if m:
                pr = float(m.group(1))
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                a = tile.css_first("a")
                href = a.attributes.get("href") if a else None
                return PriceRow(
                    sku["sku_id"], "costco", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=tile.css_first(".description").text(strip=True) if tile.css_first(".description") else None,
                    source_url=href,
                )
        return PriceRow(sku["sku_id"], "costco", "not_found", source_url=url)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "costco", "timeout", source_url=url, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "costco", "exception", source_url=url, error=f"{type(e).__name__}: {e}")


async def fetch_sams_club(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    q = quote_plus(sku["search_query"])
    url = f"https://www.samsclub.com/s/{q}"
    try:
        r = await client.get(url, headers=headers({"Referer": "https://www.samsclub.com/"}))
        if r.status_code == 403:
            return PriceRow(sku["sku_id"], "sams_club", "blocked", source_url=url, error="http 403")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "sams_club", "http_error", source_url=url, error=f"http {r.status_code}")
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', r.text, re.DOTALL)
        if not m:
            return PriceRow(sku["sku_id"], "sams_club", "parse_error", source_url=url, error="no NEXT_DATA")
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return PriceRow(sku["sku_id"], "sams_club", "parse_error", source_url=url, error="bad json")
        # Sam's Club's structure varies; this is a best-effort dive.
        items = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialReduxState", {})
            .get("searchResults", {})
            .get("payload", {})
            .get("records", [])
        )
        for it in items:
            price = it.get("price", {}).get("finalPrice", {}).get("amount")
            if price:
                pr = float(price)
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                return PriceRow(
                    sku["sku_id"], "sams_club", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=it.get("title"),
                    source_url=f"https://www.samsclub.com{it.get('seoUrl', '')}",
                )
        return PriceRow(sku["sku_id"], "sams_club", "not_found", source_url=url)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "sams_club", "timeout", source_url=url, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "sams_club", "exception", source_url=url, error=f"{type(e).__name__}: {e}")


async def fetch_amazon(client: httpx.AsyncClient, sku: dict) -> PriceRow:
    q = quote_plus(sku["search_query"])
    url = f"https://www.amazon.com/s?k={q}"
    try:
        r = await client.get(url, headers=headers({"Referer": "https://www.amazon.com/"}))
        if r.status_code == 503 or r.status_code == 403:
            return PriceRow(sku["sku_id"], "amazon", "blocked", source_url=url, error=f"http {r.status_code}")
        if r.status_code != 200:
            return PriceRow(sku["sku_id"], "amazon", "http_error", source_url=url, error=f"http {r.status_code}")
        if "captcha" in r.text.lower() or "automated access" in r.text.lower():
            return PriceRow(sku["sku_id"], "amazon", "blocked", source_url=url, error="captcha challenge")
        tree = HTMLParser(r.text)
        for card in tree.css('div[data-component-type="s-search-result"]'):
            whole = card.css_first("span.a-price-whole")
            frac = card.css_first("span.a-price-fraction")
            if whole and frac:
                price_txt = whole.text(strip=True).rstrip(".") + "." + frac.text(strip=True)
                try:
                    pr = float(price_txt)
                except ValueError:
                    continue
                norm = normalize(pr, sku["normalization"], sku["canonical_name"])
                title_el = card.css_first("h2 a span")
                href_el = card.css_first("h2 a")
                href = href_el.attributes.get("href") if href_el else ""
                return PriceRow(
                    sku["sku_id"], "amazon", "ok",
                    price=pr, normalized_price=norm, normalization=sku["normalization"],
                    canonical_name=title_el.text(strip=True) if title_el else None,
                    source_url=f"https://www.amazon.com{href}" if href and href.startswith("/") else href,
                )
        return PriceRow(sku["sku_id"], "amazon", "not_found", source_url=url)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        return PriceRow(sku["sku_id"], "amazon", "timeout", source_url=url, error=str(e))
    except Exception as e:
        return PriceRow(sku["sku_id"], "amazon", "exception", source_url=url, error=f"{type(e).__name__}: {e}")


ADAPTERS = {
    "walmart":   fetch_walmart,
    "target":    fetch_target,
    "kroger":    fetch_kroger,
    "aldi":      fetch_aldi,
    "costco":    fetch_costco,
    "sams_club": fetch_sams_club,
    "amazon":    fetch_amazon,
}


async def run_one(sema: asyncio.Semaphore, client: httpx.AsyncClient, retailer: str, sku: dict) -> PriceRow:
    async with sema:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2),
            wait=wait_exponential_jitter(initial=1.5, max=8),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.RemoteProtocolError)),
            reraise=True,
        ):
            with attempt:
                row = await ADAPTERS[retailer](client, sku)
        # polite jitter even on success
        await asyncio.sleep(random.uniform(0.4, 1.2))
        return row


async def main_async(args) -> None:
    basket = json.loads(Path(args.basket).read_text())
    skus = basket["skus"]
    if args.skus:
        skus = skus[: args.skus]
    retailers = args.retailers.split(",") if args.retailers else list(ADAPTERS)

    timeout = httpx.Timeout(15.0, connect=8.0)
    limits = httpx.Limits(max_connections=30, max_keepalive_connections=10)
    rows: list[PriceRow] = []

    async with httpx.AsyncClient(http2=True, follow_redirects=True, timeout=timeout, limits=limits) as client:
        # warm guest session for kroger
        try:
            await client.get("https://www.kroger.com/", headers=headers())
        except Exception:
            pass
        per_retailer_sema = {r: asyncio.Semaphore(args.concurrency) for r in retailers}
        tasks = [
            run_one(per_retailer_sema[r], client, r, sku)
            for sku in skus
            for r in retailers
        ]
        t0 = time.time()
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            row = await coro
            rows.append(row)
            if i % 25 == 0 or i == len(tasks):
                done_pct = 100.0 * i / len(tasks)
                print(f"  [{i}/{len(tasks)}  {done_pct:5.1f}%]  last: {row.retailer:10s} {row.sku_id:36s} {row.status}", file=sys.stderr)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

    # coverage report
    by_retailer: dict[str, dict[str, int]] = {}
    for r in rows:
        d = by_retailer.setdefault(r.retailer, {})
        d[r.status] = d.get(r.status, 0) + 1
    print("\nCoverage report:")
    for retailer, statuses in by_retailer.items():
        attempted = sum(statuses.values())
        ok = statuses.get("ok", 0)
        print(f"  {retailer:10s}  attempted {attempted:4d}  ok {ok:4d}  ({100.0*ok/attempted:5.1f}%)  details {statuses}")

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "target_zip": args.zip,
        "n_rows": len(rows),
        "rows": [asdict(r) for r in rows],
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nWrote {args.out} with {len(rows)} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basket", default="data/basket.json")
    ap.add_argument("--out", default="data/prices.json")
    ap.add_argument("--zip", default="30309")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--retailers", default=None, help="comma-separated subset, e.g. walmart,target")
    ap.add_argument("--skus", type=int, default=None, help="cap SKU count for smoke tests")
    args = ap.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
