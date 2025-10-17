import logging, re, subprocess, tempfile, shutil, atexit, os, uuid
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger("formbot")

def _detect_chrome_version_full():
    for bin_path in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
        try:
            result = subprocess.run([bin_path, "--version"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out = (result.stdout or result.stderr or "").strip()
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)
        except Exception:
            continue
    return None

class DriverManager:
    @staticmethod
    def get_driver(headless=True):
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,900")
        options.add_argument("user-agent=Mozilla/5.0")

        # 👉 only use --user-data-dir in NON-headless mode
        tmp_profile = None
        if not headless:
            tmp_profile = tempfile.mkdtemp(prefix=f"chrome_profile_{uuid.uuid4().hex}_")
            options.add_argument(f"--user-data-dir={tmp_profile}")
            logger.debug(f"[driver] Using temp profile {tmp_profile}")

        if headless:
             options.add_argument("--headless=new")

        version_full = _detect_chrome_version_full()
        service = Service(
            ChromeDriverManager(driver_version=version_full).install() if version_full
            else ChromeDriverManager().install()
        )

        driver = webdriver.Chrome(service=service, options=options)
        driver._tmp_profile = tmp_profile

        # ensure cleanup always happens
        if tmp_profile:
            atexit.register(lambda: shutil.rmtree(tmp_profile, ignore_errors=True))

        driver.set_page_load_timeout(60)
        driver.implicitly_wait(2)
        return driver

    @staticmethod
    def cleanup(driver):
        try:
            tmp_profile = getattr(driver, "_tmp_profile", None)
            driver.quit()
            if tmp_profile:
                shutil.rmtree(tmp_profile, ignore_errors=True)
                logger.debug(f"[driver] Cleaned up temp profile {tmp_profile}")
        except Exception as e:
            logger.warning(f"[driver] Cleanup failed: {e}")
