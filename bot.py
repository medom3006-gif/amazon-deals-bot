import os
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
HASDATA_API_KEY = os.environ["HASDATA_API_KEY"]
CHAT_ID = os.environ["CHAT_ID"]

SEARCH_TERMS = ["iphone", "samsung", "adidas", "nike", "laptop", "headphones"]
SENT_FILE = Path("sent_deals.json")


def load_sent():
    if SENT_FILE.exists():
        try:
            return json.loads(SENT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_sent(sent):
    SENT_FILE.write_text(
        json.dumps(sent, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def search_amazon(term):
    url = "https://api.hasdata.com/scrape/amazon/search"

    params = {
        "q": term,
        "domain": "www.amazon.eg",
        "language": "EN"
    }

    headers = {
        "x-api-key": HASDATA_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=120
    )

    response.raise_for_status()

    return response.json().get("productResults", [])


def send_telegram(product):
    message = f"""🔥🔥 عرض قوي على Amazon مصر

🛍️ {product['title']}

📉 الخصم: {product['discountPercent']}%
🏷️ السعر قبل: {product['originalPrice']} جنيه
💰 السعر الآن: {product['currentPrice']} جنيه

🔗 {product['url']}"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()


sent = load_sent()
found = {}

for term in SEARCH_TERMS:
    products = search_amazon(term)

    for product in products:
        price = product.get("price") or {}

        current = price.get("currentPrice")
        before = price.get("beforePrice")

        if current is None or before is None or before <= 0:
            continue

        discount = round((before - current) / before * 100)

        if discount < 50:
            continue

        key = product.get("asin") or product.get("url")

        if not key:
            continue

        found[key] = {
            "asin": product.get("asin"),
            "title": product.get("title"),
            "currentPrice": current,
            "originalPrice": before,
            "discountPercent": discount,
            "url": product.get("url")
        }


for key, product in found.items():

    deal_signature = (
        f"{key}|"
        f"{product['currentPrice']}|"
        f"{product['originalPrice']}"
    )

    if deal_signature in sent:
        continue

    send_telegram(product)

    sent[deal_signature] = {
        "title": product["title"],
        "sent_at": datetime.now(timezone.utc).isoformat()
    }


save_sent(sent)

print(f"تم فحص المنتجات. العروض الجديدة: {len(found)}")

# =========================
# NOON EGYPT
# =========================

def search_noon():
    url = "https://www.noon.com/egypt-en/"

    headers = {
        "x-api-key": HASDATA_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "url": url,
        "proxyCountry": "US",
        "proxyType": "datacenter",
        "jsRendering": True,
        "outputFormat": ["markdown", "json"],
        "aiExtractRules": {
            "products": {
                "type": "list",
                "description": "Extract products from this Noon Egypt page. For each product, extract the product title, current price, original price before discount, displayed discount percentage, and product URL.",
                "output": {
                    "title": {
                        "type": "string",
                        "description": "Full product title"
                    },
                    "currentPrice": {
                        "type": "number",
                        "description": "Current selling price"
                    },
                    "originalPrice": {
                        "type": "number",
                        "description": "Original price before discount"
                    },
                    "discountPercent": {
                        "type": "number",
                        "description": "Displayed discount percentage"
                    },
                    "url": {
                        "type": "string",
                        "description": "Product URL"
                    }
                }
            }
        }
    }

    response = requests.post(
        "https://api.hasdata.com/scrape/web",
        json=payload,
        headers=headers,
        timeout=180
    )

    print(response.status_code)
    print(response.text)

    data = response.json()
    return data.get("aiResponse", {}).get("products", [])


noon_products = search_noon()

for product in noon_products:

    current = product.get("currentPrice")
    original = product.get("originalPrice")

    if current is None or original is None or original <= 0:
        continue

    discount = round((original - current) / original * 100)

    if discount < 50:
        continue

    product["discountPercent"] = discount

    message = f"""🔥🔥 عرض قوي على Noon مصر

🛍️ {product.get('title', 'منتج')}

📉 الخصم: {discount}%
🏷️ السعر قبل: {original} جنيه
💰 السعر الآن: {current} جنيه

🔗 {product.get('url', '')}"""

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        telegram_url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

print(f"تم فحص Noon. المنتجات المستخرجة: {len(noon_products)}")
