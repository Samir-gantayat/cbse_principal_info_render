from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>CBSE Principal Info</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        input, button { padding: 8px; margin: 5px; }
        button { cursor: pointer; }
        .result { margin-top: 20px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
    </style>
</head>
<body>
    <h2>Enter Affiliation Code</h2>
    <form method="post">
        <input type="text" name="aff_no" placeholder="Enter Affiliation No" required>
        <button type="submit">Fetch Info</button>
    </form>
    {% if data %}
    <div class="result">
        <h3>Result:</h3>
        <ul>
            <li><b>Principal Name:</b> {{ data.principal_name }}</li>
            <li><b>Principal Contact:</b> {{ data.principal_contact }}</li>
            <li><b>Principal Email:</b> {{ data.principal_email }}</li>
        </ul>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    data = None
    if request.method == "POST":
        aff_no = request.form["aff_no"]
        url = f"https://saras.cbse.gov.in/maps/finalreportDetail?AffNo={aff_no}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        data = {
            "principal_name": soup.find("span", id="lblprinci").text.strip() if soup.find("span", id="lblprinci") else "Not Found",
            "principal_contact": soup.find("span", id="lblprincicon").text.strip() if soup.find("span", id="lblprincicon") else "Not Found",
            "principal_email": soup.find("span", id="lblprinciemail").text.strip() if soup.find("span", id="lblprinciemail") else "Not Found"
        }

    return render_template_string(HTML_PAGE, data=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
