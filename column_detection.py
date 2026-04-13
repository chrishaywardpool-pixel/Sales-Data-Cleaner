import streamlit as st
import pandas as pd
from typing import Dict, Tuple, Optional, List

def detect_columns(columns: List[str], df: Optional[pd.DataFrame] = None) -> Tuple[Dict[str, Tuple[str, float]], Dict[str, float]]:
    """Auto-detect column mappings based on column names with confidence scores"""
    detected_mapping = {}
    confidence_scores = {}

    # Define expected output columns and their possible input names
    column_mappings = {
        "Date": ["date", "order date", "invoice date", "transaction date", "created date"],
        "Sold To": ["sold to", "customer", "customer name", "buyer", "client", "account", "account name"],
        "THD Y/N": ["thd", "thd y/n", "home depot", "hd", "depot"],
        "Distributor SKU Code": ["prelude code code", "item code", "sku", "product code", "distributor sku"],
        "Hayward SKU Code": ["prelude code manufacturer code", "manufacturer code", "mfg code", "manuf code", "hayward sku", "item number"],
        "SKU Name": ["description", "product name", "item name", "product description", "sku name", "prelude code mcp line"],
        "Volume": ["total qty sold", "qty", "quantity", "units", "units sold", "volume", "amount"],
        "Value": ["total sales value", "sales", "sales value", "revenue", "total value", "value", "amount"]
    }

    for output_col, possible_names in column_mappings.items():
        best_match = None
        best_confidence = 0.0

        for col in columns:
            col_lower = col.lower().strip()
            # Check for exact matches first
            if any(name.lower() == col_lower for name in possible_names):
                best_match = col
                best_confidence = 1.0
                break
            # Check for partial matches
            for name in possible_names:
                if name.lower() in col_lower:
                    # Calculate confidence based on how much of the column name matches
                    name_ratio = len(name) / len(col_lower) if col_lower else 0
                    confidence = min(name_ratio, 0.9)  # Cap at 90% for partial matches
                    if confidence > best_confidence:
                        best_match = col
                        best_confidence = confidence

        if best_match:
            detected_mapping[output_col] = (best_match, best_confidence)
            confidence_scores[output_col] = best_confidence

    return detected_mapping, confidence_scores

def get_user_column_mapping(available_columns: List[str], detected_mapping: Dict[str, Tuple[str, float]]) -> Dict[str, str]:
    """Allow user to manually adjust column mappings"""
    final_mapping = {}

    st.subheader("Manual Column Mapping")

    # Define expected output columns
    output_cols = ["Date", "Sold To", "THD Y/N", "Distributor SKU Code",
                   "Hayward SKU Code", "SKU Name", "Volume", "Value"]

    for output_col in output_cols:
        detected_info = detected_mapping.get(output_col)
        detected_col = detected_info[0] if detected_info else None
        confidence = detected_info[1] if detected_info else 0.0

        # Show confidence level
        if confidence >= 0.8:
            st.success(f"✅ {output_col}: High confidence match found")
        elif confidence >= 0.5:
            st.warning(f"⚠️ {output_col}: Medium confidence match found")
        else:
            st.error(f"❌ {output_col}: Low confidence - manual selection needed")

        selected_col = st.selectbox(
            f"Select column for {output_col}:",
            options=[None] + available_columns,
            index=available_columns.index(detected_col) + 1 if detected_col in available_columns else 0,
            key=f"map_{output_col}",
            help=f"Auto-detected: {detected_col or 'None'} ({confidence:.1%} confidence)"
        )

        if selected_col:
            final_mapping[output_col] = selected_col

    return final_mapping

def validate_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> Dict[str, str]:
    """Validate that mapped columns exist and contain appropriate data"""
    warnings = {}

    # Check if columns exist
    for output_col, input_col in mapping.items():
        if input_col not in df.columns:
            warnings[output_col] = f"Column '{input_col}' not found in data"

    # Validate data types for critical columns
    if "Volume" in mapping and mapping["Volume"] in df.columns:
        sample_values = df[mapping["Volume"]].dropna().head(10)
        try:
            numeric_values = pd.to_numeric(sample_values, errors='coerce').dropna()
            if len(numeric_values) == 0:
                warnings["Volume"] = "Volume column contains no numeric values"
        except:
            warnings["Volume"] = "Volume column validation failed"

    if "Value" in mapping and mapping["Value"] in df.columns:
        sample_values = df[mapping["Value"]].dropna().head(10)
        try:
            # Remove commas and try to convert
            cleaned_values = sample_values.astype(str).str.replace(',', '', regex=False)
            numeric_values = pd.to_numeric(cleaned_values, errors='coerce').dropna()
            if len(numeric_values) == 0:
                warnings["Value"] = "Value column contains no numeric values"
        except:
            warnings["Value"] = "Value column validation failed"

    return warnings