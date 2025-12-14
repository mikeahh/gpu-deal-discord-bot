import requests, os, json, re
from bs4 import BeautifulSoup

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

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
HEADERS = {"User-Agent": "Mozilla/5.0"}

DATA_FILE = "sent_deals.json"

VALID_GPUS = {
    "RTX 4070": 700,
    "RTX 4070 SUPER": 750,
    "RTX 4080": 1100,
    "RTX 4080 SUPER": 1150,
    "RTX 4090": 1600,
    "RTX 5070": 9999,
    "RTX 5080": 9999,
    "RTX 5090": 9999
}

EXCLUDED = ["4060", "4060 TI"]

def load_sent():
    if not os.path.exists(DATA_FILE):
        return set()
    with open(DATA_FILE) as f:
        return set(json.load(f))

def save_sent(sent):
    with open(DATA_FILE, "w") as f:
        json.dump(list(sent), f)

def parse_price(text):
    nums = re.findall(r"\d+", text.replace(",", ""))
    return int(nums[0]) if nums else None

def send_discord(name, price, store, link):
    msrp = MSRP.get(name, "Unknown")
    diff = ""
    if isinstance(msrp, int):
        diff = f"\n💰 **MSRP:** ${msrp} ({price - msrp:+}$)"

    message = {
        "content": (
            f"🔥 **GPU DEAL FOUND** 🔥\n"
            f"**{name}**\n"
            f"🏪 {store}\n"
            f"💵 **Price:** ${price}{diff}\n"
            f"🔗 {link}"
        )
    }

    requests.post(WEBHOOK, json=message)

def check_newegg(sent):
    url = "https://www.newegg.com/p/pl?d=rtx+graphics+card"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select(".item-cell"):
        title = item.select_one(".item-title")
        price = item.select_one(".price-current")

        if not title or not price:
            continue

        name = title.text.upper()
        link = title["href"]

        if link in sent or any(x in name for x in EXCLUDED):
            continue

        for gpu, limit in VALID_GPUS.items():
            if gpu in name:
                p = parse_price(price.text)
                if p and p <= limit:
                    send_discord(name, p, "Newegg", link)
                    sent.add(link)

def check_bestbuy(sent):
    url = "https://www.bestbuy.com/site/searchpage.jsp?st=rtx+graphics+card"
    soup = BeautifulSoup(requests.get(url, headers=HEADERS).text, "html.parser")

    for item in soup.select(".sku-item"):
        title = item.select_one(".sku-title a")
        price = item.select_one(".priceView-customer-price span")

        if not title or not price:
            continue

        name = title.text.upper()
        link = "https://www.bestbuy.com" + title["href"]

        if link in sent or any(x in name for x in EXCLUDED):
            continue

        for gpu, limit in VALID_GPUS.items():
            if gpu in name:
                p = parse_price(price.text)
                if p and p <= limit:
                    send_discord(name, p, "Best Buy", link)
                    sent.add(link)

def check_amazon():
    url = "https://www.amazon.com/s?k=rtx+gpu"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select(".s-result-item"):
        title = item.select_one("h2 span")
        price_whole = item.select_one(".a-price-whole")
        price_frac = item.select_one(".a-price-fraction")
        link = item.select_one("h2 a")

        if not title or not price_whole or not link:
            continue

        name = title.text.strip()

        # Filter NVIDIA 40/50 series but exclude 60/60 Ti
        if not any(x in name for x in ["RTX 40", "RTX 50"]):
            continue
        if "60" in name:
            continue

        try:
            price = int(price_whole.text.replace(",", ""))
        except:
            continue

        full_link = "https://www.amazon.com" + link["href"]

        for model in MSRP:
            if model in name and price <= MSRP[model]:
                send_discord(model, price, "Amazon", full_link)

if __name__ == "__main__":
    sent = load_sent()
    check_newegg(sent)
    check_bestbuy(sent)
    check_amazon(sent)
    save_sent(sent)

send_discord("TEST GPU 4090", 999, "Test Store", "https://example.com")
