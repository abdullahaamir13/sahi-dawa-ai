"""
Sahi Dawa: Final Trim & Fix Pass
Fixes: duplicates, broken brand names, oversized dataset
Run this on medicines_final.csv to produce medicines_v3.csv
"""

import pandas as pd
import re

INPUT_FILE = "medicines_final.csv"
OUTPUT_FILE = "medicines_v3.csv"
MAX_PER_INGREDIENT = 10   # cap brands per active ingredient 

def clean_brand(row):
    brand = str(row["brand_name"])
    active = str(row["active_ingredient"])

    # Case: manufacturer name leaked into brand field (contains "Pvt", "Ltd", "Pharmaceuticals")
    if re.search(r'\b(Pvt|Ltd|Pharmaceuticals|Laboratories)\b', brand, re.IGNORECASE):
        return None

    # Case: brand duplicates the active ingredient name awkwardly, e.g. "PARACETAMOL Paracetamol"
    brand = re.sub(rf'\b{re.escape(active)}\b', '', brand, flags=re.IGNORECASE).strip()
    brand = re.sub(r'[\(\)•,\.]+$', '', brand).strip()   # trailing junk chars
    brand = re.sub(r'\s+', ' ', brand).strip()

    # Case: truncated/garbled entries with stray parentheses and no real name left
    if len(brand) < 3 or brand.count('(') != brand.count(')'):
        return None

    return brand[:50]

def main():
    df = pd.read_csv(INPUT_FILE)
    print(f"Starting: {len(df)} records")

    # 1. Real dedupe, normalize whitespace/case in key columns first
    df["registration_number"] = df["registration_number"].astype(str).str.strip()
    df["pack_size"] = df["pack_size"].astype(str).str.strip().str.replace("’", "'")
    before = len(df)
    df = df.drop_duplicates(subset=["registration_number", "pack_size"], keep="first")
    print(f"After dedupe: {len(df)} (removed {before - len(df)})")

    # 2. Fix / drop broken brand names
    df["brand_name_clean"] = df.apply(clean_brand, axis=1)
    dropped = df["brand_name_clean"].isna().sum()
    df = df.dropna(subset=["brand_name_clean"])
    df["brand_name"] = df["brand_name_clean"]
    df = df.drop(columns=["brand_name_clean"])
    print(f"After dropping unrecoverable brand names: {len(df)} (removed {dropped})")

    # 3. Cap records per active ingredient, keep cheapest + most expensive + up to MAX_PER_INGREDIENT
    #    (keeps real price spread for the comparison feature, trims noise)
    def trim_group(g):
        if len(g) <= MAX_PER_INGREDIENT:
            return g
        g = g.sort_values("price")
        # keep lowest, highest, and evenly spaced middle entries
        idx = pd.Series(range(len(g)))
        keep_positions = sorted(set([0, len(g)-1] + list(idx[::max(1, len(g)//MAX_PER_INGREDIENT)])))
        return g.iloc[keep_positions[:MAX_PER_INGREDIENT]]

    df = df.groupby("active_ingredient", group_keys=False).apply(trim_group)
    print(f"After capping at {MAX_PER_INGREDIENT} brands/ingredient: {len(df)}")

    # 4. Reassign clean sequential IDs
    df = df.sort_values(["active_ingredient", "strength"]).reset_index(drop=True)
    df["medicine_id"] = [f"MED{str(i+1).zfill(3)}" for i in range(len(df))]

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n Final: {len(df)} records -> {OUTPUT_FILE}")
    print("\nCategory breakdown:")
    print(df["medicine_category"].value_counts())
    print("\nCoverage per active ingredient:")
    print(df["active_ingredient"].value_counts())

if __name__ == "__main__":
    main()
