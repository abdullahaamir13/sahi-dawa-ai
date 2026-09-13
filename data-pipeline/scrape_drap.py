"""
Sahi Dawa - DRAP Price Scraper using Playwright (v2 - Esha's list merged in)
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re
from datetime import datetime

# ====================== CONFIG ======================
BASE_URL = "https://e.dra.gov.pk/public/price"
OUTPUT_FILE = "medicines_drap_playwright_v2.csv"

# Original 12 + everything (generics + specific brand names)
SEARCH_TERMS = [
    # --- Original batch ---
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Metronidazole",
    "Paracetamol", "Ibuprofen", "Cefixime", "Ceftriaxone",
    "Clarithromycin", "Levofloxacin", "Omeprazole", "Esomeprazole",

    # --- generics ---
    "Aspirin", "Nimesulide", "Methotrexate", "Ondansetron",
    "Fluconazole", "Cefotaxime", "Amikacin", "Clopidogrel",
    "Ranitidine", "Fexofenadine", "Moxifloxacin", "Telmisartan",
    "Salbutamol", "Simvastatin",

    # --- Specific brand names ---
    "Grasil", "Emesson", "Gamet", "Ventolin", "Claritec", "Sim-stat", "Jardy",
    "Uneek", "Titan", "Novosef", "Cefinig", "Traxon", "Fortexone",
    "Moxiget", "Megamox", "Avelox",
    "Azilla", "Azeloc", "Lazio", "Zetro",
    "Xempra", "Megazole",
    "Cefiget",
    "Cipvax", "Evosin", "Ciprosafe", "Excipro", "Cithrox", "Savoxacin",
    "Telsartan",
]

DELAY = 2.5

# ====================== HELPERS ======================
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_price(price_text):
    if not price_text:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_text.replace(',', ''))
    try:
        return float(cleaned)
    except:
        return None

# ====================== MAIN SCRAPER ======================
def scrape_drap():
    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("="*60)
        print("Sahi Dawa - DRAP Scraper v2 (Esha's list merged)")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total search terms: {len(SEARCH_TERMS)}")
        print("="*60)

        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        for term in SEARCH_TERMS:
            print(f"\nSearching: {term}")
            try:
                search_input = page.locator('input[type="text"]').first
                search_input.fill("")
                search_input.fill(term)
                time.sleep(0.5)

                search_btn = page.locator('button:has-text("Search")').first
                search_btn.click()
                time.sleep(DELAY)

                page.wait_for_selector('tr.hover\\:bg-emerald-50, tr[class*="hover"]', timeout=10000)
                rows = page.locator('tr.hover\\:bg-emerald-50, tr[class*="hover"]').all()
                print(f"   Found {len(rows)} rows")

                for row in rows[:25]:
                    try:
                        cells = row.locator('td').all()
                        if len(cells) < 6:
                            continue

                        name = clean_text(cells[0].inner_text())
                        reg_number = clean_text(cells[1].inner_text())
                        manufacturer = clean_text(cells[2].inner_text())
                        category = clean_text(cells[3].inner_text())
                        pack_size = clean_text(cells[4].inner_text())
                        price_text = clean_text(cells[5].inner_text())
                        effective_date = clean_text(cells[6].inner_text()) if len(cells) > 6 else ""
                        price = extract_price(price_text)

                        if name and reg_number:
                            all_data.append({
                                "search_term": term,
                                "product_name": name,
                                "registration_number": reg_number,
                                "manufacturer": manufacturer,
                                "category": category,
                                "pack_size": pack_size,
                                "price": price,
                                "price_text": price_text,
                                "effective_from": effective_date,
                                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "source": "https://e.dra.gov.pk/public/price"
                            })
                    except Exception:
                        continue

                print(f"   Extracted records for {term}")

            except Exception as e:
                print(f"   No results / error on '{term}': {e}")

            time.sleep(DELAY)

        browser.close()

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(OUTPUT_FILE, index=False)
        print("\n" + "="*60)
        print(f"Total records extracted: {len(df)}")
        print(f"Saved to: {OUTPUT_FILE}")
        print("="*60)
    else:
        print("\nNo data extracted.")

if __name__ == "__main__":
    scrape_drap()
