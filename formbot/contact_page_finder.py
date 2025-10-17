import logging
import time
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger("formbot")


class ContactPageFinder:
    CONTACT_KEYWORDS = [
        "contact", "support", "inquiry", "enquire",
        "quote", "book", "talk", "free case review",
        "consultation", "speak", "get in touch", "request a quote",
        "schedule", "appointment", "estimate", "demo", "request service",
    ]

    COMMON_PATHS = [
        "/contact", "/contact-us", "/contactus", "/contact.php",
        "/support", "/enquiry", "/consultation", "/get-in-touch",
        "/talk-to-us", "/free-case-review", "/book", "/schedule",
    ]

    NEWSLETTER_HINTS = ["newsletter", "subscribe", "sign up", "sign-up"]

    def __init__(self, driver, timeout=15, debug=False, max_runtime=30):
        self.driver = driver
        self.timeout = timeout
        self.debug = debug
        self.max_runtime = max_runtime

    def log(self, msg):
        if self.debug:
            logger.debug("[ContactPageFinder] %s", msg)

    # ---- core checks ----
    def _forms_on_page(self):
        """Collect forms including common framework containers (HubSpot, WP forms…)."""
        forms = self.driver.find_elements(By.TAG_NAME, "form")
        forms += self.driver.find_elements(By.CSS_SELECTOR,
            "#contact-form, .wpcf7-form, .elementor-form, .wpforms-form, "
            ".nf-form-layout, form.hs-form, .gform_wrapper, .hbspt-form form"
        )
        unique, seen = [], set()
        for f in forms:
            try:
                fid = f.get_attribute("outerHTML")
                if fid not in seen:
                    seen.add(fid)
                    unique.append(f)
            except Exception:
                unique.append(f)
        return unique

    def _looks_like_contact_form(self, form_element):
        try:
            text = (form_element.text or "").lower()
            if any(h in text for h in self.NEWSLETTER_HINTS):
                self.log("Rejected newsletter/subscribe form")
                return False

            inputs = form_element.find_elements(By.TAG_NAME, "input")
            textareas = form_element.find_elements(By.TAG_NAME, "textarea")

            visible_inputs = []
            for i in inputs:
                try:
                    if not i.is_displayed():
                        continue
                    t = (i.get_attribute("type") or "").lower()
                    if t in ["text", "email", "tel", "number", "search", ""] or not t:
                        visible_inputs.append(i)
                except Exception:
                    continue

            if not inputs and "hbspt-form" in (form_element.get_attribute("class") or ""):
                self.log("✔️ Accepting HubSpot form shell")
                return True

            if textareas:
                return True
            if len(visible_inputs) >= 2:
                return True
        except Exception:
            pass
        return False

    def _check_iframes(self):
        """Look for generic forms inside any iframe."""
        frames = self.driver.find_elements(By.TAG_NAME, "iframe")
        for idx, fr in enumerate(frames):
            try:
                self.log(f"Inspecting iframe #{idx}")
                self.driver.switch_to.frame(fr)

                for f in self._forms_on_page():
                    if self._looks_like_contact_form(f):
                        self.driver.switch_to.default_content()
                        self.log("✔️ Found generic form inside iframe")
                        return True

                if self.driver.find_elements(By.CSS_SELECTOR, ".hbspt-form"):
                    self.driver.switch_to.default_content()
                    self.log("✔️ Found HubSpot shell inside iframe")
                    return True

                self.driver.switch_to.default_content()
            except Exception as e:
                self.log(f"⚠️ Iframe error #{idx}: {e}")
                self.driver.switch_to.default_content()
                continue
        return False

    def _page_has_contact_form(self, max_wait=None):
        wait_time = max(max_wait or self.timeout, 4)
        end = time.time() + wait_time
        while time.time() < end:
            if self._check_iframes():
                self.log("✅ Form detected via iframe")
                return True

            for f in self._forms_on_page():
                if self._looks_like_contact_form(f):
                    self.log(f"✅ Found contact form on {self.driver.current_url}")
                    return True

            time.sleep(0.3)

        # Scroll retry
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            for f in self._forms_on_page():
                if self._looks_like_contact_form(f):
                    self.log("✔️ Found form after scrolling")
                    return True
        except Exception:
            pass

        self.log("❌ No form detected in window")
        return False

    # ---- strategies ----
    def on_homepage(self, base_url):
        self.log("→ Checking homepage")
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: self._page_has_contact_form(max_wait=8) or len(d.find_elements(By.TAG_NAME, "a")) > 0
            )
        except Exception:
            pass
        if self._page_has_contact_form(max_wait=8):
            return base_url
        return None

    def via_common_paths(self, base_url):
        self.log("→ Trying common contact paths")
        for path in self.COMMON_PATHS:
            candidate = urljoin(base_url, path)
            try:
                self.driver.get(candidate)
                time.sleep(1)
                if self._page_has_contact_form(max_wait=8):
                    return candidate
            except Exception:
                continue
        return None

    def via_links(self, base_url):
        self.log("→ Scanning contact/support links")
        anchors = self.driver.find_elements(By.TAG_NAME, "a")
        for a in anchors[:15]:
            try:
                txt = (a.text or "").strip().lower()
                href = (a.get_attribute("href") or "").strip()
                if not href:
                    continue
                href_low = href.lower()
                if any(k in txt for k in self.CONTACT_KEYWORDS) or any(k in href_low for k in self.CONTACT_KEYWORDS):
                    to = urljoin(base_url, href)
                    self.log(f"Trying link: {to}")
                    self.driver.get(to)
                    time.sleep(1)
                    if self._page_has_contact_form(max_wait=8):
                        return to
            except Exception:
                continue
        return None

    def via_popups(self, wait_time=8):
        self.log("→ Checking popups/iframes")
        end = time.time() + wait_time
        while time.time() < end:
            try:
                popups = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class,'modal') or contains(@class,'popup') or "
                    "contains(@class,'dialog') or contains(@class,'overlay')]"
                )
                for p in popups:
                    if p.is_displayed():
                        for f in p.find_elements(By.TAG_NAME, "form"):
                            if self._looks_like_contact_form(f):
                                self.log("✔️ Found form in popup")
                                return self.driver.current_url
            except Exception:
                pass

            if self._check_iframes():
                return self.driver.current_url

            time.sleep(0.3)
        return None

    def run(self, base_url):
        self.log(f"ContactPageFinder.run on {base_url}")
        start = time.time()

        for strategy in [self.via_links, self.via_common_paths, self.via_popups]:
            if time.time() - start > self.max_runtime:
                self.log("⏱ Max runtime exceeded, aborting")
                return None
            url = strategy(base_url)
            if url:
                return url

        self.debug_dump()
        self.log("✗ No contact form found")
        return None

    def debug_dump(self, max_len=400):
        try:
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            logger.debug(f"[ContactPageFinder] Found {len(forms)} <form> elements")
            for idx, f in enumerate(forms):
                try:
                    html = f.get_attribute("outerHTML") or ""
                    snippet = html[:max_len].replace("\n", " ")
                    logger.debug(f"[Form #{idx}] {snippet}...")
                except Exception as e:
                    logger.debug(f"[Form #{idx}] ⚠️ Could not read HTML: {e}")
        except Exception as e:
            logger.debug(f"[ContactPageFinder] Error fetching forms: {e}")

        try:
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            logger.debug(f"[ContactPageFinder] Found {len(frames)} <iframe> elements")
            for idx, fr in enumerate(frames):
                try:
                    src = fr.get_attribute("src")
                    fid = fr.get_attribute("id")
                    classes = fr.get_attribute("class")
                    logger.debug(f"[Iframe #{idx}] id={fid}, src={src}, class={classes}")
                except Exception as e:
                    logger.debug(f"[Iframe #{idx}] ⚠️ Could not read attributes: {e}")
        except Exception as e:
            logger.debug(f"[ContactPageFinder] Error fetching iframes: {e}")
