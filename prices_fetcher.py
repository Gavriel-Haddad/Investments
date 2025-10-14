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
    r"Last\s*Rate\s*\((.*?)\)\s*([0-9\.,]+)",          # EN with unit "(0.01 NIS)"
    r"Last\s*Rate.*?([0-9\.,]+)",                       # EN generic
    r"שער\s*אחרון\s*\((.*?)\)\s*([0-9\.,]+)",           # HE with unit "(באגורות)"
    r"שער\s*אחרון[^0-9]*([0-9\.,]+)",                   # HE generic
    r"שער[^0-9]{0,8}([0-9\.,]+)",                       # very loose HE fallback ("שער 436,200")
]

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

def _extract_price(text):
    # Try specific patterns first
    for pat in PRICE_PATTERNS:
        m = re.search(pat, text, flags=re.I|re.S)
        if not m: 
            continue
        # With unit (group 1) + number (group 2)
        if m.lastindex and m.lastindex >= 2:
            unit, num = m.group(1), m.group(2)
            val = _clean_number(num)
            if val is None: 
                continue
            if unit and (("0.01" in unit) or ("אגורות" in unit) or ("Agorot" in unit)):
                val *= 0.01
            # Heuristic: giant integers are usually agorot
            if unit is None and val is not None and val >= 10000:
                val *= 0.01
            return round(val, 6), ("unit:" + unit) if unit else "no-unit"
        # Only number captured
        if m.lastindex and m.lastindex >= 1:
            val = _clean_number(m.group(1))
            if val is None: 
                continue
            if val >= 10000:  # assume agorot
                val *= 0.01
            return round(val, 6), "heuristic"
    return None

def fetch_price_from_source(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return None, f"{name}: HTTP {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        got = _extract_price(text)
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
