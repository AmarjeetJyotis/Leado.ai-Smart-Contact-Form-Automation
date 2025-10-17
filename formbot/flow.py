import logging
import time
from formbot.driver_manager import DriverManager
from formbot.contact_page_finder import ContactPageFinder
from formbot.form_filler import FormFiller
from formbot.submit_handler import SubmitHandler
from formbot.success_checker import SuccessChecker
from selenium.webdriver.common.by import By

logger = logging.getLogger("formbot")


def _dismiss_overlays(driver):
    """Actively accept cookie banners and remove chat/overlay blockers."""
    try:
        # 1) Try visible "Accept/Agree" buttons
        xpath_text_buttons = [
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
            "//*[@id='onetrust-accept-btn-handler']",
            "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
            "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
        ]
        for xp in xpath_text_buttons:
            for el in driver.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed() and el.is_enabled():
                        el.click()
                        time.sleep(0.2)
                        return
                except Exception:
                    continue

        # 2) Try iframes for cookie banners
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for fr in frames[:4]:
            try:
                src = (fr.get_attribute("src") or "").lower()
                if any(k in src for k in ["consent", "cookie", "privacy", "onetrust"]):
                    driver.switch_to.frame(fr)
                    clicked = False
                    for xp in xpath_text_buttons:
                        for el in driver.find_elements(By.XPATH, xp):
                            if el.is_displayed() and el.is_enabled():
                                el.click()
                                clicked = True
                                break
                        if clicked:
                            break
                    driver.switch_to.default_content()
                    if clicked:
                        time.sleep(0.2)
                        return
                else:
                    driver.switch_to.frame(fr)
                    for xp in xpath_text_buttons[:2]:
                        for el in driver.find_elements(By.XPATH, xp):
                            if el.is_displayed() and el.is_enabled():
                                el.click()
                                driver.switch_to.default_content()
                                time.sleep(0.2)
                                return
                    driver.switch_to.default_content()
            except Exception:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass

        # 3) Remove overlays if clicking didn’t work
        overlays = [
            "#onetrust-banner-sdk", "#onetrust-policy-text",
            ".cookie", "[id*='cookie']", "[class*='cookie']",
            ".cc-window", ".cc-banner", ".osano-cm-window",
            ".consent", ".gdpr", ".cm-root", ".sp-privacy-manager",
        ]
        for sel in overlays:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    driver.execute_script("arguments[0].remove();", el)
                except Exception:
                    pass

        # 4) Remove chat widgets
        chats = [
            "iframe[src*='intercom']", "iframe[src*='drift']", "iframe[src*='hubspot']",
            "iframe[src*='tawk']", "iframe[src*='livechat']", "iframe[id*='launcher']",
            ".chat-widget", ".launcher__button", ".chatbot", ".chat-container"
        ]
        for sel in chats:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    driver.execute_script("arguments[0].remove();", el)
                except Exception:
                    pass
    except Exception:
        pass


def _has_captcha(driver):
    try:
        if driver.find_elements(By.CSS_SELECTOR, ".g-recaptcha, .h-captcha, .cf-challenge, .cf-turnstile"):
            return True
        if driver.find_elements(
            By.XPATH,
            "//iframe[contains(@src,'captcha') or contains(@src,'recaptcha') or contains(@src,'hcaptcha') or contains(@src,'turnstile')]"
        ):
            return True
    except Exception:
        pass
    return False


class FormFlow:
    def __init__(self, url, dataset, debug=False):
        self.url = url if url.startswith("http") else "https://" + url
        self.dataset = dataset
        self.debug = debug

    def run(self):
        try:
            driver = DriverManager.get_driver(headless=not self.debug)
        except Exception as e:
            logger.exception("Chrome launch failed for %s", self.url)
            return f"[Error] Could not start Chrome for {self.url}: {e}"

        had_form = False
        before_html = ""

        try:
            driver.get(self.url)

            # Ensure DOM ready
            try:
                for _ in range(20):
                    if driver.execute_script("return document.readyState") == "complete":
                        break
                    time.sleep(0.25)
            except Exception:
                pass

            _dismiss_overlays(driver)
            before_html = driver.page_source

            # 1) Find a contact form page
            finder = ContactPageFinder(driver, timeout=10, debug=self.debug)
            contact_url = finder.run(self.url)
            if not contact_url:
                DriverManager.cleanup(driver)
                # ✅ green success for no form case
                GREEN = "\033[92m"
                RESET = "\033[0m"
                return f"{GREEN}[✓] Email sent (no contact form found for {self.url}){RESET}"

            if driver.current_url.rstrip("/") != contact_url.rstrip("/"):
                driver.get(contact_url)
                time.sleep(1.2)

            _dismiss_overlays(driver)

            # 2) Captcha guard
            if _has_captcha(driver):
                DriverManager.cleanup(driver)
                return f"[X] Captcha/Anti-bot detected on {contact_url}"

            # 3) Fill form(s)
            filler = FormFiller(driver, self.dataset)
            hubspot_used = filler.run()
            had_form = True

            # 4) Submit
            submitter = SubmitHandler(driver, timeout=14)
            submitter.run()

            # 5) Post-submit wait
            time.sleep(3)
            _dismiss_overlays(driver)

            # 6) Success check
            checker = SuccessChecker(driver, contact_url, had_form=had_form, before_html=before_html)
            if checker.run():
                DriverManager.cleanup(driver)
                return f"[✓] {'HubSpot ' if hubspot_used else ''}form submitted and confirmed on {contact_url}"

            # Retry multi-step forms
            hubspot_used2 = filler.run()
            submitter.run()
            time.sleep(2.5)
            if checker.run():
                DriverManager.cleanup(driver)
                return f"[✓] {'HubSpot ' if (hubspot_used or hubspot_used2) else ''}form submitted and confirmed on {contact_url}"

            DriverManager.cleanup(driver)
            return f"[X] Submitted (attempted) but no confirmation on {contact_url}"

        except Exception as e:
            try:
                DriverManager.cleanup(driver)
            except Exception:
                pass
            logger.exception("Unhandled exception in flow for %s", self.url)
            return f"[Error] On {self.url}: {e}"
