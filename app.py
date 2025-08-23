from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

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

    /* Hero search */
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

    /* Results Grid */
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
        overflow-wrap: anywhere;  /* ensures long text (emails, URLs, address) wraps inside */
    }
</style>
</head>
<body>
<div class="container">
    <div class="hero">
        <h1 class="title">School Info Explorer</h1>
        <p class="subtitle">Enter Affiliation Number to fetch school details, principal info, students, and fees.</p>

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
        <div class="card"><div class="head">Principal Name</div><div class="value">{{ data.principal_name }}</div></div>
        <div class="card"><div class="head">Principal Contact</div><div class="value">{{ data.principal_contact }}</div></div>
        <div class="card"><div class="head">Principal Email</div><div class="value">{{ data.principal_email }}</div></div>
        <div class="card"><div class="head">School Email</div><div class="value">{{ data.school_email }}</div></div>
        <div class="card"><div class="head">Address</div><div class="value">{{ data.address }}</div></div>
        <div class="card"><div class="head">Website</div><div class="value">
            {% if data.website and data.website != 'Not Found' %}
                <a href="{{ data.website if data.website.startswith('http') else 'http://' + data.website }}" target="_blank">{{ data.website }}</a>
            {% else %} Not Found {% endif %}
        </div></div>
        <div class="card"><div class="head">Total Students</div><div class="value">{{ data.total_students }}</div></div>
        <div class="card"><div class="head">Fee Structure (₹)</div><div class="value">
            {% if data.fee_structure is not none %}
                ₹ {{ "{:,}".format(data.fee_structure) }}
            {% else %} Not Available {% endif %}
        </div></div>
    </section>
    {% endif %}
</div>
</body>
</html>
"""

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
    if sec_adm: fee += sec_adm

    if sec_tui:
        if len(str(sec_tui)) == 3:  # 3-digit tuition → multiply by 12
            fee += sec_tui * 12
        else:  # 4+ digits → use directly
            fee += sec_tui

    if sec_oth: fee += sec_oth
    if sec_dev: fee += sec_dev

    return fee if fee > 0 else None

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
