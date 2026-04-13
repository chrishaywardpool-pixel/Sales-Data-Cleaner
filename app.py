import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from cleaning import clean_data
from column_detection import detect_columns, get_user_column_mapping
from sku_matching import load_sku_list, filter_by_sku

# main.py

st.set_page_config(page_title="Sales Data Processor", layout="wide")

st.title("📊 Sales Data Processor")

# Initialize session state
if "sku_list" not in st.session_state:
    st.session_state.sku_list = None
if "column_mapping" not in st.session_state:
    st.session_state.column_mapping = None
if "cleaned_data" not in st.session_state:
    st.session_state.cleaned_data = None

# Sidebar for SKU list
with st.sidebar:
    st.header("⚙️ Configuration")
    sku_file = st.file_uploader("Upload SKU List (sku_list.csv)", type="csv", key="sku_upload")
    
    if sku_file:
        st.session_state.sku_list = load_sku_list(sku_file)
        st.success(f"✓ Loaded {len(st.session_state.sku_list)} SKUs")
    elif Path("sku_list.csv").exists():
        st.session_state.sku_list = load_sku_list("sku_list.csv")
        st.success(f"✓ Loaded {len(st.session_state.sku_list)} SKUs (from file)")
    else:
        st.warning("⚠️ No SKU list loaded")

# Main content
st.header("1️⃣ Upload Sales Data")
csv_file = st.file_uploader("Upload CSV file", type="csv", key="csv_upload")

if csv_file:
    df = pd.read_csv(csv_file)
    st.write(f"**Uploaded:** {csv_file.name} ({len(df)} rows)")
    
    with st.expander("Preview Raw Data"):
        st.dataframe(df.head(10))
    
    # Column detection
    st.header("2️⃣ Column Detection")
    
    detected_mapping, confidence_scores = detect_columns(df.columns.tolist())
    
    # Show confidence
    low_conf_cols = [col for col, conf in confidence_scores.items() if conf < 0.8]
    if low_conf_cols:
        st.warning(f"⚠️ Low confidence for: {', '.join(low_conf_cols)}")
    
    # Column mapping UI
    required_columns = ["Date", "Sold To", "THD Y/N", "Distributor SKU Code",
                        "Hayward SKU Code", "SKU Name", "Volume", "Value"]
    final_mapping = {}
    
    for output_col in required_columns:
        auto_value = detected_mapping.get(output_col, (None, 0.0))[0]
        auto_conf = detected_mapping.get(output_col, (None, 0.0))[1]
        
        st.write(f"**{output_col}**: auto-detected `{auto_value or 'None'}` (confidence {auto_conf:.0%})")
        
        if auto_conf < 0.8:
            st.warning(f"⚠️ Low confidence for '{output_col}', please choose manually")
        
        selected_col = st.selectbox(
            f"Map '{output_col}' to input column:",
            options=[None] + list(df.columns),
            index=(list(df.columns).index(auto_value) + 1) if auto_value in df.columns else 0,
            key=f"map_{output_col}"
        )
        
        if selected_col:
            final_mapping[output_col] = selected_col
    
    st.session_state.column_mapping = final_mapping
    
    # Data cleaning
    st.header("3️⃣ Clean & Filter Data")
    
    if st.button("Process Data", type="primary"):
        if not st.session_state.sku_list:
            st.error("❌ SKU list required. Load it from sidebar first.")
        else:
            # Clean data
            cleaned_df = clean_data(df, st.session_state.column_mapping, file_name=csv_file.name if csv_file else None)
            
            # Filter by SKU
            filtered_df = filter_by_sku(
                cleaned_df,
                st.session_state.sku_list,
                raw_df=df,
                raw_column_mapping=st.session_state.column_mapping
            )
            
            st.session_state.cleaned_data = filtered_df
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Rows Processed", len(df))
            with col2:
                st.metric("Rows Retained", len(filtered_df))
    
    # Preview cleaned data
    if st.session_state.cleaned_data is not None:
        st.header("4️⃣ Preview Cleaned Data")
        st.dataframe(st.session_state.cleaned_data)
        
        # Download section
        st.header("5️⃣ Download")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            output_name = st.text_input("Output filename", "cleaned_sales_data.csv")
        
        with col2:
            csv = st.session_state.cleaned_data.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=output_name if output_name.endswith(".csv") else f"{output_name}.csv",
                mime="text/csv"
            )