import requests
import os
import json
from bs4 import BeautifulSoup

# ======================
# SETTINGS
# ======================

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

ROLE_PING = ""  # Example: "<@&123456789012345678>" or leave blank
TEST_MODE = False  # 🔴 SET TRUE TO FORCE A TEST ALERT

HEADERS = {"User-Agent": "Mozilla/5.0"}
DATA_FILE = "sent_deals.json"

# ======================
# STORES (Name + Emoji)
# ======================

STORES = {
    "Amazon": "🟧 Amazon",
    "Newegg": "🟥 Newegg",
    "Best Buy": "🟦 Best Buy",
    "Micro Center": "🟩 Micro Center"
}

# ======================
# NVIDIA MSRP (USD)
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
# STATE TRACKING
# ======================

def load_sent():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

SENT = load_sent()

def already_sent(store, model):
    key = f"{store}-{model}"
    if key in SENT:
        return True
    SENT.append(key)
    save_sent(SENT)
    return False

# ======================
# DISCORD
# ======================

def send_discord(model, price, store, link):
    msrp = MSRP[model]
    delta = price - msrp
    sign = "+" if delta > 0 else ""

    message = {
        "content": (
            f"{ROLE_PING}\n"
            "🔥 **GPU DEAL FOUND** 🔥\n\n"
            f"🎮 **{model}**\n"
            f"🏪 {STORES[store]}\n"
            f"💵 **Price:** ${price}\n"
            f"💰 **MSRP:** ${msrp} ({sign}{delta}$)\n"
            f"🔗 {link}"
        )
    }

    requests.post(WEBHOOK, json=message)

# ======================
# FILTERING
# ======================

def valid_gpu(title):
    t = title.upper()
    return (
        "RTX" in t
        and ("RTX 40" in t or "RTX 50" in t)
        and "60" not in t
    )

def get_model(title):
    for model in MSRP:
        if model in title:
            return model
    return None

# ======================
# HTTP SESSION (OPTIMIZATION)
# ======================

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ======================
# STORES
# ======================

def check_newegg():
    soup = BeautifulSoup(
        SESSION.get("https://www.newegg.com/p/pl?d=rtx+gpu", timeout=10).text,
        "html.parser"
    )

    for item in soup.select(".item-cell"):
        title = item.select_one(".item-title")
        price = item.select_one(".price-current strong")
        if not title or not price:
            continue

        name = title.text.strip()
        if not valid_gpu(name):
            continue

        model = get_model(name)
        if not model:
            continue

        price = int(price.text.replace(",", ""))
        if price <= MSRP[model] and not already_sent("Newegg", model):
            send_discord(model, price, "Newegg", title["href"])

def check_bestbuy():
    soup = BeautifulSoup(
        SESSION.get("https://www.bestbuy.com/site/searchpage.jsp?st=rtx+gpu", timeout=10).text,
        "html.parser"
    )

    for item in soup.select(".sku-item"):
        title = item.select_one(".sku-title a")
        price = item.select_one(".priceView-customer-price span")
        if not title or not price:
            continue

        name = title.text.strip()
        if not valid_gpu(name):
            continue

        model = get_model(name)
        if not model:
            continue

        price = int(price.text.replace("$", "").replace(",", ""))
        link = "https://www.bestbuy.com" + title["href"]

        if price <= MSRP[model] and not already_sent("Best Buy", model):
            send_discord(model, price, "Best Buy", link)

def check_amazon():
    soup = BeautifulSoup(
        SESSION.get("https://www.amazon.com/s?k=rtx+gpu", timeout=10).text,
        "html.parser"
    )

    for item in soup.select(".s-result-item"):
        title = item.select_one("h2 span")
        price = item.select_one(".a-price-whole")
        link = item.select_one("h2 a")
        if not title or not price or not link:
            continue

        name = title.text.strip()
        if not valid_gpu(name):
            continue

        model = get_model(name)
        if not model:
            continue

        price = int(price.text.replace(",", ""))
        link = "https://www.amazon.com" + link["href"]

        if price <= MSRP[model] and not already_sent("Amazon", model):
            send_discord(model, price, "Amazon", link)

def check_microcenter():
    soup = BeautifulSoup(
        SESSION.get("https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+gpu", timeout=10).text,
        "html.parser"
    )

    for item in soup.select(".product_wrapper"):
        title = item.select_one(".h2")
        price = item.select_one(".price")
        if not title or not price:
            continue

        name = title.text.strip()
        if not valid_gpu(name):
            continue

        model = get_model(name)
        if not model:
            continue

        price = int(price.text.replace("$", "").replace(",", ""))
        link = "https://www.microcenter.com" + title.find("a")["href"]

        if price <= MSRP[model] and not already_sent("Micro Center", model):
            send_discord(model, price, "Micro Center", link)

# ======================
# TEST MODE
# ======================

def run_test():
    send_discord(
        "RTX 4090",
        1399,
        "Amazon",
        "https://example.com"
    )

# ======================
# RUN
# ======================

if __name__ == "__main__":
    if TEST_MODE:
        run_test()
    else:
        check_newegg()
        check_bestbuy()
        check_amazon()
        check_microcenter()
