import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, request, send_from_directory
from openai import OpenAI

from formbot.driver_manager import DriverManager
from formbot.flow import FormFlow
from formbot.contact_page_finder import ContactPageFinder


# ---------------------------------------------------------------------
# Flask + Logging Setup
# ---------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static")

LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("formbot")

# ---------------------------------------------------------------------
# OpenAI Client Setup
# ---------------------------------------------------------------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    logger.warning("⚠️  OPENAI_API_KEY not set in environment.")
else:
    logger.info(f"🔑 Using OpenAI key prefix: {OPENAI_KEY[:8]}*******")

client = OpenAI(api_key=OPENAI_KEY)


# ---------------------------------------------------------------------
# Helper: Extract Website Text
# ---------------------------------------------------------------------
def get_website_text(url: str) -> str:
    """Fetch visible text from a website for context."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        texts = [t.strip() for t in soup.stripped_strings]
        return " ".join(texts[:1500])
    except Exception as e:
        logger.error(f"Failed to fetch website text from {url}: {e}")
        return f"Error fetching website: {e}"


# ---------------------------------------------------------------------
# Helper: Generate AI Pitch with Error Handling
# ---------------------------------------------------------------------
def generate_pitch(website_text, company, email, phone, service) -> str:
    """Generate a short business pitch using OpenAI API with strong error handling."""
    prompt = f"""
    You are a marketing assistant. Based on the website content below, write a professional pitch 
    from "{company}" offering "{service}" services.

    Requirements:
    - Start with a friendly intro.
    - Mention something relevant about the target business.
    - Explain how {company} can help them with {service}.
    - End with contact details: Email {email}, Phone {phone}.
    - Max 200 words.

    Website content:
    {website_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        msg = str(e)
        if "insufficient_quota" in msg:
            logger.error("❌ OpenAI quota exhausted — please add billing.")
            return "[OpenAI Error] Quota exhausted. Please add billing or credits."
        elif "invalid_api_key" in msg:
            logger.error("❌ Invalid OpenAI API key.")
            return "[OpenAI Error] Invalid API key."
        else:
            logger.error(f"❌ OpenAI Error: {msg}")
            return f"[OpenAI Error] {msg}"


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.route("/")
def index():
    """Serve static homepage."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health")
def health():
    """Quick health check for API key and connectivity."""
    try:
        client.models.list()
        return {"status": "✅ OpenAI key working and has quota."}, 200
    except Exception as e:
        return {"status": f"❌ OpenAI error: {str(e)}"}, 500


@app.route("/fill")
def fill():
    """Main route to process target URLs and generate personalized pitches."""
    raw_urls = request.args.get("urls", "").strip()
    name = request.args.get("name", "").strip() or "Test User"
    email = request.args.get("email", "").strip() or "test@example.com"
    phone = request.args.get("phone", "").strip() or "9999999999"
    service = request.args.get("service", "").strip() or "Digital Marketing"
    debug = request.args.get("debug", "false").lower() == "true"

    urls: List[str] = [u.strip() for u in raw_urls.split(",") if u.strip()]
    if not urls:
        def empty_stream():
            yield f"data: {json.dumps({'url': '', 'status': '[X] No URLs provided'})}\n\n"
            yield "event: done\ndata: No URLs\n\n"
        return Response(empty_stream(), mimetype="text/event-stream")

    def stream():
        for url in urls:
            try:
                logger.info(f"🌐 Processing URL: {url}")
                website_text = get_website_text(url)
                pitch = generate_pitch(website_text, name, email, phone, service)

                dataset = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "message": pitch,
                    "zipcode": "12345",
                    "address": "123 St",
                    "city": "MindAptix",
                    "state": "MindAptix",
                }

                status = FormFlow(url, dataset, debug=debug).run()

                if "No contact form found" in str(status) or "✗" in str(status):
                    try:
                        driver = DriverManager.get_driver(headless=not debug)
                        driver.get(url)
                        finder = ContactPageFinder(driver, debug=True)
                        finder.debug_dump()
                    except Exception as inner_e:
                        logger.error(f"Debug dump failed for {url}: {inner_e}")
                    finally:
                        try:
                            DriverManager.cleanup(driver)
                        except Exception:
                            pass

            except Exception as e:
                logger.exception(f"Flow crashed for {url}")
                status = f"[Error] On {url}: {e}"

            yield f"data: {json.dumps({'url': url, 'status': status})}\n\n"
            time.sleep(0.25)

        yield "event: done\ndata: All URLs processed\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------
if __name__ == "__main__":
    Path(app.static_folder).mkdir(parents=True, exist_ok=True)
    logger.info("🚀 FormAI Bot Server started on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
