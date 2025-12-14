import requests
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime

# ======================
# CONFIG
# ======================

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HEADERS = {"User-Agent": "Mozilla/5.0"}

TEST_MODE = True  # ← SET TO True TO SEND TEST ALERTS

SENT_FILE = "sent_deals.json"

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
        "name": "🟩 Micro Center (Tustin, CA)",
        "url": "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+gpu&storeid=101"
    }
]

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
        and ("RTX 40" in t or "RTX 50" in t)
        and "60" not in t
    )

def extract_model(title):
    for model in MSRP:
        if model in title:
            return model
    return None

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

    requests.post(DISCORD_WEBHOOK, json=payload)

# ======================
# TEST MODE
# ======================

def run_test():
    print("🧪 TEST MODE ENABLED — sending test alerts")

    for store in STORES:
        send_discord(
            store=store["name"],
            model="RTX 4080 SUPER",
            price=999,
            link=store["url"],
            test=True
        )

# ======================
# SCRAPER
# ======================

def scrape_store(store):
    print(f"[{datetime.utcnow()}] Checking {store['name']}")

    try:
        r = requests.get(store["url"], headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    found_any = False
    sent_any = False

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

        parent_text = a.parent.get_text(" ", strip=True)
        price = None

        for word in parent_text.split():
            if word.startswith("$"):
                try:
                    price = int(word.replace("$", "").replace(",", ""))
                    break
                except:
                    pass

        if not price:
            continue

        found_any = True

        link = href if href.startswith("http") else store["url"].split("/")[0] + "//" + store["url"].split("/")[2] + href
        key = f"{store['name']}|{model}"

        print(f"Found {model} at ${price}")

        if price <= MSRP[model] and key not in SENT:
            send_discord(store["name"], model, price, link)
            SENT.append(key)
            save_sent(SENT)
            sent_any = True
            print(f"✅ DEAL SENT for {model}")

    if not found_any:
        print("ℹ️ No qualifying GPUs found.")
    elif not sent_any:
        print("ℹ️ GPUs found, but no deals at or below MSRP.")

# ======================
# RUN
# ======================

if __name__ == "__main__":
    if TEST_MODE:
        run_test()
    else:
        for store in STORES:
            scrape_store(store)
