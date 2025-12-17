import requests
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======================
# CONFIG
# ======================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

TIMEOUT = 8
SENT_FILE = "sent_gpu_deals.json"
TEST_MODE = False  # set True to test Discord

# ======================
# HTTP SESSION (FAST + SAFE)
# ======================

session = requests.Session()
retries = Retry(
    total=2,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)

# ======================
# STORES
# ======================

STORES = [
    {
        "name": "🟦 Best Buy",
        "url": "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+graphics+card"
    },
    {
        "name": "🟧 Amazon",
        "url": "https://www.amazon.com/s?k=rtx+graphics+card"
    },
    {
        "name": "🟥 Newegg",
        "url": "https://www.newegg.com/p/pl?d=rtx+graphics+card"
    },
    {
        "name": "🟩 Micro Center (Tustin)",
        "url": "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx&storeid=101"
    }
]

# ======================
# NVIDIA MSRP
# ======================

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
    "RTX 5090": 1599
}

# ======================
# STATE
# ======================

def load_sent():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_sent(data):
    with open(SENT_FILE, "w") as f:
        json.dump(list(data), f)

SENT = load_sent()

# ======================
# HELPERS
# ======================

def valid_gpu(title):
    t = title.upper()
    return (
        "RTX" in t
        and ("RTX 40" in t or "RTX 50" in t)
        and "60" not in t
    )

def extract_model(title):
    t = title.upper()
    for model in MSRP:
        if model in t:
            return model
    return None

def extract_price(text):
    for word in text.split():
        if word.startswith("$"):
            try:
                return int(word.replace("$", "").replace(",", ""))
            except:
                pass
    return None

def build_link(store_url, href):
    if not href or not isinstance(href, str):
        return None
    if href.startswith("http"):
        return href
    base = store_url.split("/")[0] + "//" + store_url.split("/")[2]
    return base + href

# ======================
# DISCORD
# ======================

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

    session.post(DISCORD_WEBHOOK, json=payload, timeout=5)

# ======================
# STORE CHECK
# ======================

def check_store(store):
    print(f"{store['name']} Checking")

    try:
        r = session.get(store["url"], headers=HEADERS, timeout=TIMEOUT)
    except Exception as e:
        print(f"⚠️ {store['name']} skipped: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("a"):
        title = a.get_text(strip=True)
        href = a.get("href")

        if not title or not href:
            continue
        if not valid_gpu(title):
            continue

        model = extract_model(title)
        if not model:
            continue

        price = extract_price(a.parent.get_text(" ", strip=True))
        if not price or price > MSRP[model]:
            continue

        link = build_link(store["url"], href)
        if not link:
            continue

        key = f"{store['name']}|{model}"
        if key in SENT:
            continue

        send_discord(store["name"], model, price, link)
        SENT.add(key)
        save_sent(SENT)

        print(f"✅ SENT: {model} @ ${price}")

# ======================
# TEST MODE
# ======================

def run_test():
    for store in STORES:
        send_discord(
            store=store["name"],
            model="RTX 4080 SUPER",
            price=999,
            link=store["url"],
            test=True
        )

# ======================
# RUN
# ======================

if __name__ == "__main__":
    print(f"⏰ Run started at {datetime.utcnow()} UTC")

    if TEST_MODE:
        run_test()
    else:
        for store in STORES:
            check_store(store)
