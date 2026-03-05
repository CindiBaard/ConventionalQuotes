import streamlit as st
import pandas as pd
import datetime
import os
from fpdf import FPDF
from pathlib import Path
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Artwork and Repro cost Estimate")

# GOOGLE SHEETS CONFIGURATION
SHEET_ID = "1zHOIawXjuufNYXymRxOWGghd6BQ8aXdZs7ve3P8fBYQ" 
DB_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DIRECTORY SETUP ---
DESKTOP_PATH = Path.home() / "Desktop" / "Conventional Quotes"
if not DESKTOP_PATH.exists():
    try:
        DESKTOP_PATH.mkdir(parents=True, exist_ok=True)
    except:
        pass

# UI Styling
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            [data-testid="stHeader"] { background: rgba(0,0,0,0); color: rgba(0,0,0,0); }
            .block-container { padding-top: 2rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem; }
            [data-testid="stMarkdownContainer"] p { margin-bottom: 0.2rem; }
            hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- DATABASE PERSISTENCE LOGIC ---
def load_db():
    try:
        df = conn.read(spreadsheet=DB_URL, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_db(df):
    conn.update(spreadsheet=DB_URL, data=df)

# --- SESSION STATE INITIALIZATION ---
if 'database' not in st.session_state:
    st.session_state.database = load_db()

if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}

# --- HELPER FUNCTIONS ---
def parse_price(value):
    if pd.isna(value) or str(value).lower() == 'nan' or str(value) == '':
        return 0.0
    try:
        clean_val = str(value).replace(' ', '').replace(',', '').replace('%', '')
        return float(clean_val)
    except:
        return 0.0

def clean_dataframe(df):
    df = df.astype(str)
    num_cols = len(df.columns)
    standard_names = ['Item', 'Nett', 'Gross', 'Markup']
    new_names = standard_names[:num_cols]
    if num_cols > len(standard_names):
        new_names += [f"Col_{i}" for i in range(len(standard_names), num_cols)]
    df.columns = new_names
    df = df[df['Item'] != 'nan']
    df = df[~df['Item'].str.contains("Item|Quantity|Rand Value|Description", case=False, na=False)]
    return df

# --- SIDEBAR & DATA LOADING ---
st.sidebar.title("🛠 Settings")

view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])
is_admin = False
if view_mode == "Advanced (Admin)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123": 
        is_admin = True
    else: 
        st.sidebar.warning("Incorrect password")

st.sidebar.markdown("---")
data = pd.DataFrame()
data_option = st.sidebar.radio("Load data from:", ["Upload CSV File", "Google Sheet Link"])

if data_option == "Upload CSV File":
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        data = clean_dataframe(pd.read_csv(uploaded_file))
else:
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    try:
        data = clean_dataframe(pd.read_csv(csv_url, storage_options={'User-Agent': 'Mozilla/5.0'}))
    except:
        st.sidebar.warning("⚠️ Google Sheet unreachable.")

# --- MAIN FORM ---
if not data.empty:
    st.title("📋 Bowler Artwork and Repro cost Estimate")
    count = st.session_state.reset_counter
    loaded = st.session_state.loaded_data
    
    # 1. Header Info
    c1, c2, c3, c4 = st.columns([1.5, 1, 2, 1])
    client_name = c1.text_input("Client Name", value=loaded.get("Client", ""), key=f"cl_{count}")
    preprod_ref = c2.text_input("Preprod Ref", value=loaded.get("Preprod", ""), key=f"pr_{count}")
    preprod_desc = c3.text_input("Preprod Description", value=loaded.get("Description", ""), key=f"pd_{count}")
    quote_date = c4.date_input("Date", datetime.date.today(), key=f"dt_{count}")

    st.markdown("**Foil Block Specifications:**")
    f1, f2, f3 = st.columns([1, 1, 1])
    foil_height = f1.number_input("Height (mm)", min_value=0.0, step=1.0, value=float(loaded.get("Foil_H", 0.0)), key=f"fh_{count}")
    foil_width = f2.number_input("Width (mm)", min_value=0.0, step=1.0, value=float(loaded.get("Foil_W", 0.0)), key=f"fw_{count}")
    foil_code = f3.number_input("Foil Code", min_value=0.0, step=1.0, value=float(loaded.get("Foil_C", 0.0)), key=f"fc_{count}")

    st.markdown("---")
    header_cols = [3, 1, 1, 1, 1, 1] if is_admin else [3, 1, 1, 1]
    cols = st.columns(header_cols)
    cols[0].write("**Item Description**"); cols[1].write("**Quantity**"); cols[2].write("**Unit Price (R)**"); cols[3].write("**Gross Total (R)**")
    if is_admin:
        cols[4].write("**Nett Total (R)**"); cols[5].write("**Markup %**")

    item_entries = {}; total_gross_sum = 0.0
    main_items = data[~data['Item'].str.lower().str.contains("foil")]
    
    # 2. Render Main Items
    for idx, row in main_items.iterrows():
        r = st.columns(header_cols)
        item_name = row['Item']
        r[0].write(item_name)
        
        nett = parse_price(row.get('Nett', '0.00'))
        markup = parse_price(row.get('Markup', '0'))
        calc_price = nett * (1 + (markup / 100))

        qty = r[1].number_input("Qty", min_value=0.0, value=float(loaded.get(f"{item_name}_Qty", 0.0)), step=1.0, key=f"qty_{idx}_{count}", label_visibility="collapsed")
        unit_p = r[2].number_input("Price", min_value=0.0, value=float(calc_price), key=f"prc_{idx}_{count}", label_visibility="collapsed")
        
        line_total = float(qty) * float(unit_p)
        total_gross_sum += line_total
        r[3].code(f"{line_total:,.2f}")
        
        if is_admin:
            r[4].write(f"{float(qty) * nett:,.2f}")
            r[5].write(f"{markup}%")
        item_entries[item_name] = {"qty": qty, "unit": unit_p, "total": line_total}

    # 3. Render Foil Block (Removed bold and dividers)
    fr = st.columns(header_cols)
    foil_name_search = data[data['Item'].str.lower().str.contains("foil")]
    f_item_name = foil_name_search.iloc[0]['Item'] if not foil_name_search.empty else "Foil Block"
    
    # Text weight matched to other items
    fr[0].write(f_item_name)
    
    f_calc_price = foil_code * 1.56
    f_qty = fr[1].number_input("Qty", min_value=0.0, value=float(loaded.get(f"{f_item_name}_Qty", 0.0)), step=1.0, key=f"fqty_{count}", label_visibility="collapsed")
    f_unit_p = fr[2].number_input("Price", min_value=0.0, value=float(f_calc_price), key=f"fprc_{count}", label_visibility="collapsed")
    
    f_line_total = float(f_qty) * float(f_unit_p)
    total_gross_sum += f_line_total
    fr[3].code(f"{f_line_total:,.2f}")
    
    if is_admin:
        fr[4].write(f"{float(f_qty) * foil_code:,.2f}")
        fr[5].write("56%")
    item_entries[f_item_name] = {"qty": f_qty, "unit": f_unit_p, "total": f_line_total}

    # 4. Totals
    st.markdown("---")
    res_c2 = st.columns([3, 3])[1]
    with res_c2:
        st.write("**Total (Excl. VAT):**"); st.code(f"R {total_gross_sum:,.2f}")
        vat_amount = total_gross_sum * 0.15
        st.write("**VAT (15%):**"); st.code(f"R {vat_amount:,.2f}")
        final_grand_total = total_gross_sum + vat_amount
        st.subheader(f"Grand Total: R {final_grand_total:,.2f}")

    # 5. Buttons
    act1, act2, act3 = st.columns([1, 1, 1])
    if act1.button("🚀 Finalize and Save to Google Sheets"):
        record = {
            "Status": "ACTIVE", "Client": client_name, "Preprod": preprod_ref, "Description": preprod_desc, 
            "Date": str(quote_date), "Foil_H": foil_height, "Foil_W": foil_width, "Foil_C": foil_code,
            "Total_Excl_Vat": total_gross_sum, "VAT_15": vat_amount, "Grand_Total": final_grand_total
        }
        for item, vals in item_entries.items(): record[f"{item}_Qty"] = vals["qty"]
        
        new_df = pd.concat([st.session_state.database, pd.DataFrame([record])], ignore_index=True)
        save_db(new_df)
        st.session_state.database = new_df
        st.success("✅ Permanent Save Complete.")

    if act3.button("🔄 Refresh / Clear Form"):
        st.session_state.reset_counter += 1
        st.session_state.loaded_data = {}
        st.rerun()

    # 6. Database Search
    if not st.session_state.database.empty:
        st.markdown("---")
        with st.expander("📂 Database Search & Load", expanded=False):
            search_term = st.text_input("🔍 Search Client or Preprod Ref").lower()
            db = st.session_state.database
            
            filtered_db = db[
                db['Client'].astype(str).str.lower().str.contains(search_term) | 
                db['Preprod'].astype(str).str.lower().str.contains(search_term)
            ]
            
            cols_to_hide = ["Item", "Nett", "Gross", "Markup"]
            display_columns = [col for col in filtered_db.columns if col not in cols_to_hide]
            st.dataframe(filtered_db, column_order=display_columns, use_container_width=True)
            
            if not filtered_db.empty:
                col_l, col_r = st.columns([2, 1])
                options = {idx: f"{row['Preprod']} - {row['Client']}" for idx, row in filtered_db.iterrows()}
                selected_idx = col_l.selectbox("Select Estimate to Load:", options=list(options.keys()), format_func=lambda x: options[x])
                
                if col_l.button("📂 Load Selected into Form"):
                    st.session_state.loaded_data = db.loc[selected_idx].to_dict()
                    st.session_state.reset_counter += 1
                    st.rerun()
else:
    st.info("👈 Use Sidebar to load source data.")