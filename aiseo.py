from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load API key from .env file
load_dotenv()
app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Step 1: Scrape website text ---
def get_website_text(url):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = [t.strip() for t in soup.stripped_strings]
        return " ".join(texts[:1500])
    except Exception as e:
        return f"Error fetching website: {e}"

# --- Step 2: Extract SEO keywords ---
def extract_keywords(website_text, service):
    prompt = f"""
    You are an SEO expert. Based on this website content, extract 8-12 highly relevant SEO keywords 
    that can help the business grow online. Prioritize keywords related to {service} 
    and their industry. Return them as a comma-separated list.

    Website content:
    {website_text}
    """

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content.strip()

# --- Step 3: Generate pitch (with optional SEO keywords) ---
def generate_pitch(website_text, company, email, phone, service, use_seo=False):
    keywords = None
    if use_seo:
        keywords = extract_keywords(website_text, service)

    prompt = f"""
    You are a marketing assistant. Based on the following website content, write a professional pitch 
    from the company "{company}" offering their "{service}" services.

    The pitch should:
    - Start with a friendly intro.
    - Mention something relevant about the target business (based on website content).
    - Explain how {company} can help them with {service}.
    - If SEO keywords are provided, include a separate highlighted line before contact details in this exact format:
      📌 Targeted SEO Keywords: keyword1, keyword2, keyword3
    - End with contact details: Email {email}, Phone {phone}.
    - Keep it under 200 words.

    SEO Keywords: {keywords if keywords else "N/A"}

    Website content:
    {website_text}
    """

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    return resp.choices[0].message.content

# --- Step 4: Flask routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        url = request.form.get("url")
        company = request.form.get("company")
        email = request.form.get("email")
        phone = request.form.get("phone")
        service = request.form.get("service")
        use_seo = request.form.get("use_seo") == "on"  # checkbox for SEO keywords

        website_text = get_website_text(url)
        result = generate_pitch(website_text, company, email, phone, service, use_seo)

    return render_template("index.html", result=result, company=request.form.get("company"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)
