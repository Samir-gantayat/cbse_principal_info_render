# CBSE Principal Info Scraper

This is a Flask web app to fetch CBSE school principal details using affiliation code.

## Run locally
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 in your browser.

## Deploy on Render
1. Push this project to GitHub.
2. Create a new Web Service on https://render.com.
3. Build Command:
```
pip install -r requirements.txt
```
4. Start Command:
```
gunicorn app:app
```
5. Select Free tier and deploy.
