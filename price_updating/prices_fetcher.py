import re, time, json, requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
}

SOURCES = [
    # TASE (EN + HE). HE needs 8-digit code with leading zero.
    ("TASE EN major", "https://market.tase.co.il/en/market_data/security/{code}"),
    ("TASE HE major", "https://market.tase.co.il/he/market_data/security/{code8}/major_data"),
    ("TASE EN graph", "https://market.tase.co.il/en/market_data/security/{code}/graph"),
    # TheMarker finance (often plain HTML text)
    ("TheMarker", "https://finance.themarker.com/etf/{code}"),
    # Funder ETF page
    ("Funder ETF", "https://www.funder.co.il/etf/{code}"),
    # Bizportal traded fund (as extra fallback)
    ("Bizportal ETF", "https://www.bizportal.co.il/tradedfund/quote/generalview/{code}"),
]

# Patterns to find a price on each page.
# We look for "Last Rate" / "שער אחרון" / generic "שער" + a number.
PRICE_PATTERNS = [
    # EN with unit before number
    r"Last\s*Rate\s*\((.*?)\)\s*([0-9\.,]+)",
    r"Last\s*Rate[^0-9]*([0-9\.,]+)\s*\((.*?)\)",       # EN with unit after number, inside ()
    r"Last\s*Rate.*?([0-9\.,]+)",

    # HE with unit before number
    r"שער\s*אחרון\s*\((.*?)\)\s*([0-9\.,]+)",
    # HE with unit after number
    r"שער\s*אחרון[^0-9]*([0-9\.,]+)\s*\((.*?)\)",
    r"שער\s*אחרון[^0-9]*([0-9\.,]+)",

    # Very loose fallbacks
    r"שער[^0-9]{0,12}([0-9\.,]+)",
    r"([0-9\.,]+)\s*(?:אג(?:'|ורות)?|Agorot|0\.01\s*NIS)",  # unit after number
]

def _is_agorot_unit(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    s_lower = s.lower()
    return (
        "0.01" in s_lower or
        "agorot" in s_lower or
        "אג" in s or
        "אג'" in s or
        "אגורות" in s
    )

def _clean_number(txt):
    if not txt: return None
    t = re.sub(r"[^\d\.,\-]", "", txt.strip())
    if "," in t and "." in t:
        t = t.replace(",", "")
    elif "," in t and "." not in t:
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")
    try:
        return float(t)
    except:
        return None

def _extract_price(text: str):
    """
    Try patterns; if no explicit unit was found next to the number,
    scan a larger window and finally the WHOLE PAGE for agorot hints
    before returning.
    """
    best_val = None
    best_unit = None
    best_how = None

    for pat in PRICE_PATTERNS:
        m = re.search(pat, text, flags=re.I | re.S)
        if not m:
            continue

        # Pull number and any other captured group (potentially unit)
        unit = None
        num = None

        if m.lastindex:
            groups = [g for g in m.groups() if g is not None]
            # pick first numeric-like token as number
            for g in groups:
                v = _clean_number(g)
                if v is not None:
                    num = g
                    break
            # pick a different group as unit candidate
            unit_candidates = [g for g in groups if g is not num]
            unit = unit_candidates[0] if unit_candidates else None

        if num is None and m.lastindex and m.lastindex >= 1:
            num = m.group(1)

        val = _clean_number(num) if num is not None else None
        if val is None:
            continue

        # 1) local window scan (now much larger)
        if not _is_agorot_unit(unit):
            start, end = m.span()
            wstart = max(0, start - 250)
            wend   = min(len(text), end + 250)
            window = text[wstart:wend]
            if _is_agorot_unit(window):
                unit = "nearby-agorot"

        # 2) if still no unit, remember candidate and keep searching (don’t return yet)
        candidate_val = val
        candidate_unit = unit

        # 3) save the best candidate so far
        # prefer one with explicit/nearby unit
        if _is_agorot_unit(candidate_unit):
            best_val = candidate_val * 0.01
            best_unit = "agorot"
            best_how = "unit-detected"
            break  # found explicit agorot, we’re done
        else:
            # keep as fallback; we may still discover global agorot below
            best_val = candidate_val
            best_unit = None
            best_how = "no-unit"

    if best_val is None:
        return None

    # 4) GLOBAL PAGE SCAN for agorot hints if we didn’t detect a unit near the match
    if best_unit is None:
        if re.search(r"(?:0\.01\s*NIS|Agorot|אג(?:'|ורות)?)", text, flags=re.I):
            return round(best_val * 0.01, 6), "unit:global-agorot"

    # 5) heuristic: giant integers are usually agorot
    if best_val >= 10000:
        return round(best_val * 0.01, 6), "heuristic"

    return round(best_val, 6), (f"unit:{best_unit}" if best_unit else "no-unit")

def fetch_price_from_source(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return None, f"{name}: HTTP {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Try parsed text first, then raw HTML (some units appear only in scripts)
        got = _extract_price(text) or _extract_price(r.text)
        if got:
            price, how = got
            return (price, f"{name} ({how}) {url}")
        return None, f"{name}: pattern not found"
    except requests.RequestException as e:
        return None, f"{name}: {e.__class__.__name__}"


def get_price_for_code(code):
    code8 = f"{int(code):08d}"
    for name, tmpl in SOURCES:
        url = tmpl.format(code=code, code8=code8)
        val, info = fetch_price_from_source(name, url)
        if val is not None:
            return val #, info
    return None #, "No source yielded a price"

# if __name__ == "__main__":
#     codes = [1183441, 5137641, 1159250, 5114657]  # edit this list

#     results = {}
#     for c in codes:
#         price, src = get_price_for_code(c)
#         results[c] = {"price_nis": None if price is None else f"{price:.6f}", "source": src}
#         time.sleep(0.6)  # be polite

#     # simple list of values in input order
#     values = [results[c]["price_nis"] for c in codes]
#     print(values)
#     # detailed mapping
#     print(json.dumps(results, ensure_ascii=False, indent=2))
