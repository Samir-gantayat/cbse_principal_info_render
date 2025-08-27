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

# Safe CSV loader (skips broken rows)
def load_csv():
    try:
        return pd.read_csv(
            CSV_FILE,
            dtype=str,
            on_bad_lines="skip",   # skip malformed rows
            engine="python"        # flexible parsing
        ).fillna("Not Found")
    except Exception as e:
        print(f"⚠️ Error reading CSV: {e}")
        return pd.DataFrame(columns=REQUIRED_COLS)

# Load CSV at startup
school_df = load_csv()

# Full HTML Frontend
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
    :root{
        --card-bg: rgba(255,255,255,0.95);
        --card-shadow: 0 10px 30px rgba(0,0,0,0.15);
        --card-shadow-hover: 0 16px 40px rgba(0,0,0,0.22);
        --accent: #2c7be5;
        --accent-2: #6c5ce7;
        --danger: #d9534f;
        --success: #20c997;
        --muted: #6b7280;
        --text: #111827;
        --radius: 14px;
    }
    * { box-sizing: border-box; }
    html, body { height: 100%; margin:0; }
    body {
        font-family: 'Inter', sans-serif;
        color: var(--text);
        background:
            linear-gradient( to bottom right, rgba(32,33,36,0.45), rgba(32,33,36,0.65) ),
            url('https://images.unsplash.com/photo-1516979187457-637abb4f9353?q=80&w=1600&auto=format&fit=crop') center/cover fixed no-repeat;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 40px 20px;
    }
    .container { width: min(1100px, 100%); }
    .hero { text-align: center; margin-bottom: 26px; }
    .title { font-size: clamp(26px, 4vw, 40px); font-weight: 700; color: #fff; text-shadow: 0 2px 20px rgba(0,0,0,0.35); margin-bottom:12px; }
    .subtitle { color: #e5e7eb; margin-bottom: 22px; }
    .search-wrap { display: flex; justify-content: center; }
    .search {
        width: min(820px, 100%);
        background: var(--card-bg);
        border-radius: 999px;
        padding: 14px;
        box-shadow: var(--card-shadow);
        display: flex;
        gap: 10px;
    }
    .search input {
        flex: 1; padding: 16px 20px; border: none; outline: none;
        font-size: 18px; border-radius: 999px; background: transparent;
    }
    .search button {
        padding: 14px 22px;
        border: none; border-radius: 999px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: white; font-weight: 600; cursor: pointer;
        box-shadow: 0 8px 20px rgba(44,123,229,0.45);
    }
    .alert {
        background: rgba(255,255,255,0.92);
        padding: 14px 16px;
        border-radius: var(--radius);
        margin-top: 16px;
        box-shadow: var(--card-shadow);
    }
    .alert.error { border-left: 6px solid var(--danger); }
    .alert.success { border-left: 6px solid var(--success); }
    .results {
        margin-top: 26px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
    }
    .card {
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 18px;
        box-shadow: var(--card-shadow);
        transition: transform .18s ease, box-shadow .22s ease;
        overflow: hidden;
    }
    .card:hover { transform: translateY(-4px); box-shadow: var(--card-shadow-hover); }
    .card .head {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: .12em;
        color: var(--muted);
        margin-bottom: 8px;
        font-weight: 700;
    }
    .card .value {
        font-size: 18px;
        font-weight: 600;
        word-break: break-word;
        overflow-wrap: anywhere;
    }
</style>
</head>
<body>
<div class="container">
    <div class="hero">
        <h1 class="title">School Info Explorer</h1>
        <p class="subtitle">Enter Affiliation Number to fetch school details from SARAS or local database.</p>
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
        <div class="card"><div class="head">Email</div><div class="value">{{ data.mail }}</div></div>
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
        try:
            with open(CSV_FILE, "a", encoding="utf-8", newline="") as f:
                new_row.to_csv(f, header=False, index=False)
            school_df = load_csv()  # reload with safe loader
        except PermissionError:
            print("⚠️ Permission denied while writing to CSV. Is the file open in Excel or locked by OneDrive?")


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
            data = fetch_from_cbse(aff_no)
            if data:
                save_to_csv(data)
            else:
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
