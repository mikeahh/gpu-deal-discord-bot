import requests, os, json, re
from bs4 import BeautifulSoup

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
    data = {
        "embeds": [{
            "title": "🔥 GPU DEAL FOUND",
            "color": 5763719,
            "fields": [
                {"name": "GPU", "value": name, "inline": False},
                {"name": "Price", "value": f"${price}", "inline": True},
                {"name": "Store", "value": store, "inline": True},
                {"name": "Link", "value": link, "inline": False}
            ]
        }]
    }
    requests.post(WEBHOOK, json=data)

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

if __name__ == "__main__":
    sent = load_sent()
    check_newegg(sent)
    check_bestbuy(sent)
    save_sent(sent)

send_discord("TEST GPU 4090", 999, "Test Store", "https://example.com")
