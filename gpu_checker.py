import requests
import json
import os
from bs4 import BeautifulSoup
from datetime import datetime

# =========================
# CONFIG
# =========================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
}

SEEN_FILE = "seen_gpus.json"
TIMEOUT = 8  # lower timeout = faster failures

MSRP_LIMITS = {
    "RTX 4070": 600,
    "RTX 4070 SUPER": 600,
    "RTX 4070 Ti": 800,
    "RTX 4080": 1200,
    "RTX 4080 SUPER": 1000,
}

# =========================
# UTILITIES
# =========================

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, "r") as f:
        return json.load(f)

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def send_discord(title, price, link, store):
    payload = {
        "content": (
            "🚨 **GPU FOUND AT MSRP** 🚨\n"
            f"**Store:** {store}\n"
            f"**Product:** {title}\n"
            f"**Price:** ${price}\n"
            f"{link}"
        )
    }
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=TIMEOUT)

def is_msrp(title, price):
    for model, limit in MSRP_LIMITS.items():
        if model.lower() in title.lower() and price <= limit:
            return True
    return False

# =========================
# STORE CHECKERS (SAFE)
# =========================

def check_bestbuy(session, seen):
    print("🟦 Checking Best Buy")
    try:
        url = "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+4070"
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".sku-item"):
            title_el = item.select_one(".sku-title")
            price_el = item.select_one(".priceView-customer-price span")

            if not title_el or not price_el:
                continue

            title = title_el.text.strip()
            price = int(price_el.text.replace("$", "").replace(",", ""))
            link = "https://www.bestbuy.com" + title_el["href"]

            key = f"bestbuy|{title}|{price}"
            if key in seen:
                continue

            if is_msrp(title, price):
                send_discord(title, price, link, "Best Buy")
                seen[key] = True

    except Exception as e:
        print(f"⚠️ Best Buy skipped: {e}")

def check_amazon(session, seen):
    print("🟧 Checking Amazon")
    try:
        url = "https://www.amazon.com/s?k=rtx+4070"
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".s-result-item"):
            title_el = item.select_one("h2 span")
            price_whole = item.select_one(".a-price-whole")

            if not title_el or not price_whole:
                continue

            title = title_el.text.strip()
            price = int(price_whole.text.replace(",", ""))
            link_el = item.select_one("h2 a")
            link = "https://www.amazon.com" + link_el["href"]

            key = f"amazon|{title}|{price}"
            if key in seen:
                continue

            if is_msrp(title, price):
                send_discord(title, price, link, "Amazon")
                seen[key] = True

    except Exception as e:
        print(f"⚠️ Amazon skipped: {e}")

def check_newegg(session, seen):
    print("🟥 Checking Newegg")
    try:
        url = "https://www.newegg.com/p/pl?d=rtx+4070"
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".item-cell"):
            title_el = item.select_one(".item-title")
            price_el = item.select_one(".price-current strong")

            if not title_el or not price_el:
                continue

            title = title_el.text.strip()
            price = int(price_el.text.replace(",", ""))
            link = title_el["href"]

            key = f"newegg|{title}|{price}"
            if key in seen:
                continue

            if is_msrp(title, price):
                send_discord(title, price, link, "Newegg")
                seen[key] = True

    except Exception as e:
        print(f"⚠️ Newegg skipped: {e}")

def check_microcenter(session, seen):
    print("🟩 Checking Micro Center (Tustin)")
    try:
        url = "https://www.microcenter.com/search/search_results.aspx?N=&Ntt=rtx+4070"
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select(".product_wrapper"):
            title_el = item.select_one(".h2")
            price_el = item.select_one(".price")

            if not title_el or not price_el:
                continue

            title = title_el.text.strip()
            price = int(price_el.text.replace("$", "").replace(",", ""))
            link = "https://www.microcenter.com" + title_el["href"]

            key = f"microcenter|{title}|{price}"
            if key in seen:
                continue

            if is_msrp(title, price):
                send_discord(title, price, link, "Micro Center (Tustin)")
                seen[key] = True

    except Exception as e:
        print(f"⚠️ Micro Center skipped: {e}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    start = datetime.utcnow()
    print(f"⏰ Run started at {start} UTC")

    seen = load_seen()

    with requests.Session() as session:
        check_bestbuy(session, seen)
        check_amazon(session, seen)
        check_newegg(session, seen)
        check_microcenter(session, seen)

    save_seen(seen)

    end = datetime.utcnow()
    print(f"✅ Run finished in {(end - start).total_seconds()} seconds")
