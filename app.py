from flask import Flask, render_template_string, request
import pandas as pd
import requests
import os
from bs4 import BeautifulSoup

app = Flask(__name__)

CSV_FILE = "schools.csv"
MATCHED_FILE = "matched_schools.csv"
V2_FILE = "v2_data.csv"

REQUIRED_COLS = [
    "School Name", "Aff No", "Principal Name", "Principal Number",
    "Principal Email", "School Email", "Address", "Website",
    "Fee Structure", "Total Strength"
]

if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=REQUIRED_COLS).to_csv(CSV_FILE, index=False)
if not os.path.exists(MATCHED_FILE):
    pd.DataFrame(columns=["Aff No", "Person", "SCHOOL_ID"]).to_csv(MATCHED_FILE, index=False)
if not os.path.exists(V2_FILE):
    pd.DataFrame(columns=["SCHOOL_ID","Type of Round","Prelims Date","Reg","Part","Rep"]).to_csv(V2_FILE, index=False)

# Load CSVs
school_df = pd.read_csv(CSV_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("Not Found")
matched_df = pd.read_csv(MATCHED_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("")
v2_df = pd.read_csv(V2_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("Not Found")

HTML_PAGE = """ 
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>School Info Explorer</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Inter', sans-serif; background: #f3f4f6; margin:0; padding:20px; display:flex; justify-content:center; }
.container { width: min(900px,100%); }
.hero { text-align:center; margin-bottom:20px; }
.title { font-size:32px; font-weight:700; margin-bottom:10px; }
.subtitle { color:#555; margin-bottom:20px; }
.search-wrap { display:flex; justify-content:center; }
.search { width:100%; max-width:700px; display:flex; background:#fff; border-radius:50px; padding:8px; box-shadow:0 4px 12px rgba(0,0,0,0.1); }
.search input { flex:1; border:none; padding:12px 16px; font-size:16px; border-radius:50px; outline:none; }
.search button { background:linear-gradient(135deg, #2c7be5, #6c5ce7); border:none; color:#fff; font-weight:600; border-radius:50px; padding:12px 20px; cursor:pointer; }

.box { background:#fff; border-radius:14px; box-shadow:0 8px 20px rgba(0,0,0,0.1); padding:20px; margin-top:20px; }
.box h2 { font-size:20px; margin-bottom:15px; border-bottom:2px solid #eee; padding-bottom:5px; }
.info-row { margin:8px 0; }
.label { font-weight:600; color:#444; }
.value { margin-left:6px; color:#222; }
a.mail-link { color:#2c7be5; text-decoration:none; font-weight:600; }
a.mail-link:hover { text-decoration:underline; }
.journey-table { width:100%; border-collapse:collapse; margin-top:10px; }
.journey-table th, .journey-table td { border:1px solid #ccc; padding:6px 10px; text-align:left; }
.journey-table th { background:#f0f0f0; }

/* Popup styles */
.popup-bg { display:none; position:fixed; top:0; left:0; width:100%; height:100%; backdrop-filter: blur(6px); background: rgba(0,0,0,0.4); justify-content:center; align-items:center; z-index:1000; }
.popup { background:#fff; padding:20px; border-radius:12px; max-width:400px; width:90%; text-align:center; }
.popup button { margin:10px; padding:10px 20px; font-size:16px; cursor:pointer; border:none; border-radius:6px; color:#fff; }
.math-btn { background:#2c7be5; }
.hots-btn { background:#f39c12; }
.score-btn { background:#6c5ce7; }
.close-btn { margin-top:15px; background:#888; }
</style>
</head>
<body>
<div class="container">
<div class="hero">
<h1 class="title">School Info Explorer</h1>
<p class="subtitle">Enter Affiliation Number to fetch school details</p>
<form class="search-wrap" method="post">
<div class="search">
<input name="aff_no" placeholder="Enter Affiliation Number" required value="" />
<button type="submit">Search</button>
</div>
</form>
{% if error %}
<p style="color:red; margin-top:10px;"><strong>Error:</strong> {{ error }}</p>
{% endif %}
</div>

{% if data %}
<div class="box">
<h2>School Details</h2>
<div class="info-row"><span class="label">School Name:</span> <span class="value">{{ data.school_name }}</span></div>
<div class="info-row"><span class="label">Principal:</span> <span class="value">{{ data.principal_name }}</span></div>
<div class="info-row"><span class="label">Principal Contact:</span> <span class="value">{{ data.principal_number }}</span></div>
<div class="info-row"><span class="label">Principal Email:</span> <a class="mail-link" href="mailto:{{ data.principal_email }}">{{ data.principal_email }}</a></div>
<div class="info-row"><span class="label">School Email:</span> <a class="mail-link" href="mailto:{{ data.school_email }}">{{ data.school_email }}</a></div>
<div class="info-row"><span class="label">Total Strength:</span> <span class="value">{{ data.total_strength }}</span></div>
<div class="info-row"><span class="label">Fee Structure (Yearly):</span> <span class="value">{{ data.fee_structure }}</span></div>
<div class="info-row">
<button onclick="openMailPopup('{{ data.principal_email }}','{{ data.school_email }}','{{ data.school_name }}','{{ data.principal_name }}'); return false;">📧 Send Email</button>
</div>
</div>

<div class="box">
<h2>Other Information</h2>
<div class="info-row"><span class="label">Address:</span> <span class="value">{{ data.address }}</span></div>
<div class="info-row"><span class="label">Website:</span> <a href="{{ data.website }}" target="_blank">{{ data.website }}</a></div>
{% if data.school_code %}
<div class="info-row"><span class="label">School Code:</span> <span class="value">{{ data.school_code }}</span></div>
<div class="info-row"><span class="label">Lead Owner:</span> <span class="value">{{ data.lead_owner }}</span></div>
{% endif %}

{% if data.journey %}
<h3>Journey:</h3>
<table class="journey-table">
<tr>
<th>Round</th><th>Prelims Date</th><th>Registration</th><th>Participation</th><th>Rep</th>
</tr>
{% for r in data.journey %}
<tr>
<td>{{ r['Type of Round'] }}</td>
<td>{{ r['Prelims Date'] }}</td>
<td>{{ r['Reg'] }}</td>
<td>{{ r['Part'] }}</td>
<td>{{ r['Rep'] }}</td>
</tr>
{% endfor %}
</table>
{% endif %}

</div>
{% endif %}
</div>

<!-- Mail template popup -->
<div class="popup-bg" id="mailPopup">
<div class="popup">
<h3>Select Mail Template</h3>
<button class="math-btn" onclick="sendMail('math')">MATH</button>
<button class="hots-btn" onclick="sendMail('hots')">HOTS</button>
<button class="score-btn" onclick="sendMail('score')">SCORE</button>
<br>
<button class="close-btn" onclick="closePopup()">Cancel</button>
</div>
</div>

<script>
let currentMail = {};
function openMailPopup(principalEmail, schoolEmail, schoolName, principalName){
    currentMail = {principalEmail, schoolEmail, schoolName, principalName};
    document.getElementById('mailPopup').style.display='flex';
}
function closePopup(){ document.getElementById('mailPopup').style.display='none'; }

function capitalizeFirstLetter(str){
    return str.replace(/\b\w/g, c => c.toUpperCase());
}

function sendMail(template){
    let subj="", body="";
    let schoolName = capitalizeFirstLetter(currentMail.schoolName);
    let principalName = capitalizeFirstLetter(currentMail.principalName);

    if(template==="math"){
        subj="Invitation to Participate in MATH Test: Empowering Students through Assessment Excellence";
        body=`Dear ${principalName},\n\nWe are delighted to invite ${schoolName} to participate in the MATH Test.\nMode Of Exam: Online\n\nMotive: This free initiative offers students valuable aptitude, decision-making, and critical thinking exposure.\n\nThanks & Regards,\nName\nDesignation\n{user's mail id}`;
    } else if(template==="hots"){
        subj="Invitation to Participate in HOTS Test";
        body=`Dear ${principalName},\n\nWe are delighted to invite ${schoolName} to participate in the HOTS Test.\nMode Of Exam: Online\n\nMotive: This free initiative offers students valuable aptitude, decision-making, and critical thinking exposure.\n\nThanks & Regards,\nName\nDesignation\n{user's mail id}`;
    } else if(template==="score"){
        subj="Invitation to Participate in SCORE Test: Empowering Students through Assessment Excellence";
        body=`Dear ${principalName},\n\nWe are delighted to invite ${schoolName} to participate in the SCORE Test.\nMode Of Exam: Online\n\nMotive: This free initiative offers students valuable aptitude, decision-making, and critical thinking exposure.\n\nThanks & Regards,\nName\nDesignation\n{user's mail id}`;
    }

    let mailtoLink = `https://mail.google.com/mail/?view=cm&fs=1&to=${currentMail.principalEmail},${currentMail.schoolEmail}&su=${encodeURIComponent(subj)}&body=${encodeURIComponent(body)}`;
    window.open(mailtoLink,'_blank');
    closePopup();
}
</script>
</body>
</html>
"""

def fetch_from_cbse(aff_no):
    try:
        url = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        def get_val(_id):
            el = soup.find(id=_id)
            return el.get_text(strip=True) if el else "Not Found"

        total_strength = 0
        for i in range(1, 13):
            val = get_val(f"lblstu{i}")
            if val.isdigit():
                total_strength += int(val)

        adm = int(get_val("lblsecadm") or 0) if get_val("lblsecadm").isdigit() else 0
        dev = int(get_val("lblsecdev") or 0) if get_val("lblsecdev").isdigit() else 0
        oth = int(get_val("lblsecoth") or 0) if get_val("lblsecoth").isdigit() else 0
        tui = get_val("lblsectui")
        tui = int(tui) if tui.isdigit() else 0
        if 0 < tui < 10000:
            tui *= 12
        fee_total = adm + dev + oth + tui

        return {
            "school_name": get_val("lblsch_name"),
            "aff_no": aff_no,
            "principal_name": get_val("lblprinci"),
            "principal_number": get_val("lblprincicon"),
            "principal_email": get_val("lblprinciemail"),
            "school_email": get_val("lblschemail"),
            "address": get_val("lbladd"),
            "website": get_val("lblschweb"),
            "fee_structure": str(fee_total),
            "total_strength": str(total_strength),
            "saras_link": url,
        }
    except Exception as e:
        print("Error fetching CBSE:", e)
        return None

def save_to_csv(data):
    global school_df
    # Normalize values for uniqueness
    aff_no_val = str(data["aff_no"]).strip()
    if not (school_df["Aff No"].astype(str).str.strip() == aff_no_val).any():
        new_row = pd.DataFrame([{
            "School Name": data["school_name"],
            "Aff No": data["aff_no"],
            "Principal Name": data["principal_name"],
            "Principal Number": data["principal_number"],
            "Principal Email": data["principal_email"],
            "School Email": data["school_email"],
            "Address": data["address"],
            "Website": data["website"],
            "Fee Structure": data["fee_structure"],
            "Total Strength": data["total_strength"],
        }])
        new_row.to_csv(CSV_FILE, mode="a", header=False, index=False)
        school_df = pd.read_csv(CSV_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("Not Found")

def get_school_data(aff_no):
    global school_df
    aff_no = str(aff_no).strip()
    
    # Check if it already exists
    row = school_df.loc[school_df["Aff No"].astype(str).str.strip() == aff_no]
    if not row.empty:
        # Already exists, return existing data
        row = row.iloc[0]
        return {
            "school_name": row["School Name"],
            "principal_name": row["Principal Name"],
            "principal_number": row["Principal Number"],
            "principal_email": row["Principal Email"],
            "school_email": row["School Email"],
            "address": row["Address"],
            "website": row["Website"],
            "fee_structure": row["Fee Structure"],
            "total_strength": row["Total Strength"],
        }
    
    # Else fetch from Saras
    data = fetch_from_cbse(aff_no)
    if data:
        save_to_csv(data)
    return data

@app.route("/", methods=["GET","POST"])
def index():
    global school_df, matched_df, v2_df
    data, error = None, None
    if request.method=="POST":
        aff_no = request.form.get("aff_no","").strip()
        if not aff_no:
            error = "Please enter a valid Affiliation Number."
        else:
            data = fetch_from_cbse(aff_no)
            if not data:
                row = school_df.loc[school_df["Aff No"]==aff_no]
                if row.empty:
                    error = "No information found for this Affiliation Number."
                else:
                    row = row.iloc[0]
                    data = {
                        "school_name": row["School Name"],
                        "principal_name": row["Principal Name"],
                        "principal_number": row["Principal Number"],
                        "principal_email": row["Principal Email"],
                        "school_email": row["School Email"],
                        "address": row["Address"],
                        "website": row["Website"],
                        "fee_structure": row["Fee Structure"],
                        "total_strength": row["Total Strength"],
                        "saras_link": f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
                    }
            else:
                save_to_csv(data)

            # Existing lead check
            row = matched_df.loc[matched_df["Aff No"]==aff_no]
            if not row.empty:
                person = row.iloc[0].get("Person","Assigned")
                school_code = row.iloc[0].get("SCHOOL_ID","")
                data["lead_status"] = f"Existing Lead — with {person}"
                data["school_code"] = school_code

                # Journey data
                rounds_df = v2_df.loc[v2_df["SCHOOL_ID"]==school_code]
                if not rounds_df.empty:
                    rounds_df = rounds_df.drop_duplicates(subset=["Type of Round","Prelims Date","Reg","Part","Rep"])
                    rounds_df = rounds_df[~rounds_df["Rep"].str.lower().isin(["canceled","duplicate"])]
                    for col in ["Prelims Date","Reg","Part"]:
                        if col in rounds_df.columns:
                            rounds_df[col] = rounds_df[col].replace("", "Not Found").fillna("Not Found")
                        else:
                            rounds_df[col] = "Not Found"
                    rounds_list=[]
                    for idx,r in rounds_df.iterrows():
                        rounds_list.append({
                            "Type of Round": r["Type of Round"],
                            "Prelims Date": r["Prelims Date"],
                            "Reg": r["Reg"],
                            "Part": r["Part"],
                            "Rep": r["Rep"]
                        })
                    data["journey"] = rounds_list
                    data["lead_owner"] = rounds_df.iloc[-1]["Rep"]

    return render_template_string(HTML_PAGE, data=data, error=error)

if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

