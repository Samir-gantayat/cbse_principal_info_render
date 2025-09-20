from flask import Flask, render_template, request, jsonify, send_file
app = Flask(__name__)
import pandas as pd
from io import BytesIO
import os, re
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import zipfile
from fpdf import FPDF  # <-- Added import for FPDF


app = Flask(__name__)

# -------------------- Student Data Preparation --------------------
def clean_name(name):
    name = name.replace('.', ' ')
    name = re.sub(r'[,\d/]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name.title()

@app.route("/api/prepare-data", methods=["POST"])
def prepare_data():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    school_id = request.form.get("school_id", "").strip()
    school_name = request.form.get("school_name", "").strip()
    class_offset = int(request.form.get("class_offset", 0))

    if not school_id or not school_name:
        return jsonify({"error": "School ID and School Name are required"}), 400

    try:
        df = pd.read_excel(file)

        name_col = "Name Of The Student"
        class_col = "Class"
        phone_col = "WhatsApp No (Provide your correct WhatsApp Number)\n(Login Id & password Will Be Shared On whatsapp Only)"

        if not all(col in df.columns for col in [name_col, class_col, phone_col]):
            return jsonify({"error": "Missing required columns"}), 400

        def extract_grade(class_value):
            match = re.search(r'\d+', str(class_value))
            return int(match.group(0)) if match else 0

        updated_grades = [extract_grade(c) + class_offset for c in df[class_col]]
        cleaned_names = df[name_col].astype(str).apply(clean_name)

        output_df = pd.DataFrame({
            "isd_code": ["91"] * len(df),
            "first_name": cleaned_names,
            "last_name": "",
            "grade": updated_grades,
            "phone": df[phone_col],
            "school_id": [school_id] * len(df),
        })

        safe_school_name = school_name.replace(" ", "_")
        out_path = f"{safe_school_name}.csv"
        output_df.to_csv(out_path, index=False)

        return send_file(out_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- CSV Setup --------------------
CSV_FILE = "schools.csv"
MATCHED_FILE = "matched_schools.csv"
V2_FILE = "v2_data.csv"

REQUIRED_COLS = [
    "School Name", "Aff No", "UDISE Code", "Principal Name", "Principal Number",
    "Principal Email", "School Email", "Address", "Pincode", "Website",
    "Fee Structure", "Total Strength"
]

# Ensure CSV files exist
for file, cols in [(CSV_FILE, REQUIRED_COLS), 
                   (MATCHED_FILE, ["Aff No", "Person", "SCHOOL_ID"]),
                   (V2_FILE, ["SCHOOL_ID", "Type of Round", "Prelims Date", "Reg", "Part", "Rep"])]:
    if not os.path.exists(file):
        pd.DataFrame(columns=cols).to_csv(file, index=False)

# Reload CSVs
def reload_dataframes():
    global school_df, matched_df, v2_df
    school_df = pd.read_csv(CSV_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("Not Found")
    matched_df = pd.read_csv(MATCHED_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("")
    v2_df = pd.read_csv(V2_FILE, dtype=str, on_bad_lines="skip", engine="python").fillna("Not Found")

reload_dataframes()

# -------------------- CBSE Fetch --------------------
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

        # Student strength
        total_strength = sum(int(get_val(f"lblstu{i}")) if get_val(f"lblstu{i}").isdigit() else 0 for i in range(1, 13))

        # Fee Structure
        adm = int(get_val("lblsecadm")) if get_val("lblsecadm").isdigit() else 0
        dev = int(get_val("lblsecdev")) if get_val("lblsecdev").isdigit() else 0
        oth = int(get_val("lblsecoth")) if get_val("lblsecoth").isdigit() else 0
        tui = int(get_val("lblsectui")) if get_val("lblsectui").isdigit() else 0
        if 0 < tui < 10000:
            tui *= 12
        fee_total = adm + dev + oth + tui

        return {
            "school_name": get_val("lblsch_name"),
            "aff_no": aff_no,
            "udise_code": get_val("txtudise"),
            "principal_name": get_val("lblprinci"),
            "principal_number": get_val("lblprincicon"),
            "principal_email": get_val("lblprinciemail"),
            "school_email": get_val("lblschemail"),
            "address": get_val("lbladd"),
            "pincode": get_val("txtpin"),
            "website": get_val("lblschweb"),
            "fee_structure": str(fee_total),
            "total_strength": str(total_strength),
            "saras_link": url,
        }
    except Exception as e:
        print("Error fetching CBSE:", e)
        return None

# -------------------- Save to CSV --------------------
def save_to_csv(data):
    reload_dataframes()
    aff_no_val = str(data.get("aff_no", "")).strip()
    if aff_no_val == "":
        return
    if not (school_df["Aff No"].astype(str).str.strip() == aff_no_val).any():
        new_row = pd.DataFrame([{
            "School Name": data.get("school_name", "Not Found"),
            "Aff No": aff_no_val,
            "UDISE Code": data.get("udise_code", "Not Found"),
            "Principal Name": data.get("principal_name", "Not Found"),
            "Principal Number": data.get("principal_number", "Not Found"),
            "Principal Email": data.get("principal_email", "Not Found"),
            "School Email": data.get("school_email", "Not Found"),
            "Address": data.get("address", "Not Found"),
            "Pincode": data.get("pincode", "Not Found"),
            "Website": data.get("website", "Not Found"),
            "Fee Structure": data.get("fee_structure", "Not Found"),
            "Total Strength": data.get("total_strength", "Not Found"),
        }])
        new_row.to_csv(CSV_FILE, mode="a", header=False, index=False)
        reload_dataframes()

# -------------------- Attach lead/journey --------------------
def attach_lead_and_journey(data, aff_no):
    reload_dataframes()
    row = matched_df.loc[matched_df["Aff No"] == aff_no]
    if not row.empty:
        person = row.iloc[0].get("Person", "Assigned")
        school_code = row.iloc[0].get("SCHOOL_ID", "")
        data["lead_status"] = f"Existing Lead — with {person}"
        data["school_code"] = school_code
        if school_code:
            rounds_df = v2_df.loc[v2_df["SCHOOL_ID"] == school_code]
            if not rounds_df.empty:
                rounds_df = rounds_df.drop_duplicates(subset=["Type of Round","Prelims Date","Reg","Part","Rep"])
                rounds_df = rounds_df[~rounds_df["Rep"].str.lower().isin(["canceled","duplicate"])]
                rounds_list = []
                for _, r in rounds_df.iterrows():
                    rounds_list.append({
                        "Type of Round": r.get("Type of Round","Not Found"),
                        "Prelims Date": r.get("Prelims Date","Not Found"),
                        "Reg": r.get("Reg","Not Found"),
                        "Part": r.get("Part","Not Found"),
                        "Rep": r.get("Rep","Not Found")
                    })
                data["journey"] = rounds_list
                data["lead_owner"] = rounds_df.iloc[-1].get("Rep","")
                # eligible_after
                prelims_dates = []
                for r in rounds_list:
                    date_str = r.get("Prelims Date")
                    if date_str and date_str not in ["","Not Found"]:
                        for fmt in ("%d-%b-%Y","%d-%m-%Y","%Y-%m-%d"):
                            try:
                                prelims_dates.append(datetime.strptime(date_str,fmt))
                                break
                            except: 
                                continue
                if prelims_dates:
                    data["eligible_after"] = (max(prelims_dates)+timedelta(days=90)).strftime("%Y-%m-%d")
                else:
                    data["eligible_after"] = "Not Available"
    return data

# -------------------- API Routes --------------------
@app.route("/api/school/<aff_no>", methods=["GET"])
def get_school(aff_no):
    aff_no = aff_no.strip()
    if not aff_no:
        return jsonify({"error": "Affiliation number required"}), 400

    data = fetch_from_cbse(aff_no)
    if not data:
        reload_dataframes()
        row = school_df.loc[school_df["Aff No"]==aff_no]
        if row.empty:
            return jsonify({"error": "No information found"}),404
        row = row.iloc[0]
        data = {k.lower(): row.get(k,"Not Found") for k in school_df.columns}
        data["aff_no"] = aff_no
        data["saras_link"] = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
    else:
        save_to_csv(data)

    data = attach_lead_and_journey(data, aff_no)
    return jsonify(data)

# -------------------- Prepare PDF --------------------
@app.route("/api/prepare-pdf", methods=["POST"])
def prepare_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    school_name = request.form.get("school_name", "").strip()
    exam_date = request.form.get("exam_date", "").strip()
    exam_time = request.form.get("exam_time", "").strip()

    if not school_name or not exam_date or not exam_time:
        return jsonify({"error": "All fields are required"}), 400

    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip().str.upper()
        df["PASSWORD"] = "qwerty"
        final_df = df[["NAME","GRADE","LOGIN ID","ATTEMPT"]]
        grades = final_df["GRADE"].unique()

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer,'w') as zip_file:
                for grade in grades:
                    grade_data = final_df[final_df["GRADE"]==grade]

                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial",'B',14)
                    pdf.cell(200,10,school_name,ln=True,align="C")
                    pdf.cell(200,10,f"Exam Date: {exam_date} | Time: {exam_time}",ln=True,align="C")
                    pdf.cell(200,10,f"Grade: {grade}",ln=True,align="C")
                    pdf.ln(10)

                    # Table Header
                    pdf.set_font("Arial",'B',10)
                    headers = ["Name","Login","Grade","Login ID","Attempt"]
                    col_widths = [55,45,20,40,30]
                    pdf.set_fill_color(0,51,102)
                    pdf.set_text_color(255,255,255)
                    for i,h in enumerate(headers):
                        pdf.cell(col_widths[i],10,h,border=1,align="C",fill=True)
                    pdf.ln()
                    pdf.set_text_color(0,0,0)
                    pdf.set_font("Arial",'',9)

                    for _,row in grade_data.iterrows():
                        pdf.cell(col_widths[0],10,str(row["NAME"]),border="TB",align="C")
                        link_url = f"https://genius.infinitylearn.com/deeplink/exampage?exam_status=scheduled&crnId=CRNP100T99999ZS11B75&eventId=68c554a4218f83652c697938&id={row['LOGIN ID']}&password=qwerty"
                        pdf.set_text_color(0,51,153)
                        pdf.cell(col_widths[1],10,"Click here to login",border="TB",align="C",link=link_url)
                        pdf.set_text_color(0,0,0)
                        pdf.cell(col_widths[2],10,str(row["GRADE"]),border="TB",align="C")
                        pdf.cell(col_widths[3],10,str(row["LOGIN ID"]),border="TB",align="C")
                        attempt_val = str(row["ATTEMPT"])
                        if attempt_val.lower()=="no": pdf.set_text_color(200,0,0)
                        elif attempt_val.lower()=="yes": pdf.set_text_color(0,150,0)
                        pdf.cell(col_widths[4],10,attempt_val,border="TB",align="C")
                        pdf.set_text_color(0,0,0)
                        pdf.ln()

                    # ✅ Fix here
                    pdf_content = pdf.output(dest="S").encode("latin1")
                    zip_file.writestr(f"Grade_{grade}.pdf", pdf_content)

        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name=f"{school_name}_PDFs.zip")

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# -------------------- Root Route --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
