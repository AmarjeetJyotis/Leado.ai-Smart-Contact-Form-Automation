from selenium.webdriver.common.by import By
import logging, time

logger = logging.getLogger("formbot")

class SuccessChecker:
    SUCCESS_TEXTS = [
        "thank you", "thanks", "submitted", "successfully",
        "we will contact you", "message has been sent",
        "we’ll be in touch", "we will be in touch",
        "request received", "submission complete",
        "form received", "your message has been sent",
        "thank-you", "thankyou",
        "your submission has been received",
        "we’ll be in touch soon",
        "thanks for submitting the form",
        "we will get back to you shortly",
        "form submitted successfully",
        "your request has been received",
    ]

    SUCCESS_SELECTORS = [
        ".wpcf7-response-output", ".elementor-message-success", ".nf-response-msg",
        ".wpforms-confirmation-container", ".gform_confirmation_message",
        ".et-pb-contact-message", ".uagb-forms-success-message",
        ".hs-form-success", ".mktoThankYouMessage", ".alert-success",
        ".contact-success", ".success-message", ".submitted-message",
        ".hs-form-ease-in", "[data-test-id*='thank']",
        "#success", ".success", "#thankyou", ".thank-you"
    ]

    def __init__(self, driver, initial_url, had_form=True, before_html=""):
        self.driver = driver
        self.initial_url = initial_url
        self.had_form = had_form
        self.before_html = before_html.lower() if before_html else ""

    def _check_iframes_recursive(self, context=None, depth=0, max_depth=3):
        """Recursively check all iframes (HubSpot, Elementor, etc.)"""
        try:
            if depth > max_depth:
                return False
            frames = (context or self.driver).find_elements(By.TAG_NAME, "iframe")
            for idx, fr in enumerate(frames):
                try:
                    self.driver.switch_to.frame(fr)
                    html = self.driver.page_source.lower()
                    if any(t in html for t in self.SUCCESS_TEXTS):
                        logger.debug(f"[SuccessChecker] ✅ Success text found in iframe #{idx} depth={depth}")
                        self.driver.switch_to.default_content()
                        return True
                    # Recurse deeper (nested iframes)
                    if self._check_iframes_recursive(self.driver, depth + 1):
                        self.driver.switch_to.default_content()
                        return True
                    self.driver.switch_to.default_content()
                except Exception as e:
                    self.driver.switch_to.default_content()
                    logger.debug(f"[SuccessChecker] ⚠️ Failed iframe #{idx} depth={depth}: {e}")
        except Exception as e:
            logger.debug(f"[SuccessChecker] ⚠️ Iframe enumeration error: {e}")
        return False

    def _check_shadow_dom(self):
        """Scan shadow roots (Elementor/HubSpot often use this)."""
        try:
            script = """
            const texts = arguments[0];
            function deepSearch(node) {
                if (!node) return false;
                if (node.shadowRoot) {
                    if (deepSearch(node.shadowRoot)) return true;
                }
                for (const child of node.children || []) {
                    const txt = (child.innerText || '').toLowerCase();
                    if (texts.some(t => txt.includes(t))) return true;
                    if (deepSearch(child)) return true;
                }
                return false;
            }
            return deepSearch(document.body);
            """
            return self.driver.execute_script(script, self.SUCCESS_TEXTS)
        except Exception:
            return False

    def run(self, max_wait=15):
        if not self.had_form:
            logger.debug("[SuccessChecker] No form detected, skipping success check")
            return False

        end = time.time() + max_wait
        while time.time() < end:
            try:
                page = self.driver.page_source.lower()

                # 1️⃣ Direct text
                for t in self.SUCCESS_TEXTS:
                    if t in page and t not in self.before_html:
                        logger.debug(f"[SuccessChecker] ✅ Found success text: '{t}'")
                        return True

                # 2️⃣ CSS-based containers
                for sel in self.SUCCESS_SELECTORS:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for el in elements:
                            if el.is_displayed():
                                txt = (el.text or "").lower()
                                if any(k in txt for k in self.SUCCESS_TEXTS) or len(txt) > 5:
                                    logger.debug(f"[SuccessChecker] ✅ Found success element {sel}: '{txt[:60]}'")
                                    return True
                    except Exception:
                        continue

                # 3️⃣ Nested iframes
                if self._check_iframes_recursive():
                    return True

                # 4️⃣ Shadow DOM
                if self._check_shadow_dom():
                    logger.debug("[SuccessChecker] ✅ Found success inside shadow DOM")
                    return True

                # 5️⃣ URL redirect
                cur = self.driver.current_url.lower()
                if cur != self.initial_url.lower() and any(
                    k in cur for k in ["thank", "success", "submitted", "complete", "confirmation"]
                ):
                    logger.debug(f"[SuccessChecker] ✅ Redirected to success page: {cur}")
                    return True

            except Exception as e:
                logger.debug(f"[SuccessChecker] ⚠️ Error checking success: {e}")
                return False

            time.sleep(0.8)

        logger.debug("[SuccessChecker] ❌ No success detected after wait")
        return False
