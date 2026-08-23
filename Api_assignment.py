import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests

# curl_cffi spoofs Chrome's TLS fingerprint automatically via `impersonate`
url = "https://www.jumia.co.ke/smartphones/"

try:
    response = requests.get(url, impersonate="chrome120", timeout=15)
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Request failed: {e}")
    exit()

soup = BeautifulSoup(response.content, "html.parser")

# Jumia product selectors
cards = soup.select("article.prd")

all_scraped_products = []

for card in cards[:10]:
    name_elem = card.select_one("h3.name, div.name")
    price_elem = card.select_one(".prc")

    if name_elem and price_elem:
        title = name_elem.text.strip()
        price_raw = price_elem.text.strip()

        # Extract only digits/decimals to handle "KSh 12,999"
        clean_price = "".join(c for c in price_raw if c.isdigit() or c == ".")

        if clean_price:
            all_scraped_products.append(
                {"title": title, "price_KES": float(clean_price)}
            )

if not all_scraped_products:
    print("Could not parse products. Checking alternative selectors...")
    # Secondary layout check for Jumia's dynamic grid
    cards = soup.find_all("a", class_="core")
    for card in cards[:10]:
        title = card.get("data-name") or (
            card.select_one(".name").text if card.select_one(".name") else None
        )
        price_raw = (
            card.select_one(".prc").text if card.select_one(".prc") else None
        )

        if title and price_raw:
            clean_price = "".join(
                c for c in price_raw if c.isdigit() or c == "."
            )
            if clean_price:
                all_scraped_products.append(
                    {"title": title.strip(), "price_KES": float(clean_price)}
                )

if not all_scraped_products:
    print("Scraping failed. Jumia rendered a CAPTCHA challenge page.")
    exit()

# Fetch Exchange Rate (KES to USD)
try:
    api_res = requests.get(
        "https://open.er-api.com/v6/latest/KES", timeout=10
    ).json()
    kes_to_usd = api_res["rates"]["USD"]
except Exception:
    kes_to_usd = 0.0077  # Fallback exchange rate

# Process Data
df = pd.DataFrame(all_scraped_products)
df["price_USD"] = (df["price_KES"] * kes_to_usd).round(2)

print("\n--- Scraped Jumia Products ---")
print(df.to_string(index=False))

df.to_csv("jumia_products.csv", index=False)
print("\nSaved output to 'jumia_products.csv'")