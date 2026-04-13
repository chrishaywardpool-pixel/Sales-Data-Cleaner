import pandas as pd
import re
from typing import List, Set, Optional, Union
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not available, fuzzy matching disabled")

def load_sku_list(file_path: str) -> List[str]:
    """Load SKU list from CSV file"""
    try:
        df = pd.read_csv(file_path)
        # Assume SKUs are in the first column
        skus = df.iloc[:, 0].astype(str).str.strip().tolist()
        return [sku for sku in skus if sku]  # Remove empty strings
    except Exception as e:
        raise ValueError(f"Error loading SKU list: {str(e)}")

def normalize_sku(sku: str) -> str:
    """Normalize SKU: lowercase, remove dashes, spaces, non-alphanumeric"""
    if not sku or pd.isna(sku):
        return ""
    # Convert to string, lowercase, remove dashes and spaces, keep only alphanumeric
    normalized = str(sku).lower()
    normalized = re.sub(r'[-_\s]', '', normalized)
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    return normalized

def fuzzy_match_sku(normalized_input: str, normalized_sku_list: List[str], threshold: float = 85) -> bool:
    """Fuzzy match using rapidfuzz"""
    if not RAPIDFUZZ_AVAILABLE:
        return False
    for sku in normalized_sku_list:
        if fuzz.ratio(normalized_input, sku) >= threshold:
            return True
    return False

def filter_by_sku(df: pd.DataFrame, sku_list: List[str], raw_df: Optional[pd.DataFrame] = None, raw_column_mapping: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Filter DataFrame rows where Prelude Code Manufacturer Code matches SKU list"""
    if not sku_list:
        return df

    # Pre-normalize SKU list
    normalized_sku_set = set(normalize_sku(sku) for sku in sku_list)
    normalized_sku_list = list(normalized_sku_set)

    total_rows = len(df)
    matched_rows = 0
    dropped_missing = 0
    unmatched_samples = []

    def row_matches(row):
        nonlocal matched_rows, dropped_missing, unmatched_samples

        # Get raw Manufacturer Code
        manufacturer_code = None
        if raw_df is not None and raw_column_mapping is not None:
            hayward_mapping = raw_column_mapping.get("Hayward SKU Code")
            if hayward_mapping and hayward_mapping in raw_df.columns and row.name in raw_df.index:
                manufacturer_code = raw_df.loc[row.name, hayward_mapping]

        if pd.isna(manufacturer_code) or not str(manufacturer_code).strip():
            dropped_missing += 1
            return False

        normalized_code = normalize_sku(manufacturer_code)

        # Exact match
        if normalized_code in normalized_sku_set:
            matched_rows += 1
            return True

        # Fuzzy match
        if fuzzy_match_sku(normalized_code, normalized_sku_list, 85):
            matched_rows += 1
            return True

        # Unmatched
        if len(unmatched_samples) < 10:
            unmatched_samples.append(str(manufacturer_code))
        return False

    mask = df.apply(row_matches, axis=1)
    filtered_df = df[mask].copy()

    # Debug output
    print(f"SKU Matching Results:")
    print(f"  Total rows processed: {total_rows}")
    print(f"  Rows matched: {matched_rows}")
    print(f"  Rows dropped (missing SKU): {dropped_missing}")
    print(f"  Rows dropped (no match): {total_rows - matched_rows - dropped_missing}")
    if unmatched_samples:
        print(f"  Sample unmatched Manufacturer Codes: {unmatched_samples}")

    return filtered_df

def find_sku_column(df: pd.DataFrame) -> Optional[str]:
    """Find the most likely SKU column in the DataFrame"""
    sku_keywords = ['sku', 'item code', 'product code', 'prelude code code', 'distributor sku']

    for col in df.columns:
        col_lower = col.lower()
        for keyword in sku_keywords:
            if keyword in col_lower:
                return col

    # If no keyword match, look for columns with many unique values (likely SKUs)
    for col in df.columns:
        if df[col].nunique() > len(df) * 0.1:  # At least 10% unique values
            return col

    return None