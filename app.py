from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

app = Flask(__name__)

# Google Sheet (CSV export)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UCYuxblCP-XDYLD6pJG-_Md_dlUzOr7Ucf0X_lBDEsU/gviz/tq?tqx=out:csv"

# Load sheet at startup
try:
    school_df = pd.read_csv(SHEET_URL, dtype=str).fillna("")
except Exception as e:
    school_df = pd.DataFrame()

HTML_PAGE = """ 
<!-- (your original HTML stays unchanged) -->
"""  # keeping your frontend same

def get_text(soup, el_id):
    el = soup.find("span", id=el_id)
    return el.get_text(strip=True) if el else ""

def parse_number(value):
    if not value: return None
    cleaned = re.sub(r"[^\d]", "", value)
    if not cleaned: return None
    try:
        return int(cleaned)
    except:
        return None

def calculate_fee(soup):
    sec_adm  = parse_number(get_text(soup, "lblsecadm"))
    sec_tui  = parse_number(get_text(soup, "lblsectui"))
    sec_oth  = parse_number(get_text(soup, "lblsecoth"))
    sec_dev  = parse_number(get_text(soup, "lblsecdev"))

    fee = 0
    if sec_adm:
        fee += sec_adm

    if sec_tui:
        digits = len(str(sec_tui))
        if digits == 4:       # 4-digit → multiply by 12
            fee += sec_tui * 12
        elif digits >= 5:     # 5+ digits → use directly
            fee += sec_tui
        else:                 # 3-digit or less → multiply by 12
            fee += sec_tui * 12

    if sec_oth:
        fee += sec_oth
    if sec_dev:
        fee += sec_dev

    return fee if fee > 0 else None

def get_school_from_sheet(aff_no):
    if school_df.empty or "Affiliation No" not in school_df.columns:
        return None

    row = school_df.loc[school_df['Affiliation No'].astype(str) == str(aff_no)]
    if row.empty:
        return None
    
    row = row.iloc[0]
    return {
        "principal_name": row.get("Principal Name", "Not Found"),
        "principal_contact": row.get("Principal Contact", "Not Found"),
        "principal_email": row.get("Principal Email", "Not Found"),
        "school_email": row.get("School Email", "Not Found"),
        "address": row.get("Address", "Not Found"),
        "website": row.get("Website", "Not Found"),
        "total_students": row.get("Total Students", "Not Available"),
        "fee_structure": int(row["Fee Structure"]) if row.get("Fee Structure") else None
    }

@app.route("/", methods=["GET", "POST"])
def index():
    data = None
    error = None
    aff_no = None

    if request.method == "POST":
        aff_no = request.form.get("aff_no", "").strip()
        if not aff_no:
            error = "Please enter a valid Affiliation Number."
        else:
            # ✅ Try from Google Sheet first
            data = get_school_from_sheet(aff_no)

            if not data:  # fallback to scraping if not in sheet
                url = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
                try:
                    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
                    res.raise_for_status()
                    soup = BeautifulSoup(res.text, "html.parser")

                    principal_name   = get_text(soup, "lblprinci") or "Not Found"
                    principal_contact= get_text(soup, "lblprincicon") or "Not Found"
                    principal_email  = get_text(soup, "lblprinciemail") or "Not Found"
                    school_email     = get_text(soup, "lblschemail") or "Not Found"
                    address          = get_text(soup, "lbladd") or "Not Found"
                    website          = get_text(soup, "lblschweb") or "Not Found"

                    total_students = 0
                    found_any = False
                    for i in range(1, 13):
                        val = parse_number(get_text(soup, f"lblstu{i}"))
                        if val is not None:
                            total_students += val
                            found_any = True
                    total_students_display = f"{total_students:,}" if found_any else "Not Available"

                    fee_structure = calculate_fee(soup)

                    data = {
                        "principal_name": principal_name,
                        "principal_contact": principal_contact,
                        "principal_email": principal_email,
                        "school_email": school_email,
                        "address": address,
                        "website": website,
                        "total_students": total_students_display,
                        "fee_structure": fee_structure
                    }

                    if all(v in ("Not Found", "Not Available", None) for v in data.values()):
                        data = None
                        error = "No information found for this Affiliation Number."

                except requests.exceptions.Timeout:
                    error = "The server took too long to respond. Please try again."
                except requests.exceptions.RequestException as e:
                    error = f"Failed to fetch data: {e}"

    return render_template_string(HTML_PAGE, data=data, error=error, aff_no=aff_no)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
