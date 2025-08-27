from flask import Flask, render_template_string, request
import pandas as pd
import requests
import os

app = Flask(__name__)

CSV_FILE = "schools.csv"

# Ensure CSV exists with required columns
REQUIRED_COLS = ["School Name", "Aff No", "Principal Name", "Number", "Mail"]
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=REQUIRED_COLS).to_csv(CSV_FILE, index=False)

# Load CSV
school_df = pd.read_csv(CSV_FILE, dtype=str).fillna("Not Found")

HTML_PAGE = """ 
<!-- same HTML frontend as before -->
"""  

def fetch_from_cbse(aff_no):
    """
    Fetch school details from CBSE SARAS portal.
    Returns dict if found, else None.
    """
    try:
        url = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Helper to fetch value by label text
        def get_text(label):
            el = soup.find(string=lambda t: label in t)
            if el:
                td = el.find_parent("td").find_next_sibling("td")
                if td:
                    return td.get_text(strip=True)
            return "Not Found"

        return {
            "school_name": get_text("Name of Institution"),
            "aff_no": aff_no,
            "principal_name": get_text("Principal"),
            "number": get_text("Principal's Phone No"),
            "mail": get_text("Principal's Email ID")
        }
    except Exception as e:
        print("Error fetching CBSE:", e)
        return None


def save_to_csv(data):
    """Append school details to CSV if not already present."""
    global school_df
    if data["aff_no"] not in school_df["Aff No"].astype(str).values:
        new_row = pd.DataFrame([{
            "School Name": data["school_name"],
            "Aff No": data["aff_no"],
            "Principal Name": data["principal_name"],
            "Number": data["number"],
            "Mail": data["mail"]
        }])
        new_row.to_csv(CSV_FILE, mode="a", header=False, index=False)
        # Reload into memory
        school_df = pd.read_csv(CSV_FILE, dtype=str).fillna("Not Found")


@app.route("/", methods=["GET", "POST"])
def index():
    global school_df
    data = None
    error = None
    aff_no = None

    if request.method == "POST":
        aff_no = request.form.get("aff_no", "").strip()
        if not aff_no:
            error = "Please enter a valid Affiliation Number."
        else:
            # Step 1: Try SARAS
            data = fetch_from_cbse(aff_no)

            if data:
                save_to_csv(data)  # store result in local CSV for offline use
            else:
                # Step 2: fallback to CSV
                row = school_df.loc[school_df["Aff No"] == aff_no]
                if row.empty:
                    error = "No information found for this Affiliation Number."
                else:
                    row = row.iloc[0]
                    data = {
                        "school_name": row["School Name"],
                        "aff_no": row["Aff No"],
                        "principal_name": row["Principal Name"],
                        "number": row["Number"],
                        "mail": row.get("Mail", "Not Found"),
                    }

    return render_template_string(HTML_PAGE, data=data, error=error, aff_no=aff_no)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
