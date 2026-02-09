import streamlit as st
import pandas as pd
import datetime
import os
import platform
import subprocess
from fpdf import FPDF
from pathlib import Path

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Artwork and Repro Cost Estimate")

DB_FILE = "estimates_db.csv"

def get_desktop_path():
    """Detects the desktop path across Windows (with/without OneDrive) and macOS."""
    home = Path.home()
    # Check common OneDrive locations first as they are the primary cause of 'missing' files
    onedrive_desktop = home / "OneDrive" / "Desktop"
    standard_desktop = home / "Desktop"
    
    if onedrive_desktop.exists():
        return onedrive_desktop
    return standard_desktop

# Define and Create the Folder
DESKTOP_PATH = get_desktop_path() / "Conventional Quotes"
try:
    DESKTOP_PATH.mkdir(parents=True, exist_ok=True)
except Exception as e:
    st.error(f"Folder Creation Error: {e}")

# --- STYLING ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 5rem; padding-right: 5rem; }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- DATABASE LOGIC ---
def load_db():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

def save_db(df):
    df.to_csv(DB_FILE, index=False)

if 'database' not in st.session_state:
    st.session_state.database = load_db()
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0
if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}

def parse_price(value):
    try:
        clean_val = str(value).replace(' ', '').replace(',', '').replace('%', '')
        return float(clean_val) if clean_val else 0.0
    except:
        return 0.0

def clean_dataframe(df):
    df = df.astype(str)
    standard_names = ['Item', 'Nett', 'Gross', 'Markup']
    df.columns = standard_names[:len(df.columns)] + [f"Col_{i}" for i in range(len(standard_names), len(df.columns))]
    return df[df['Item'] != 'nan']

# --- PDF LOGIC ---
def create_pdf(client, ref, desc, date, foil_h, foil_w, foil_c, items, total, vat, grand):
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
    pdf.cell(60, 7, f"Height: {foil_h} mm")
    pdf.cell(60, 7, f"Width: {foil_w} mm")
    pdf.cell(60, 7, f"Code: {foil_c}", ln=True)
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
    pdf.ln(40)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(200, 10, "Client approval................................... Date...................... Order number......................", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.title("🛠 Settings")
view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])
is_admin = (view_mode == "Advanced (Admin)" and st.sidebar.text_input("Password", type="password") == "admin123")

data_option = st.sidebar.radio("Load data from:", ["Upload CSV File", "Google Sheet Link"])
data = pd.DataFrame()

if data_option == "Upload CSV File":
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        data = clean_dataframe(pd.read_csv(uploaded_file))
else:
    sheet_id = "1zHOIawXjuufNYXymRxOWGghd6BQ8aXdZs7ve3P8fBYQ"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    try:
        data = clean_dataframe(pd.read_csv(csv_url, storage_options={'User-Agent': 'Mozilla/5.0'}))
    except:
        st.sidebar.warning("⚠️ Data access error.")

# --- MAIN FORM ---
if not data.empty:
    st.title("📋 Bowler Artwork and Repro Cost Estimate")
    count = st.session_state.reset_counter
    loaded = st.session_state.loaded_data
    
    c1, c2, c3, c4 = st.columns([1.5, 1, 2, 1])
    client_name = c1.text_input("Client Name", value=loaded.get("Client", ""), key=f"cl_{count}")
    preprod_ref = c2.text_input("Preprod Ref", value=loaded.get("Preprod", ""), key=f"pr_{count}")
    preprod_desc = c3.text_input("Preprod Description", value=loaded.get("Description", ""), key=f"pd_{count}")
    quote_date = c4.date_input("Date", datetime.date.today(), key=f"dt_{count}")

    f1, f2, f3 = st.columns(3)
    foil_height = f1.number_input("Height (mm)", min_value=0.0, value=float(loaded.get("Foil_H", 0.0)), key=f"fh_{count}")
    foil_width = f2.number_input("Width (mm)", min_value=0.0, value=float(loaded.get("Foil_W", 0.0)), key=f"fw_{count}")
    foil_code = f3.number_input("Foil Code", min_value=0.0, value=float(loaded.get("Foil_C", 0.0)), key=f"fc_{count}")

    st.markdown("---")
    header_cols = [3, 1, 1, 1, 1, 1] if is_admin else [3, 1, 1, 1]
    cols = st.columns(header_cols)
    cols[0].write("**Item Description**"); cols[1].write("**Quantity**"); cols[2].write("**Unit Price (R)**"); cols[3].write("**Gross Total (R)**")

    item_entries = {}
    total_gross_sum = 0.0
    
    for idx, row in data.iterrows():
        r = st.columns(header_cols)
        item_name = row['Item']
        r[0].write(item_name)
        is_foil = "foil" in item_name.lower()
        
        nett = foil_code if is_foil else parse_price(row.get('Nett', 0))
        markup = 56.0 if is_foil else parse_price(row.get('Markup', 0))
        calc_unit = nett * (1 + (markup / 100))

        qty = r[1].number_input("Qty", min_value=0.0, value=float(loaded.get(f"{item_name}_Qty", 0.0)), key=f"qty_{idx}_{count}")
        unit = r[2].number_input("Price", min_value=0.0, value=float(calc_unit), key=f"prc_{idx}_{count}")
        
        line_total = qty * unit
        total_gross_sum += line_total
        r[3].code(f"{line_total:,.2f}")
        item_entries[item_name] = {"qty": qty, "unit": unit, "total": line_total}

    st.markdown("---")
    vat_amount = total_gross_sum * 0.15
    final_total = total_gross_sum + vat_amount
    
    act1, act2, act3 = st.columns(3)
    
    # PDF PREPARATION
    pdf_filename = f"{preprod_ref}_{client_name}.pdf".replace(" ", "_").replace("/", "-")
    pdf_bytes = create_pdf(client_name, preprod_ref, preprod_desc, quote_date, foil_height, foil_width, foil_code, item_entries, total_gross_sum, vat_amount, final_total)

    if act1.button("🚀 Save to Database"):
        record = {"Client": client_name, "Preprod": preprod_ref, "Grand_Total": final_total}
        for i, v in item_entries.items(): record[f"{i}_Qty"] = v["qty"]
        st.session_state.database = pd.concat([st.session_state.database, pd.DataFrame([record])], ignore_index=True)
        save_db(st.session_state.database)
        st.success("Database Updated!")

    if act2.button("💾 Save PDF to Desktop"):
        save_path = DESKTOP_PATH.resolve() / pdf_filename
        try:
            with open(save_path, "wb") as f:
                f.write(pdf_bytes)
            st.success(f"Saved to: {save_path}")
            # Try to open the folder automatically
            if platform.system() == "Windows":
                os.startfile(DESKTOP_PATH)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(DESKTOP_PATH)])
        except Exception as e:
            st.error(f"Save Failed: {e}")

    if act3.button("🔄 Clear Form"):
        st.session_state.reset_counter += 1
        st.session_state.loaded_data = {}
        st.rerun()

else:
    st.info("👈 Upload data in the sidebar to begin.")