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

def create_pdf(client, ref, desc, date, foil_h, foil_w, foil_c, foil_qty, items, total, vat, grand):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(200, 10, "Bowler Artwork and Repro Cost Estimate", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(100, 7, f"Client: {client}")
    pdf.cell(100, 7, f"Date: {date}", ln=True)
    pdf.cell(100, 7, f"Preprod Ref: {ref}")
    pdf.cell(100, 7, f"Description: {desc}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(200, 7, "Foil Block Specifications:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(50, 7, f"Height: {foil_h} mm")
    pdf.cell(50, 7, f"Width: {foil_w} mm")
    pdf.cell(50, 7, f"Code: {foil_c}")
    pdf.cell(50, 7, f"Block Qty: {foil_qty}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 7, "Item Description", border=1)
    pdf.cell(30, 7, "Qty", border=1)
    pdf.cell(30, 7, "Unit (R)", border=1)
    pdf.cell(30, 7, "Total (R)", border=1, ln=True)
    pdf.set_font("Helvetica", "", 10)
    for name, vals in items.items():
        if vals['qty'] > 0:
            pdf.cell(100, 7, str(name), border=1)
            pdf.cell(30, 7, f"{vals['qty']:.0f}", border=1)
            pdf.cell(30, 7, f"{vals['unit']:,.2f}", border=1)
            pdf.cell(30, 7, f"{vals['total']:,.2f}", border=1, ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(130, 7, "")
    pdf.cell(30, 7, "Total:", border=0)
    pdf.cell(30, 7, f"R {total:,.2f}", ln=True)
    pdf.cell(130, 7, "")
    pdf.cell(30, 7, "VAT (15%):", border=0)
    pdf.cell(30, 7, f"R {vat:,.2f}", ln=True)
    pdf.cell(130, 7, "")
    pdf.cell(30, 7, "Grand Total:", border=0)
    pdf.cell(30, 7, f"R {grand:,.2f}", ln=True)
    pdf.ln(20) 
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(200, 10, "Client Approval: ........................................................", ln=True)
    pdf.cell(200, 10, "Date: ....................................", ln=True)
    pdf.cell(200, 10, "Order Number: ...........................................................................", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.title("🛠 Settings")
view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])
is_admin = False
if view_mode == "Advanced (Admin)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123": is_admin = True
    else: st.sidebar.warning("Incorrect password")

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Export Database")
if not st.session_state.database.empty:
    csv_data = st.session_state.database.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(label="📥 Download Database as CSV", data=csv_data, file_name=f"quotes_db_{datetime.date.today()}.csv", mime="text/csv")

st.sidebar.markdown("---")
st.sidebar.subheader("Data Source")
data_option = st.sidebar.radio("Load data from:", ["Upload CSV File", "Google Sheet Link"])
data = pd.DataFrame()

if data_option == "Upload CSV File":
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        data = clean_dataframe(pd.read_csv(uploaded_file))
else:
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    try:
        data = clean_dataframe(pd.read_csv(csv_url, storage_options={'User-Agent': 'Mozilla/5.0'}))
    except:
        st.sidebar.warning("⚠️ Google Sheet Private or unreachable.")

# --- MAIN FORM ---
if not data.empty:
    st.title("📋 Bowler Artwork and Repro Cost Estimate")
    count = st.session_state.reset_counter
    loaded = st.session_state.loaded_data
    
    # PDF Info Section
    c1, c2, c3, c4 = st.columns([1.5, 1, 2, 1])
    client_name = c1.text_input("Client Name", value=loaded.get("Client", ""), key=f"cl_{count}")
    preprod_ref = c2.text_input("Preprod Ref", value=loaded.get("Preprod", ""), key=f"pr_{count}")
    preprod_desc = c3.text_input("Preprod Description", value=loaded.get("Description", ""), key=f"pd_{count}")
    quote_date = c4.date_input("Date", datetime.date.today(), key=f"dt_{count}")

    # Foil Block Description (Now directly underneath PDF Info)
    st.markdown("**Foil Block Specifications:**")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    foil_height = f1.number_input("Height (mm)", min_value=0.0, step=1.0, value=float(loaded.get("Foil_H", 0.0)), key=f"fh_{count}")
    foil_width = f2.number_input("Width (mm)", min_value=0.0, step=1.0, value=float(loaded.get("Foil_W", 0.0)), key=f"fw_{count}")
    foil_code = f3.number_input("Foil Code", min_value=0.0, step=1.0, value=float(loaded.get("Foil_C", 0.0)), key=f"fc_{count}")
    foil_block_qty = f4.number_input("Foil Block Qty", min_value=0.0, step=1.0, value=float(loaded.get("Foil Block_Qty", 0.0)), key=f"fbq_{count}")

    st.markdown("---")
    header_cols = [3, 1, 1, 1, 1, 1] if is_admin else [3, 1, 1, 1]
    cols = st.columns(header_cols)
    cols[0].write("**Item Description**"); cols[1].write("**Quantity**"); cols[2].write("**Unit Price (R)**"); cols[3].write("**Gross Total (R)**")
    if is_admin: cols[4].write("**Nett Total (R)**"); cols[5].write("**Markup %**")

    item_entries = {}; total_gross_sum = 0.0; foil_qty_entered = 0.0

    for idx, row in data.iterrows():
        r = st.columns(header_cols)
        item_name = row['Item']
        r[0].write(item_name)
        is_foil_row = "foil" in item_name.lower()
        
        # LOGIC: If Foil Code is inserted, calculate unit price with 56% markup
        if is_foil_row:
            calculated_unit_price = foil_code * 1.56
            current_nett_unit = foil_code
            markup_perc = 56.0
        else:
            current_nett_unit = parse_price(row.get('Nett', '0.00'))
            markup_perc = parse_price(row.get('Markup', '0'))
            calculated_unit_price = current_nett_unit * (1 + (markup_perc / 100))

        # Quantity Box
        saved_qty = loaded.get(f"{item_name}_Qty", 0.0)
        qty = r[1].number_input("Qty", min_value=0.0