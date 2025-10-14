# pip install requests beautifulsoup4
import re
import sys
from typing import Iterable, Dict, Any, Tuple
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (+price-fetcher)"}

# Try ETF page first, then Fund page
FUNDER_URLS = [
    "https://www.funder.co.il/etf/{id}",
    "https://www.funder.co.il/fund/{id}",
]

def _first_price_after(anchor_text: str, full_text: str) -> float:
    """
    Find the first big numeric right after a section anchor ("מחיר" or "שער אחרון").
    Returns value as a float of agorot (e.g., 436200.0) which we later convert to NIS.
    """
    i = full_text.find(anchor_text)
    if i == -1:
        return None  # type: ignore
    tail = full_text[i:i+800]  # scan a small window to avoid matching dates/times
    # Prefer 5–9 digit integers (agorot) or the same with separators, ignore dates like 12/10/25
    m = re.search(r"\b(\d{5,9}|\d{1,3}(?:[,\s]\d{3}){1,3})\b", tail)
    if not m:
        return None  # type: ignore
    raw = m.group(1).replace(",", "").replace(" ", "")
    return float(raw)

def _parse_funder_price(html: str) -> Tuple[float, str]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # Try anchors in order of reliability
    for anchor in ("מחיר", "שער אחרון", "שער"):
        agorot = _first_price_after(anchor, text)
        if agorot:
            nis = agorot / 100.0
            return nis, "agorot->NIS (/100) from Funder"
    raise ValueError("Price not found on page")

def fetch_price_by_number(sec_id: int) -> Dict[str, Any]:
    """
    Returns dict with 'nis', 'source' and 'url' for the given TASE security number.
    """
    last_exc = None
    for tmpl in FUNDER_URLS:
        url = tmpl.format(id=sec_id)
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                nis, note = _parse_funder_price(r.text)
                return {"id": sec_id, "nis": nis, "url": url, "source": f"Funder ({note})"}
        except Exception as e:
            last_exc = e
            continue
    raise RuntimeError(f"Failed to fetch {sec_id}. Last error: {last_exc}")

def fetch_many(ids: Iterable[int]) -> Dict[int, float]:
    out = {}
    for sec_id in ids:
        try:
            res = fetch_price_by_number(sec_id)
            out[sec_id] = res["nis"]
            print(f"{sec_id}: {res['nis']:.2f} NIS   [{res['url']}]")
        except Exception as e:
            print(f"{sec_id}: ERROR - {e}", file=sys.stderr)
    return out

if __name__ == "__main__":
    # >>> Put your numbers here:
    SECURITY_NUMBERS = [1183441, 1159250]  # add more like 1159250, 5121430, ...
    fetch_many(SECURITY_NUMBERS)
