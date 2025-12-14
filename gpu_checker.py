import requests
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# CONFIG
# ======================

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HEADERS = {"User-Agent": "Mozilla/5.0"}

DATA_FILE = "sent_deals.json"
HISTORY_FILE = "price_history.json"

TEST_MODE = True  # set True to force a test alert

STORE_NAME = "🟩 Micro Center (Tustin, CA)"

# Micro Center Tustin store ID
# This URL is specific to Tustin pricing
MICROCENTER_URL = (
    "https://www.microcenter.com/search/search_results.aspx"
    "?Ntt=rtx+gpu&storeid=101"
)

# NVIDIA MSRP
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

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ======================
# STATE
# ======================

def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return []

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

SENT = load_json(DATA_FILE)

def already_sent(model):
    if model in SENT:
        return True
    SENT.append(model)
    save_json(DATA_FILE, SENT)
    return False

# ======================
# PRICE HISTORY
# ======================

def record_price(model, price, link):
    history = load_json(HISTORY_FILE)
    history.setdefault(model, []).append({
        "price": price,
        "link": link,
        "timestamp": datetime.utcnow().isoformat()
    })
    save_json(HISTORY_FILE, history)

# ======================
# DISCORD
# ======================

def send_discord(model, price, link):
    msrp = MSRP[model]
    delta = price - msrp
    sign = "+" if delta > 0 else ""

    message = {
        "content": (
            "🔥 **GPU DEAL FOUND** 🔥\n\n"
            f"🎮 **{model}**\n"
            f"🏪 {STORE_NAME}\n"
            f"💵 **Price:** ${price}\n"
            f"💰 **MSRP:** ${msrp} ({sign}{delta}$)\n"
            f"🔗 {link}"
        )
    }

    SESSION.post(WEBHOOK, json=message)

# ======================
# FILTERING
# ======================

def valid_gpu(title):
    t = title.upper()
    return (
        "RTX" in t and
        ("RTX 40" in t or "RTX 50" in t) and
        "60" not in t
    )

def get_model(title):
    for model in MSRP:
        if model in title:
            return model
    return None

# ======================
# SCRAPER (TUSTIN ONLY)
# ======================

def check_microcenter_tustin():
    soup = BeautifulSoup(
        SESSION.get(MICROCENTER_URL, timeout=10).text,
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

        try:
            price_val = int(price.text.replace("$", "").replace(",", ""))
        except:
            continue

        link = "https://www.microcenter.com" + title.find("a")["href"]

        record_price(model, price_val, link)

        if price_val <= MSRP[model] and not already_sent(model):
            send_discord(model, price_val, link)

# ======================
# TEST MODE
# ======================

def run_test():
    send_discord(
        "RTX 4090",
        1399,
        "https://www.microcenter.com"
    )

# ======================
# RUN
# ======================

if __name__ == "__main__":
    if TEST_MODE:
        run_test()
    else:
        check_microcenter_tustin()
