import requests
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# CONFIG
# ======================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

TEST_MODE = False  # ← SET True TO FORCE TEST ALERTS
SENT_FILE = "sent_deals.json"

# ======================
# MSRP (USD)
# ======================

MSRP = {
    "RTX 4070": 599,
    "RTX 4070 SUPER": 599,
    "RTX 4070 Ti": 799,
    "RTX 4070 Ti SUPER": 799,
    "RTX 4080": 1199,
    "RTX 4080 SUPER": 999,
    "RTX 4090": 1599,
    "RTX 5070": 549,
    "RTX 5070 Ti": 749,
    "RTX 5080": 999,
    "RTX 5090": 1599
}

# ======================
# STATE
# ======================

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent(data):
    with open(SENT_FILE, "w") as f:
        json.dump(data, f)

SENT = load_sent()

# ======================
# HELPERS
# ======================

def valid_gpu(title):
    t = title.upper()
    return (
        "RTX" in t
        and ("40" in t or "50" in t)
        and "60" not in t
    )

def extract_model(title):
    for model in MSRP:
        if model in title:
            return model
    return None

def send_discord(store, model, price, link, test=False):
    delta = price - MSRP[model]
    sign = "+" if delta > 0 else ""

    header = "🧪 **TEST ALERT** 🧪\n\n" if test else "🔥 **GPU DEAL FOUND** 🔥\n\n"

    payload = {
        "content": (
            header +
            f"🎮 **{model}**\n"
            f"🏪 {store}\n"
            f"💵 **Price:** ${price}\n"
            f"💰 **MSRP:** ${MSRP[model]} ({sign}{delta}$)\n"
            f"🔗 {link}"
        )
    }

    requests.post(DISCORD_WEBHOOK, json=payload)

# ======================
# TEST MODE
# ======================

def run_test():
    print("🧪 TEST MODE ENABLED")

    for fn in [
        check_bestbuy,
        check_amazon,
        check_newegg,
        check_microcenter_tustin
    ]:
        fn(test=True)

# ======================
# STORE CHECKERS
# ======================

def check_bestbuy(test=False):
    print("🟦 Checking Best Buy")
    url = "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+graphics+card"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select(".sku-item"):
        title_el = item.select_one(".sku-title")
        price_el = item.select_one(".priceView-customer-price span")

        if not title_el or not price_el:
            continue

        title = title_el.text.strip()
        if not valid_gpu(title):
            continue

        model = extract_model(title)
        if not model:
            continue

        price = int(price_el.text.replace("$", "").replace(",", ""))
        link = "https://www.bestbuy.com" + title_el.a["href"]
        key = f"BestBuy|{model}"

        if (price <= MSRP[model] or test) and key not in SENT:
            send_discord("🟦 Best Buy", model, price, link, test)
            SENT.append(key)
            save_sent(SENT)

def check_amazon(test=False):
    print("🟧 Checking Amazon")
    url = "https://www.amazon.com/s?k=rtx+graphics+card"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select("div[data-component-type='s-search-result']"):
        title_el = item.select_one("h2 span")
        price_whole = item.select_one(".a-price-whole")

        if not title_el or not price_whole:
            continue

        title = title_el.text.strip()
        if not valid_gpu(title):
            continue

        model = extract_model(title)
        if not model:
            continue

        try:
            price = int(price_whole.text.replace(",", "").replace(".", ""))
        except:
            continue

        link = "https://www.amazon.com" + item.select_one("h2 a")["href"]
        key = f"Amazon|{model}"

        if (price <= MSRP[model] or test) and key not in SENT:
            send_discord("🟧 Amazon", model, price, link, test)
            SENT.append(key)
            save_sent(SENT)

def check_newegg(test=False):
    print("🟥 Checking Newegg")
    url = "https://www.newegg.com/p/pl?d=rtx+graphics+card"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select(".item-cell"):
        title_el = item.select_one(".item-title")
        price_el = item.select_one(".price-current strong")

        if not title_el or not price_el:
            continue

        title = title_el.text.strip()
        if not valid_gpu(title):
            continue

        model = extract_model(title)
        if not model:
            continue

        price = int(price_el.text.replace(",", ""))
        link = title_el["href"]
        key = f"Newegg|{model}"

        if (price <= MSRP[model] or test) and key not in SENT:
            send_discord("🟥 Newegg", model, price, link, test)
            SENT.append(key)
            save_sent(SENT)

def check_microcenter_tustin(test=False):
    print("🟩 Checking Micro Center (Tustin)")
    url = "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+gpu&storeid=101"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select(".product_wrapper"):
        title_el = item.select_one(".h2")
        price_el = item.select_one(".price")

        if not title_el or not price_el:
            continue

        title = title_el.text.strip()
        if not valid_gpu(title):
            continue

        model = extract_model(title)
        if not model:
            continue

        try:
            price = int(price_el.text.replace("$", "").replace(",", ""))
        except:
            continue

        link = "https://www.microcenter.com" + title_el.a["href"]
        key = f"MicroCenter|{model}"

        if (price <= MSRP[model] or test) and key not in SENT:
            send_discord("🟩 Micro Center (Tustin, CA)", model, price, link, test)
            SENT.append(key)
            save_sent(SENT)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    print(f"⏰ Run started at {datetime.utcnow()} UTC")

    if TEST_MODE:
        run_test()
    else:
        check_bestbuy()
        check_amazon()
        check_newegg()
        check_microcenter_tustin()
