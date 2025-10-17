from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time


class SubmitHandler:
    def __init__(self, driver, timeout=12):
        self.driver = driver
        self.timeout = timeout

    # ---------- Helpers ----------
    def safe_click(self, el):
        """Try multiple click methods safely"""
        try:
            WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable(el))
            el.click()
            return True
        except Exception:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            pass
        try:
            ActionChains(self.driver).move_to_element(el).click().perform()
            return True
        except Exception:
            return False

    def wait_for_any_button(self):
        """Extra wait for late-loading forms (e.g., SEO Discovery/HubSpot)"""
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "button, input[type='submit'], .btn, .hs-button")
                )
            )
            time.sleep(1)
            return True
        except Exception:
            return False

    # ---------- Framework-specific ----------
    def try_wp_cf7(self):
        try:
            for b in self.driver.find_elements(By.CSS_SELECTOR, "input.wpcf7-submit, button.wpcf7-submit"):
                if b.is_displayed() and b.is_enabled():
                    return self.safe_click(b)
        except Exception:
            pass
        return False

    def try_elementor(self):
        try:
            for b in self.driver.find_elements(By.CSS_SELECTOR, "button.elementor-button, .elementor-form button"):
                if b.is_displayed() and b.is_enabled():
                    return self.safe_click(b)
        except Exception:
            pass
        return False

    def try_wp_other_forms(self):
        selectors = [
            "button#gform_submit_button",        # Gravity Forms
            ".nf-field-element button",          # Ninja Forms
            ".wpforms-submit",                   # WPForms
            "button.hs-button, input.hs-button", # HubSpot
            ".hs-button.primary",                # HubSpot alt
            "button.mktoButton",                 # Marketo
            ".et_pb_contact_submit",             # Divi
            "button.uagb-forms-main-submit",     # Spectra/Ultimate Addons
        ]
        for sel in selectors:
            try:
                for b in self.driver.find_elements(By.CSS_SELECTOR, sel):
                    if b.is_displayed() and b.is_enabled():
                        return self.safe_click(b)
            except Exception:
                continue
        return False

    # ---------- Generic strategies ----------
    def try_input_values(self):
        """<input type='submit' value='Submit Now'> etc."""
        try:
            for inp in self.driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], .btn.btn-primary, .btn, .hs-button"):
                val = ((inp.get_attribute("value") or inp.text) or "").lower()
                if any(k in val for k in [
                    "submit", "send", "apply", "continue", "next",
                    "book", "message", "get started", "contact"
                ]):
                    if inp.is_displayed() and inp.is_enabled():
                        return self.safe_click(inp)
        except Exception:
            pass
        return False

    def try_by_text(self):
        """Click buttons/links by visible text"""
        xpath = ("//*[self::button or self::a or self::div or self::span or self::input]"
                 "[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'submit')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'book')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'message')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'get started')"
                 " or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'contact')]")
        try:
            for el in self.driver.find_elements(By.XPATH, xpath):
                if el.is_displayed() and el.is_enabled():
                    return self.safe_click(el)
        except Exception:
            pass
        return False

    def try_basic_submit(self):
        """Fallback: any <button type=submit> or <input type=submit>"""
        try:
            for b in self.driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']"):
                if b.is_displayed() and b.is_enabled():
                    return self.safe_click(b)
        except Exception:
            pass
        return False

    def press_enter_fallback(self):
        """As last resort, press Enter on last input field"""
        try:
            fields = self.driver.find_elements(By.CSS_SELECTOR, "form input, form textarea")
            if fields:
                fields[-1].send_keys(Keys.RETURN)
                return True
        except Exception:
            pass
        return False

    def wait_for_confirmation(self):
        """Wait for success message after submit"""
        try:
            WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'thank you')"
                    " or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'message has been sent')"
                    " or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'we will be in touch')]"
                ))
            )
            return True
        except Exception:
            return False

    # ---------- Runner ----------
    def run(self):
        """Try all known strategies to click a submit button"""
        self.wait_for_any_button()  # helps on late-loading UIs

        strategies = [
            self.try_wp_cf7,
            self.try_elementor,
            self.try_wp_other_forms,
            self.try_input_values,
            self.try_by_text,
            self.try_basic_submit,
            self.press_enter_fallback,
        ]

        for strategy in strategies:
            if strategy():
                # wait for success confirmation if possible
                if self.wait_for_confirmation():
                    return True
                time.sleep(8)  # fallback wait
                return True
        return False
