import requests
import os
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# CONFIG
# ======================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

TIMEOUT = 6
TEST_MODE = False  # ← set True to test Discord
SEEN_FILE = "seen_deals.json"

# ======================
# GPU FILTERS
# ======================

ALLOWED_GPUS = [
    "RTX 4070",
    "RTX 4070 SUPER",
    "RTX 4070 TI",
    "RTX 4070 TI SUPER",
    "RTX 4080",
    "RTX 4080 SUPER",
    "RTX 4090",
    "RTX 5070",
    "RTX 5070 TI",
    "RTX 5080",
    "RTX 5090",
]

MSRP = {
    "RTX 4070": 599,
    "RTX 4070 SUPER": 599,
    "RTX 4070 TI": 799,
    "RTX 4070 TI SUPER": 799,
    "RTX 4080": 1199,
    "RTX 4080 SUPER": 999,
    "RTX 4090": 1599,
    "RTX 5070": 549,
    "RTX 5070 TI": 749,
    "RTX 5080": 999,
    "RTX 5090": 1599,
}

# ======================
# STATE
# ======================

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

SEEN = load_seen()

# ======================
# HELPERS
# ======================

def match_gpu(title):
    t = title.upper()
    if "60" in t:  # blocks 3060 / 4060 / 5060
        return None
    for gpu in ALLOWED_GPUS:
        if gpu in t:
            return gpu
    return None

def extract_price(text):
    text = text.replace(",", "")
    for word in text.split():
        if word.startswith("$"):
            try:
                return int(word.replace("$", ""))
            except:
                pass
    return None

def send_discord(store, emoji, gpu, price, link):
    diff = price - MSRP[gpu]
    sign = "+" if diff > 0 else ""

    payload = {
        "content": (
            f"🔥 **GPU DEAL FOUND** 🔥\n\n"
            f"🎮 **{gpu}**\n"
            f"{emoji} **{store}**\n"
            f"💵 Price: **${price}**\n"
            f"💰 MSRP: ${MSRP[gpu]} ({sign}{diff}$)\n"
            f"🔗 {link}"
        )
    }

    requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)

# ======================
# TEST MODE
# ======================

def run_test():
    print("🧪 TEST MODE — sending test alert")
    send_discord(
        "Test Store",
        "🧪",
        "RTX 4070 SUPER",
        599,
        "https://example.com"
    )

# ======================
# STORE CHECKS
# ======================

def check_bestbuy():
    print("🟦 Best Buy Checking")
    url = "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+graphics+card"

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ 🟦 Best Buy skipped: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("a"):
        title = a.get_text(strip=True)
        href = a.get("href")

        if not title or not href:
            continue

        gpu = match_gpu(title)
        if not gpu:
            continue

        price = extract_price(a.parent.get_text(" ", strip=True))
        if not price:
            continue

        key = f"BestBuy|{gpu}|{price}"
        if key in SEEN:
            continue

        if price <= MSRP[gpu]:
            link = "https://www.bestbuy.com" + href
            send_discord("Best Buy", "🟦", gpu, price, link)
            SEEN.add(key)
            save_seen(SEEN)

def check_amazon():
    print("🟧 Amazon Checking")
    url = "https://www.amazon.com/s?k=rtx+graphics+card"

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ 🟧 Amazon skipped: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select("div[data-component-type='s-search-result']"):
        title_tag = item.select_one("h2 span")
        price_tag = item.select_one("span.a-price-whole")
        link_tag = item.select_one("h2 a")

        if not title_tag or not price_tag or not link_tag:
            continue

        title = title_tag.text.strip()
        gpu = match_gpu(title)
        if not gpu:
            continue

        try:
            price = int(price_tag.text.replace(",", "").replace(".", ""))
        except:
            continue

        key = f"Amazon|{gpu}|{price}"
        if key in SEEN:
            continue

        if price <= MSRP[gpu]:
            link = "https://www.amazon.com" + link_tag["href"]
            send_discord("Amazon", "🟧", gpu, price, link)
            SEEN.add(key)
            save_seen(SEEN)

def check_newegg():
    print("🟥 Newegg Checking")
    url = "https://www.newegg.com/p/pl?d=rtx+graphics+card"

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ 🟥 Newegg skipped: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select(".item-cell"):
        title_tag = item.select_one(".item-title")
        price_tag = item.select_one(".price-current strong")

        if not title_tag or not price_tag:
            continue

        title = title_tag.text.strip()
        gpu = match_gpu(title)
        if not gpu:
            continue

        try:
            price = int(price_tag.text.replace(",", ""))
        except:
            continue

        key = f"Newegg|{gpu}|{price}"
        if key in SEEN:
            continue

        if price <= MSRP[gpu]:
            send_discord("Newegg", "🟥", gpu, price, title_tag["href"])
            SEEN.add(key)
            save_seen(SEEN)

def check_microcenter():
    print("🟩 Micro Center (Tustin) Checking")
    url = "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+gpu&storeid=101"

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ 🟩 Micro Center skipped: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select(".product_wrapper"):
        title_tag = item.select_one(".h2 a")
        price_tag = item.select_one(".price span")

        if not title_tag or not price_tag:
            continue

        title = title_tag.text.strip()
        gpu = match_gpu(title)
        if not gpu:
            continue

        try:
            price = int(price_tag.text.replace("$", "").replace(",", ""))
        except:
            continue

        key = f"MicroCenter|{gpu}|{price}"
        if key in SEEN:
            continue

        if price <= MSRP[gpu]:
            link = "https://www.microcenter.com" + title_tag["href"]
            send_discord("Micro Center (Tustin)", "🟩", gpu, price, link)
            SEEN.add(key)
            save_seen(SEEN)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    print(f"⏰ Run started at {datetime.utcnow()} UTC")

    if TEST_MODE:
        run_test()
        exit(0)

    check_bestbuy()
    time.sleep(1)

    check_amazon()
    time.sleep(1)

    check_newegg()
    time.sleep(1)

    check_microcenter()

    print("✅ Run complete")
