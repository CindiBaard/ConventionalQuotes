import streamlit as st
import pandas as pd
import datetime
import os
from fpdf import FPDF
from pathlib import Path
from streamlit_gsheets import GSheetsConnection
import io

# --- SIDEBAR & DATA LOADING ---
st.sidebar.title("🛠 Settings")

# 1. INITIALIZE DATA HERE TO PREVENT NameError
data = pd.DataFrame() 

view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])

# ... (rest of your admin password logic) ...

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
    except Exception as e:
        st.sidebar.warning(f"⚠️ Google Sheet unreachable: {e}")
        # data remains an empty DataFrame from the initialization above# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Artwork and Repro cost Estimate")

# GOOGLE SHEETS CONFIGURATION
SHEET_ID = "1zHOIawXjuufNYXymRxOWGghd6BQ8aXdZs7ve3P8fBYQ" 
DB_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0"

# Establish Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- PDF GENERATION LOGIC ---
def create_pdf(client, preprod, desc, date, items, total_ex, vat, grand):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Header
    pdf.cell(190, 10, "Artwork and Repro Cost Estimate", ln=True, align='C')
    pdf.ln(10)
    
    # Client Info
    pdf.set_font("Arial", size=12)
    pdf.cell(95, 10, f"Client: {client}")
    pdf.cell(95, 10, f"Date: {date}", ln=True, align='R')
    pdf.cell(95, 10, f"Preprod Ref: {preprod}")
    pdf.cell(95, 10, f"Description: {desc}", ln=True, align='R')
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, "Item Description", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Unit Price", 1, 0, 'C', True)
    pdf.cell(30, 10, "Total", 1, 1, 'C', True)
    
    # Table Rows
    pdf.set_font("Arial", size=10)
    for item, val in items.items():
        if val['qty'] > 0:
            pdf.cell(100, 8, str(item), 1)
            pdf.cell(30, 8, f"{val['qty']:.2f}", 1, 0, 'C')
            pdf.cell(30, 8, f"{val['unit']:.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{val['total']:,.2f}", 1, 1, 'R')
            
    pdf.ln(5)
    
    # Totals
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(130, 8, "", 0)
    pdf.cell(30, 8, "Total (Excl):", 0)
    pdf.cell(30, 8, f"R {total_ex:,.2f}", 0, 1, 'R')
    
    pdf.cell(130, 8, "", 0)
    pdf.cell(30, 8, "VAT (15%):", 0)
    pdf.cell(30, 8, f"R {vat:,.2f}", 0, 1, 'R')
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(130, 10, "", 0)
    pdf.cell(30, 10, "Grand Total:", 1, 0, 'L', True)
    pdf.cell(30, 10, f"R {grand:,.2f}", 1, 1, 'R', True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI Styling (Existing Code) ---
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

# ... (Insert load_db, save_db, clean_dataframe, and data loading logic here from your original script) ...

# --- MAIN FORM (Simplified for logic placement) ---
if not data.empty:
    st.title("📋 Bowler Artwork and Repro cost Estimate")
    count = st.session_state.reset_counter
    loaded = st.session_state.loaded_data
    
    c1, c2, c3, c4 = st.columns([1.5, 1, 2, 1])
    client_name = c1.text_input("Client Name", value=loaded.get("Client", ""), key=f"cl_{count}")
    preprod_ref = c2.text_input("Preprod Ref", value=loaded.get("Preprod", ""), key=f"pr_{count}")
    preprod_desc = c3.text_input("Preprod Description", value=loaded.get("Description", ""), key=f"pd_{count}")
    quote_date = c4.date_input("Date", datetime.date.today(), key=f"dt_{count}")

    # ... (Insert specs and item rendering logic here from your original script) ...

    # --- FOOTER TOTALS & PDF BUTTONS ---
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
        # ... (Your existing Save logic) ...
        st.success("✅ Permanent Save Complete.")

    # --- NEW PDF DOWNLOAD BUTTON ---
    # Create the dynamic filename
    clean_client = client_name.replace(" ", "_")
    clean_desc = preprod_desc.replace(" ", "_")
    file_name = f"{preprod_ref}_{clean_client}_{clean_desc}.pdf"

    pdf_data = create_pdf(client_name, preprod_ref, preprod_desc, quote_date, 
                          item_entries, total_gross_sum, vat_amount, final_grand_total)

    act2.download_button(
        label="📄 Download Quote as PDF",
        data=pdf_data,
        file_name=file_name,
        mime="application/pdf"
    )

    if act3.button("🔄 Refresh / Clear Form"):
        st.session_state.reset_counter += 1
        st.session_state.loaded_data = {}
        st.rerun()