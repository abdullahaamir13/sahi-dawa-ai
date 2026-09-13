"""
Sahi Dawa: Clean + Merge DRAP Data (v2)
Combines the new v2 scrape with your existing medicines.csv into one final file.
"""

import pandas as pd
import re
from datetime import datetime

# ====================== CONFIG ======================
NEW_SCRAPE_FILE = "medicines_drap_playwright_v2.csv"
EXISTING_CSV = "medicines.csv"          # your current 32-record file
OUTPUT_FILE = "medicines_final.csv"     # final merged output

# ====================== HELPERS ======================
def clean_text(text):
    if pd.isna(text):
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def extract_strength(name):
    patterns = [
        r'(\d+\s*mg(?:/\d+\s*ml)?)',
        r'(\d+\s*g)',
        r'(\d+\s*mcg)',
        r'(\d+\s*IU)',
    ]
    for pat in patterns:
        match = re.search(pat, name, re.IGNORECASE)
        if match:
            return match.group(1).replace(" ", "")
    return ""

def detect_dosage_form(name):
    n = name.lower()
    if "capsule" in n: return "Capsule"
    if "tablet" in n or "tab" in n: return "Tablet"
    if "suspension" in n or "syrup" in n: return "Suspension"
    if "injection" in n or "inj" in n: return "Injection"
    if "sachet" in n: return "Sachet"
    if "inhaler" in n: return "Inhaler"
    if "cream" in n or "ointment" in n: return "Topical"
    return "Other"

# Maps EVERY search term (generic AND brand names Esha gave) -> correct active ingredient
SEARCH_TERM_TO_ACTIVE = {
    "Amoxicillin": "Amoxicillin",
    "Azithromycin": "Azithromycin", "Azilla": "Azithromycin", "Azeloc": "Azithromycin",
    "Lazio": "Azithromycin", "Zetro": "Azithromycin",
    "Ciprofloxacin": "Ciprofloxacin", "Cipvax": "Ciprofloxacin", "Evosin": "Ciprofloxacin",
    "Ciprosafe": "Ciprofloxacin", "Excipro": "Ciprofloxacin", "Cithrox": "Ciprofloxacin",
    "Savoxacin": "Ciprofloxacin",
    "Metronidazole": "Metronidazole",
    "Paracetamol": "Paracetamol",
    "Ibuprofen": "Ibuprofen",
    "Cefixime": "Cefixime", "Cefiget": "Cefixime",
    "Ceftriaxone": "Ceftriaxone", "Uneek": "Ceftriaxone", "Titan": "Ceftriaxone",
    "Novosef": "Ceftriaxone", "Cefinig": "Ceftriaxone", "Traxon": "Ceftriaxone",
    "Fortexone": "Ceftriaxone",
    "Clarithromycin": "Clarithromycin",
    "Levofloxacin": "Levofloxacin",
    "Omeprazole": "Omeprazole", "Xempra": "Omeprazole", "Megazole": "Omeprazole",
    "Esomeprazole": "Esomeprazole",
    "Aspirin": "Aspirin",
    "Nimesulide": "Nimesulide",
    "Methotrexate": "Methotrexate",
    "Ondansetron": "Ondansetron", "Emesson": "Ondansetron",
    "Fluconazole": "Fluconazole",
    "Cefotaxime": "Cefotaxime",
    "Amikacin": "Amikacin", "Grasil": "Amikacin",
    "Clopidogrel": "Clopidogrel",
    "Ranitidine": "Ranitidine", "Gamet": "Ranitidine",
    "Fexofenadine": "Fexofenadine", "Claritec": "Fexofenadine",
    "Moxifloxacin": "Moxifloxacin", "Moxiget": "Moxifloxacin", "Megamox": "Moxifloxacin",
    "Avelox": "Moxifloxacin",
    "Telmisartan": "Telmisartan", "Telsartan": "Telmisartan",
    "Salbutamol": "Salbutamol", "Ventolin": "Salbutamol",
    "Simvastatin": "Simvastatin", "Sim-stat": "Simvastatin",
    "Jardy": "Dapagliflozin",
}

ANTIBIOTICS = [
    "Amoxicillin", "Azithromycin", "Ciprofloxacin", "Metronidazole",
    "Cefixime", "Ceftriaxone", "Clarithromycin", "Levofloxacin",
    "Cefotaxime", "Amikacin", "Moxifloxacin"
]

def is_antibiotic(active):
    return "Antibiotic" if active in ANTIBIOTICS else "Non-antibiotic"

def create_brand_name(product_name):
    brand = re.split(r'\d+\s*mg|\d+\s*g|Each|contains|Suspension|Capsule|Tablet',
                      product_name, flags=re.IGNORECASE)[0]
    brand = clean_text(brand)
    return brand[:60] if len(brand) >= 3 else product_name[:60]

def process_raw_scrape(df):
    """Turn a raw scrape dataframe into final-schema records."""
    records = []
    unmapped_terms = set()

    for _, row in df.iterrows():
        product_name = clean_text(row.get("product_name", ""))
        search_term = clean_text(row.get("search_term", ""))
        reg_number = clean_text(row.get("registration_number", ""))
        manufacturer = clean_text(row.get("manufacturer", "")).split("|")[0].strip()
        pack_size = clean_text(row.get("pack_size", ""))
        price = row.get("price")
        effective = clean_text(row.get("effective_from", ""))

        if not product_name or not reg_number:
            continue

        active = SEARCH_TERM_TO_ACTIVE.get(search_term)
        if active is None:
            active = search_term  # fallback: use term as-is
            unmapped_terms.add(search_term)

        records.append({
            "brand_name": create_brand_name(product_name),
            "generic_name": active,
            "active_ingredient": active,
            "strength": extract_strength(product_name),
            "dosage_form": detect_dosage_form(product_name),
            "pack_size": pack_size,
            "manufacturer": manufacturer,
            "price": price,
            "price_effective_date": effective,
            "registration_number": reg_number,
            "drap_source_url": "https://e.dra.gov.pk/public/price",
            "last_verified": datetime.now().strftime("%Y-%m-%d"),
            "data_status": "VERIFIED",
            "medicine_category": is_antibiotic(active),
        })

    return pd.DataFrame(records), unmapped_terms

def main():
    print("="*60)
    print("Sahi Dawa - Clean + Merge (v2)")
    print("="*60)

    # 1. Process the new v2 scrape
    new_raw = pd.read_csv(NEW_SCRAPE_FILE)
    print(f"New scrape loaded: {len(new_raw)} raw rows")
    new_clean, unmapped = process_raw_scrape(new_raw)
    print(f"New scrape cleaned: {len(new_clean)} records")
    if unmapped:
        print(f" Unmapped search terms (used as-is, review these): {unmapped}")

    # 2. Load existing medicines.csv (already-cleaned, has medicine_id — drop it, we'll reassign)
    try:
        existing = pd.read_csv(EXISTING_CSV)
        if "medicine_id" in existing.columns:
            existing = existing.drop(columns=["medicine_id"])
        print(f"Existing file loaded: {len(existing)} records")
    except FileNotFoundError:
        existing = pd.DataFrame(columns=new_clean.columns)
        print("No existing medicines.csv found — starting fresh")

    # 3. Combine + dedupe (same reg number + pack size = same product)
    combined = pd.concat([existing, new_clean], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["registration_number", "pack_size"], keep="first")
    print(f"Combined: {before} -> {len(combined)} after dedupe")

    # 4. Sort + reassign clean sequential IDs
    combined = combined.sort_values(by=["active_ingredient", "strength"]).reset_index(drop=True)
    combined.insert(0, "medicine_id", [f"MED{str(i+1).zfill(3)}" for i in range(len(combined))])

    combined.to_csv(OUTPUT_FILE, index=False)

    print(f"\n Final merged records: {len(combined)}")
    print(f" Saved to: {OUTPUT_FILE}")
    print("\nCategory breakdown:")
    print(combined["medicine_category"].value_counts())
    print("\nActive ingredient coverage:")
    print(combined["active_ingredient"].value_counts())

if __name__ == "__main__":
    main()
