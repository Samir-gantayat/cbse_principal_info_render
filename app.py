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

# Load CSV safely
school_df = pd.read_csv(
    CSV_FILE,
    dtype=str,
    on_bad_lines="skip",
    engine="python"
).fillna("Not Found")

HTML_PAGE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>School Info Explorer</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* --- same CSS styles as before --- */
</style>
</head>
<body>
<div class="container">
    <div class="hero">
        <h1 class="title">School Info Explorer</h1>
        <p class="subtitle">Enter Affiliation Number to fetch school details from CBSE SARAS or fallback to local CSV.</p>
        <form class="search-wrap" method="post">
            <div class="search">
                <input name="aff_no" placeholder="Enter Affiliation Number" required value="{{ aff_no or '' }}" />
                <button type="submit">Search</button>
            </div>
        </form>
        {% if error %}
        <div class="alert error"><strong>Error:</strong> {{ error }}</div>
        {% elif data %}
        <div class="alert success"><strong>Result:</strong> Found details for {{ aff_no }}</div>
        {% endif %}
    </div>
    {% if data %}
    <section class="results">
        <div class="card"><div class="head">School Name</div><div class="value">{{ data.school_name }}</div></div>
        <div class="card"><div class="head">Affiliation No</div><div class="value">{{ data.aff_no }}</div></div>
        <div class="card"><div class="head">Principal Name</div><div class="value">{{ data.principal_name }}</div></div>
        <div class="card"><div class="head">Principal Contact</div><div class="value">{{ data.number }}</div></div>
        <div class="card"><div class="head">Principal Email</div><div class="value">{{ data.mail }}</div></div>
        {% if data.school_mail %}<div class="card"><div class="head">School Email</div><div class="value">{{ data.school_mail }}</div></div>{% endif %}
        {% if data.total_strength %}<div class="card"><div class="head">Total Students</div><div class="value">{{ data.total_strength }}</div></div>{% endif %}
        {% if data.fee_structure %}<div class="card"><div class="head">Fee Structure (Annual)</div><div class="value">{{ data.fee_structure }}</div></div>{% endif %}
    </section>
    {% endif %}
</div>
</body>
</html>
"""

def fetch_from_cbse(aff_no):
    """Fetch school details from CBSE SARAS portal."""
    try:
        url = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        def get_val(div_id):
            el = soup.find(id=div_id)
            return el.get_text(strip=True) if el else "Not Found"

        # Total strength = sum of lblstu1 to lblstu12
        total_strength = 0
        for i in range(1, 13):
            val = get_val(f"lblstu{i}")
            if val.isdigit():
                total_strength += int(val)

        total_strength = str(total_strength) if total_strength > 0 else "Not Found"

        # Fee structure calculation
        fee_parts = []
        for fid in ["lblsecadm", "lblsecdev", "lblsecoth", "lblsectui"]:
            val = get_val(fid)
            if val.isdigit():
                amt = int(val)
                if fid == "lblsectui":
                    if len(str(amt)) <= 4:  # treat as monthly, multiply by 12
                        amt *= 12
                fee_parts.append(amt)
        fee_structure = str(sum(fee_parts)) if fee_parts else "Not Found"

        return {
            "school_name": get_val("schoolName"),
            "aff_no": get_val("affNo"),
            "principal_name": get_val("lblprinci"),
            "number": get_val("lblprincicon"),
            "mail": get_val("lblprinciemail"),
            "school_mail": get_val("lblschemail"),
            "total_strength": total_strength,
            "fee_structure": fee_structure
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
        school_df = pd.read_csv(
            CSV_FILE, dtype=str, on_bad_lines="skip", engine="python"
        ).fillna("Not Found")

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
                save_to_csv(data)  # store basic result in local CSV
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
                        "mail": row["Mail"],
                        "school_mail": None,
                        "total_strength": None,
                        "fee_structure": None
                    }

    return render_template_string(HTML_PAGE, data=data, error=error, aff_no=aff_no)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
