import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import re

def clean_data(df: pd.DataFrame, column_mapping: Dict[str, str], file_name: Optional[str] = None) -> pd.DataFrame:
    """Clean and standardize the data based on column mappings"""
    df_cleaned = df.copy()

    # Define output columns
    output_columns = ["Date", "Sold To", "THD Y/N", "Distributor SKU Code",
                     "Hayward SKU Code", "SKU Name", "Volume", "Value"]

    # First, remove obvious summary rows and blank rows
    df_cleaned = remove_summary_and_blank_rows(df_cleaned)

    # Remove duplicate rows
    initial_rows = len(df_cleaned)
    df_cleaned = df_cleaned.drop_duplicates()
    if len(df_cleaned) < initial_rows:
        print(f"Removed {initial_rows - len(df_cleaned)} duplicate rows")

    # Apply cleaning to each mapped column
    for output_col in output_columns:
        if output_col in column_mapping and column_mapping[output_col] in df_cleaned.columns:
            input_col = column_mapping[output_col]
            # Convert to string and clean
            df_cleaned[output_col] = df_cleaned[input_col].astype(str).str.strip()

            # Specific cleaning based on column type
            if output_col == "Volume":
                df_cleaned[output_col] = clean_volume_column(df_cleaned[output_col])
            elif output_col == "Value":
                df_cleaned[output_col] = clean_value_column(df_cleaned[output_col])
            elif output_col == "THD Y/N":
                df_cleaned[output_col] = clean_thd_column(df_cleaned[output_col])
            elif output_col == "Date":
                df_cleaned[output_col] = clean_date_column(df_cleaned[output_col])
            # For other columns, just keep the cleaned string
        else:
            # If column not mapped or not found, create empty column
            df_cleaned[output_col] = ""

    # If date is missing and file_name has month/year info, populate with month first day
    if file_name and "Date" in df_cleaned.columns:
        if df_cleaned["Date"].replace("", pd.NA).isna().all():
            inferred_date = extract_date_from_filename(file_name)
            if inferred_date is not None:
                df_cleaned["Date"] = inferred_date

    # Reorder columns to match the required output format
    df_cleaned = df_cleaned[output_columns]

    return df_cleaned

def remove_summary_and_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove summary rows and completely blank rows"""
    initial_rows = len(df)

    # Remove rows where most columns are empty (likely summary rows)
    non_empty_counts = df.notna().sum(axis=1)
    avg_non_empty = non_empty_counts.mean()

    # Keep rows with at least 30% of columns having data
    min_required = max(2, int(len(df.columns) * 0.3))  # At least 2 columns or 30%
    df = df[non_empty_counts >= min_required]

    # Remove completely blank rows
    df = df.dropna(how='all')

    removed_rows = initial_rows - len(df)
    if removed_rows > 0:
        print(f"Removed {removed_rows} summary/blank rows")

    return df

def clean_volume_column(series: pd.Series) -> pd.Series:
    """Clean volume column - should be integers"""
    # Convert to string first, then clean
    cleaned = series.astype(str).str.strip()

    # Remove commas and other non-numeric characters except decimal point
    cleaned = cleaned.str.replace(r'[^\d.-]', '', regex=True)

    # Convert to numeric, then to integers
    numeric = pd.to_numeric(cleaned, errors='coerce')
    integers = numeric.astype('Int64')  # Nullable integer type

    return integers

def clean_value_column(series: pd.Series) -> pd.Series:
    """Clean value column - should be floats, handle currency and formatting"""
    # Convert to string first, then clean
    cleaned = series.astype(str).str.strip()

    # Remove any non-numeric characters except decimal points and minus signs
    cleaned = cleaned.str.replace(r'[^\d.-]', '', regex=True)

    # Convert to numeric (floats) with coercion for invalid values
    numeric = pd.to_numeric(cleaned, errors='coerce')

    return numeric

def clean_thd_column(series: pd.Series) -> pd.Series:
    """Clean THD Y/N column - standardize to Y/N"""
    cleaned = series.astype(str).str.strip().str.upper()

    # Map various representations to Y/N
    mappings = {
        'YES': 'Y', 'Y': 'Y', 'TRUE': 'Y', '1': 'Y',
        'NO': 'N', 'N': 'N', 'FALSE': 'N', '0': 'N'
    }

    cleaned = cleaned.replace(mappings)

    # Anything not Y/N becomes blank
    cleaned = cleaned.where(cleaned.isin(['Y', 'N']), "")

    return cleaned

def clean_date_column(series: pd.Series) -> pd.Series:
    """Clean date column - standardize to YYYY-MM-DD format"""
    # Try to parse dates
    dates = pd.to_datetime(series, errors='coerce')

    # Format as string in YYYY-MM-DD format, keep NaT as empty string
    formatted = dates.dt.strftime('%Y-%m-%d').fillna("")

    return formatted

def extract_date_from_filename(file_name: str) -> Optional[str]:
    """Extract month/year from filename and return YYYY-MM-01"""
    import re

    file_lower = file_name.lower()

    month_map = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }

    month = None
    year = None

    month_match = re.search(r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)', file_lower)
    if month_match:
        month = month_map.get(month_match.group(1))

    year_match = re.search(r'(20\d{2})', file_lower)
    if year_match:
        year = int(year_match.group(1))

    if not month:
        # try numeric month like _03, -03, 03
        month_match = re.search(r'[^\d](0?[1-9]|1[0-2])[^\d]', f" {file_lower} ")
        if month_match:
            month = int(month_match.group(1))

    if not year:
        # fallback to current year if none found
        year = pd.Timestamp.now().year

    if month and year:
        return f"{year:04d}-{month:02d}-01"

    return None

def validate_data_quality(df: pd.DataFrame) -> Dict[str, str]:
    """Validate data quality and return warnings"""
    warnings = {}

    # Check for missing critical data
    if "Distributor SKU Code" in df.columns:
        missing_skus = df["Distributor SKU Code"].isna().sum()
        if missing_skus > 0:
            warnings["SKU"] = f"{missing_skus} rows missing SKU codes"

    if "Volume" in df.columns:
        missing_volume = df["Volume"].isna().sum()
        if missing_volume > 0:
            warnings["Volume"] = f"{missing_volume} rows missing volume data"

    if "Value" in df.columns:
        missing_value = df["Value"].isna().sum()
        if missing_value > 0:
            warnings["Value"] = f"{missing_value} rows missing value data"

    # Check data types
    if "Volume" in df.columns and df["Volume"].dtype != 'Int64':
        non_integer_volume = df["Volume"].notna() & (df["Volume"] % 1 != 0)
        if non_integer_volume.any():
            warnings["Volume Type"] = "Volume column contains non-integer values"

    return warnings