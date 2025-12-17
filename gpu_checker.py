import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import hashlib
import json
import os

# ================= CONFIG =================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

TIMEOUT_FAST = 6
TIMEOUT_SLOW = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

SEEN_FILE = "seen.json"

SEARCH_TERMS = [
    "rtx graphics card",
]

MICROCENTER_TUSTIN = "https://www.microcenter.com/search/search_results.aspx?N=&cat=&Ntt=rtx+graphics+card&storeID=101"

# ================= UTIL =================

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()

def send_discord(title, price, link, store):
    if not DISCORD_WEBHOOK:
        return

    payload = {
        "content": (
            f"**{title}**\n"
            f"💲 {price}\n"
            f"🏪 {store}\n"
            f"{link}"
        )
    }
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)

# ================= STORES =================

def check_bestbuy(session, seen):
    print("🟦 Best Buy Checking")
    url = "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+graphics+card"

    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT_SLOW)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".sku-item"):
            title = item.select_one(".sku-title")
            price = item.select_one(".priceView-customer-price span")

            if not title or not price:
                continue

            name = title.text.strip()
            cost = price.text.strip()
            link = "https://www.bestbuy.com" + title.a["href"]

            fp = fingerprint(name + cost)
            if fp in seen:
                continue

            seen.add(fp)
            send_discord(name, cost, link, "Best Buy")

    except Exception as e:
        print(f"⚠️ 🟦 Best Buy skipped: {e}")

def check_amazon(session, seen):
    print("🟧 Amazon Checking (best-effort)")
    url = "https://www.amazon.com/s?k=rtx+graphics+card"

    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT_FAST)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select("[data-component-type='s-search-result']"):
            title = item.select_one("h2 span")
            price_whole = item.select_one(".a-price-whole")

            if not title or not price_whole:
                continue

            name = title.text.strip()
            cost = "$" + price_whole.text.strip()
            link = "https://www.amazon.com" + item.h2.a["href"]

            fp = fingerprint(name + cost)
            if fp in seen:
                continue

            seen.add(fp)
            send_discord(name, cost, link, "Amazon")

    except Exception as e:
        print(f"⚠️ 🟧 Amazon skipped: {e}")

def check_newegg(session, seen):
    print("🟥 Newegg Checking")
    url = "https://www.newegg.com/p/pl?d=rtx+graphics+card"

    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT_FAST)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".item-cell"):
            title = item.select_one(".item-title")
            price = item.select_one(".price-current strong")

            if not title or not price:
                continue

            name = title.text.strip()
            cost = "$" + price.text.strip()
            link = title["href"]

            fp = fingerprint(name + cost)
            if fp in seen:
                continue

            seen.add(fp)
            send_discord(name, cost, link, "Newegg")

    except Exception as e:
        print(f"⚠️ 🟥 Newegg skipped: {e}")

def check_microcenter(session, seen):
    print("🟩 Micro Center (Tustin) Checking")

    try:
        r = session.get(MICROCENTER_TUSTIN, headers=HEADERS, timeout=TIMEOUT_FAST)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".product_wrapper"):
            title = item.select_one(".h2 a")
            price = item.select_one(".price")

            if not title or not price:
                continue

            name = title.text.strip()
            cost = price.text.strip()
            link = "https://www.microcenter.com" + title["href"]

            fp = fingerprint(name + cost)
            if fp in seen:
                continue

            seen.add(fp)
            send_discord(name, cost, link, "Micro Center (Tustin)")

    except Exception as e:
        print(f"⚠️ 🟩 Micro Center skipped: {e}")

# ================= MAIN =================

if __name__ == "__main__":
    start = datetime.utcnow()
    print(f"⏰ Run started at {start} UTC")

    session = requests.Session()
    seen = load_seen()

    check_bestbuy(session, seen)
    check_amazon(session, seen)
    check_newegg(session, seen)
    check_microcenter(session, seen)

    save_seen(seen)

    end = datetime.utcnow()
    print(f"✅ Run finished in {(end - start).total_seconds():.2f}s")
