import streamlit as st
import pandas as pd
import datetime
import os
from fpdf import FPDF
from pathlib import Path
from streamlit_gsheets import GSheetsConnection
import io

# --- 1. CONFIGURATION & GLOBAL VARIABLES ---
st.set_page_config(layout="wide", page_title="Artwork and Repro cost Estimate")

# Define Sheet ID at the global level to prevent NameErrors
SHEET_ID = "1zHOIawXjuufNYXymRxOWGghd6BQ8aXdZs7ve3P8fBYQ"
DB_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Initialize data variable to prevent NameError if loading fails
data = pd.DataFrame()

# --- 2. PDF GENERATION FUNCTION ---
def create_pdf(client, preprod, desc, date, items, total_ex, vat, grand):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Title
    pdf.cell(190, 10, "Artwork and Repro Cost Estimate", ln=True, align='C')
    pdf.ln(10)
    
    # Header Details
    pdf.set_font("Arial", size=12)
    pdf.cell(95, 10, f"Client: {client}")
    pdf.cell(95, 10, f"Date: {date}", ln=True, align='R')
    pdf.cell(95, 10, f"Preprod Ref: {preprod}")
    pdf.cell(95, 10, f"Description: {desc}", ln=True, align='R')
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Item Description", 1, 0, 'L', True)
    pdf.cell(25, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Unit Price", 1, 0, 'C', True)
    pdf.cell(35, 10, "Total (R)", 1, 1, 'C', True)
    
    # Table Rows
    pdf.set_font("Arial", size=10)
    for item, val in items.items():
        if val['qty'] > 0:
            pdf.cell(100, 8, str(item), 1)
            pdf.cell(25, 8, f"{val['qty']:.2f}", 1, 0, 'C')
            pdf.cell(30, 8, f"{val['unit']:,.2f}", 1, 0, 'R')
            pdf.cell(35, 8, f"{val['total']:,.2f}", 1, 1, 'R')
            
    pdf.ln(5)
    
    # Summary Totals
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(125, 8, "", 0)
    pdf.cell(30, 8, "Subtotal:", 0)
    pdf.cell(35, 8, f"R {total_ex:,.2f}", 0, 1, 'R')
    
    pdf.cell(125, 8, "", 0)
    pdf.cell(30, 8, "VAT (15%):", 0)
    pdf.cell(35, 8, f"R {vat:,.2f}", 0, 1, 'R')
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(125, 10, "", 0)
    pdf.cell(30, 10, "Grand Total:", 1, 0, 'L', True)
    pdf.cell(35, 10, f"R {grand:,.2f}", 1, 1, 'R', True)
    
    # Generate bytes
    return pdf.output(dest='S').encode('latin-1')

# --- 3. DATABASE & HELPER LOGIC ---
def load_db():
    try:
        df = conn.read(spreadsheet=DB_URL, ttl=0)
        return df if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_db(df):
    conn.update(spreadsheet=DB_URL, data=df)

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

# --- 4. SESSION STATE ---
if 'database' not in st.session_state:
    st.session_state.database = load_db()
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}

# --- 5. SIDEBAR ---
st.sidebar.title("🛠 Settings")
view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])
is_admin = False
if view_mode == "Advanced (Admin)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123": is_admin = True
    else: st.sidebar.warning("Incorrect password")

st.sidebar.markdown("---")
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

# --- 6. MAIN FORM ---
if not data.empty:
    st.title("📋 Bowler Artwork and Repro cost Estimate")
    count = st.session_state.reset_counter
    loaded = st.session_state.loaded_data
    
    # Header Info
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

    item_entries = {}; total_gross_sum = 0.0
    main_items = data[~data['Item'].str.lower().str.contains("foil")]
    
    for idx, row in main_items.iterrows():
        r = st.columns(header_cols)
        item_name = row['Item']
        r[0].write(item_name)
        nett = parse_price(row.get('Nett', '0.00'))
        markup = parse_price(row.get('Markup', '0'))
        calc_price = nett * (1 + (markup / 100))
        qty = r[1].number_input("Qty", min_value=0.0, value=float(loaded.get(f"{item_name}_Qty", 0.0)), key=f"qty_{idx}_{count}", label_visibility="collapsed")
        unit_p = r[2].number_input("Price", min_value=0.0, value=float(calc_price), key=f"prc_{idx}_{count}", label_visibility="collapsed")
        line_total = float(qty) * float(unit_p)
        total_gross_sum += line_total
        r[3].code(f"{line_total:,.2f}")
        item_entries[item_name] = {"qty": qty, "unit": unit_p, "total": line_total}

    # Foil Block Logic
    fr = st.columns(header_cols)
    foil_name_search = data[data['Item'].str.lower().str.contains("foil")]
    f_item_name = foil_name_search.iloc[0]['Item'] if not foil_name_search.empty else "Foil Block"
    fr[0].write(f_item_name)
    f_calc_price = foil_code * 1.56
    f_qty = fr[1].number_input("Qty", min_value=0.0, value=float(loaded.get(f"{f_item_name}_Qty", 0.0)), key=f"fqty_{count}", label_visibility="collapsed")
    f_unit_p = fr[2].number_input("Price", min_value=0.0, value=float(f_calc_price), key=f"fprc_{count}", label_visibility="collapsed")
    f_line_total = float(f_qty) * float(f_unit_p)
    total_gross_sum += f_line_total
    fr[3].code(f"{f_line_total:,.2f}")
    item_entries[f_item_name] = {"qty": f_qty, "unit": f_unit_p, "total": f_line_total}

    # Totals Section
    st.markdown("---")
    res_c2 = st.columns([3, 3])[1]
    with res_c2:
        st.write("**Total (Excl. VAT):**"); st.code(f"R {total_gross_sum:,.2f}")
        vat_amount = total_gross_sum * 0.15
        st.write("**VAT (15%):**"); st.code(f"R {vat_amount:,.2f}")
        final_grand_total = total_gross_sum + vat_amount
        st.subheader(f"Grand Total: R {final_grand_total:,.2f}")

    # --- BUTTONS SECTION ---
    act1, act2, act3 = st.columns([1, 1, 1])
    
    if act1.button("🚀 Finalize and Save to Google Sheets"):
        record = {"Status": "ACTIVE", "Client": client_name, "Preprod": preprod_ref, "Description": preprod_desc, "Date": str(quote_date), "Grand_Total": final_grand_total}
        for item, vals in item_entries.items(): record[f"{item}_Qty"] = vals["qty"]
        new_df = pd.concat([st.session_state.database, pd.DataFrame([record])], ignore_index=True)
        save_db(new_df)
        st.session_state.database = new_df
        st.success("✅ Permanent Save Complete.")

    # PDF Download Button
    clean_client = client_name.replace(" ", "_") if client_name else "Client"
    clean_desc = preprod_desc.replace(" ", "_") if preprod_desc else "Quote"
    unique_filename = f"{preprod_ref}_{clean_client}_{clean_desc}.pdf"

    pdf_bytes = create_pdf(client_name, preprod_ref, preprod_desc, quote_date, item_entries, total_gross_sum, vat_amount, final_grand_total)
    
    act2.download_button(
        label="📄 Download PDF Quote",
        data=pdf_bytes,
        file_name=unique_filename,
        mime="application/pdf"
    )

    if act3.button("🔄 Refresh / Clear Form"):
        st.session_state.reset_counter += 1
        st.session_state.loaded_data = {}
        st.rerun()
else:
    st.info("👈 Use Sidebar to load source data.")