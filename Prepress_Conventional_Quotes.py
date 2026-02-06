import streamlit as st
import pandas as pd
import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Artwork and Repro Cost Estimate")

# Remove footer and tighten layout spacing
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                padding-left: 5rem;
                padding-right: 5rem;
            }
            [data-testid="stMarkdownContainer"] p {
                margin-bottom: 0.2rem;
            }
            hr {
                margin-top: 0.5rem !important;
                margin-bottom: 0.5rem !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'database' not in st.session_state:
    st.session_state.database = pd.DataFrame()

if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

if 'loaded_data' not in st.session_state:
    st.session_state.loaded_data = {}

def parse_price(value):
    if pd.isna(value) or str(value).lower() == 'nan' or str(value) == '':
        return 0.0
    try:
        clean_val = str(value).replace(' ', '').replace(',', '.')
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

# PDF Generation Function - UPDATED FONT TO HELVETICA
def create_pdf(client, ref, desc, date, foil_h, foil_w, foil_c, items, total, vat, grand):
    pdf = FPDF()
    pdf.add_page()
    
    # Use Helvetica as it is a standard PDF core font
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
    
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR ---
st.sidebar.title("🛠 Settings")
view_mode = st.sidebar.selectbox("Select View Mode", ["Standard User", "Advanced (Admin)"])

# Admin Password Logic
is_admin = False
if view_mode == "Advanced (Admin)":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == "admin123": # You can change this password
        is_admin = True
    else:
        st.sidebar.warning("Incorrect password")

st.sidebar.markdown("---")
st.sidebar.subheader("Data Source")
data_option = st.sidebar.radio("Load data from:", ["Upload CSV File", "Google Sheet Link"])
data = pd.DataFrame()

if data_option == "Upload CSV File":
    uploaded_file = st.sidebar.file_uploader("Upload your Sheet (Exported as CSV)", type="csv")
    if uploaded_file:
        raw_df = pd.read_csv(uploaded_file)
        data = clean_dataframe(raw_df)
else:
    sheet_id = "1zHOIawXjuufNYXymRxOWGghd6BQ8aXdZs7ve3P8fBYQ"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    try:
        raw_df = pd.read_csv(csv_url, storage_options={'User-Agent': 'Mozilla/5.0'})
        data = clean_dataframe(raw_df)
    except:
        st.sidebar.warning("⚠️ Google Sheet is Private.")

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

    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    foil_height = f1.number_input("Height (mm)", min_value=0.0, step=1.0, value=loaded.get("Foil_H", 0.0), key=f"fh_{count}")
    foil_width = f2.number_input("Width (mm)", min_value=0.0, step=1.0, value=loaded.get("Foil_W", 0.0), key=f"fw_{count}")
    foil_code = f3.number_input("Code", min_value=0.0, step=1.0, value=loaded.get("Foil_C", 0.0), key=f"fc_{count}")

    st.markdown("---")

    # Layout adjustment for Admin View
    header_cols = [3, 1, 1, 1, 1, 1] if is_admin else [3, 1, 1, 1]
    cols = st.columns(header_cols)
    cols[0].write("**Item Description**")
    cols[1].write("**Quantity**")
    cols[2].write("**Unit Price (R)**")
    cols[3].write("**Total (R)**")
    if is_admin:
        cols[4].write("**Nett (R)**")
        cols[5].write("**Markup %**")

    item_entries = {}
    total_nett = 0.0

    for idx, row in data.iterrows():
        r = st.columns(header_cols)
        item_name = row['Item']
        r[0].write(item_name)
        
        is_foil_row = "foil" in item_name.lower()
        if is_foil_row and foil_code > 0:
            base_price = float(foil_code) * 1.56
            nett_val = foil_code
            markup_val = "56%"
        else:
            base_price = parse_price(row.get('Gross', row.get('Nett', '0.00')))
            nett_val = parse_price(row.get('Nett', '0.00'))
            markup_val = row.get('Markup', '0%')

        saved_qty = loaded.get(f"{item_name}_Qty", 0.0)
        
        qty = r[1].number_input("Qty", min_value=0.0, value=saved_qty, step=1.0, key=f"qty_{idx}_{count}", label_visibility="collapsed")
        unit_price = r[2].number_input("Price", min_value=0.0, value=base_price, key=f"prc_{idx}_{count}", label_visibility="collapsed")
        
        line_total = qty * unit_price
        total_nett += line_total
        r[3].code(f"{line_total:,.2f}") 

        if is_admin:
            r[4].write(f"{nett_val:,.2f}")
            r[5].write(f"{markup_val}")
        
        item_entries[item_name] = {"qty": qty, "unit": unit_price, "total": line_total}

    st.markdown("---")
    
    res_c1, res_c2 = st.columns([3, 3])
    with res_c2:
        st.write("**Total (Excl. VAT):**")
        st.code(f"R {total_nett:,.2f}")
        vat_amount = total_nett * 0.15
        st.write("**VAT (15%):**")
        st.code(f"R {vat_amount:,.2f}")
        final_grand_total = total_nett + vat_amount
        st.subheader(f"Grand Total: R {final_grand_total:,.2f}")

    act1, act2, act3 = st.columns([1, 1, 1])
    
    if act1.button("🚀 Finalize and Save to Database"):
        if not client_name:
            st.error("Please enter a Client Name.")
        else:
            record = {
                "Status": "ACTIVE",
                "Client": client_name, 
                "Preprod": preprod_ref, 
                "Description": preprod_desc, 
                "Date": str(quote_date), 
                "Foil_H": foil_height, 
                "Foil_W": foil_width, 
                "Foil_C": foil_code, 
                "Total_Excl_Vat": total_nett, 
                "VAT_15": vat_amount, 
                "Grand_Total": final_grand_total
            }
            for item, vals in item_entries.items():
                record[f"{item}_Qty"] = vals["qty"]
            st.session_state.database = pd.concat([st.session_state.database, pd.DataFrame([record])], ignore_index=True)
            st.success(f"Quote for {client_name} saved!")

    pdf_filename = f"{preprod_ref}_{client_name}_{preprod_desc}.pdf".replace(" ", "_")
    try:
        pdf_bytes = create_pdf(client_name, preprod_ref, preprod_desc, quote_date, foil_height, foil_width, foil_code, item_entries, total_nett, vat_amount, final_grand_total)
        act2.download_button(label="📥 Download PDF", data=pdf_bytes, file_name=pdf_filename, mime="application/pdf")
    except Exception as e:
        act2.error(f"PDF Generation Error: {e}")

    if act3.button("🔄 Refresh / Clear Form"):
        st.session_state.reset_counter += 1
        st.session_state.loaded_data = {}
        st.rerun()

    # DATABASE SECTION
    if not st.session_state.database.empty:
        st.markdown("---")
        with st.expander("📂 Database Search & Load", expanded=False):
            search_term = st.text_input("🔍 Search by Client, Ref, or Description").lower()
            db = st.session_state.database
            
            # Filter logic
            filtered_db = db[
                db['Client'].str.lower().str.contains(search_term) | 
                db['Preprod'].str.lower().str.contains(search_term) |
                db['Description'].str.lower().str.contains(search_term)
            ]
            
            # Show dataframe with a visual indicator for Status
            st.dataframe(filtered_db.style.map(lambda x: 'color: red; font-weight: bold' if x == 'CANCELLED' else '', subset=['Status']))
            
            if not filtered_db.empty:
                col_l, col_r = st.columns(2)
                
                # Selection list with Status indicator
                select_list = [f"{idx}: [{row['Status']}] {row['Client']} ({row['Preprod']})" for idx, row in filtered_db.iterrows()]
                selected_item = col_l.selectbox("Select an entry to manage:", select_list)
                original_idx = int(selected_item.split(":")[0])

                if col_l.button("📂 Load Selected Estimate"):
                    st.session_state.loaded_data = db.loc[original_idx].to_dict()
                    st.session_state.reset_counter += 1
                    st.rerun()

                # THE CANCEL BUTTON
                if col_r.button("❌ Mark Selected as CANCELLED"):
                    st.session_state.database.at[original_idx, 'Status'] = "CANCELLED"
                    st.warning(f"Estimate {original_idx} has been marked as Cancelled.")
                    st.rerun()
else:
    st.info("👈 Use the Sidebar to upload your CSV file to begin.")