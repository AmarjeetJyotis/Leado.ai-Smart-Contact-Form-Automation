import logging
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementNotInteractableException,
    TimeoutException,
)

logger = logging.getLogger("formbot")

class FormFiller:
    def __init__(self, driver, dataset):
        self.driver = driver
        self.dataset = dataset

    # ---------- Helpers ----------
    def _choose_value(self, field, ftype, attr):
        attr = attr.lower()
        if "mail" in attr:
            return self.dataset.get("email", "test@example.com")
        if "first" in attr:
            return self.dataset.get("name", "Test User").split()[0]
        if "last" in attr:
            return self.dataset.get("name", "User").split()[-1]
        if "name" in attr:
            return self.dataset.get("name", "Test User")
        if "phone" in attr or "tel" in attr:
            return self.dataset.get("phone", "9999999999")
        if "zip" in attr or "postal" in attr:
            return self.dataset.get("zipcode", "12345")
        if "address" in attr:
            return self.dataset.get("address", "123 Test Street")
        if "city" in attr:
            return self.dataset.get("city", "Test City")
        if "state" in attr or "region" in attr:
            return self.dataset.get("state", "Test State")
        if "website" in attr or "url" in attr:
            return self.dataset.get("website", "https://example.com")
        if "looking_for" in attr:
            return self.dataset.get("looking_for", "SEO")
        if "challenge" in attr or "message" in attr:
            return self.dataset.get("message", "We want to grow our traffic.")
        return self.dataset.get("name", "Test User")

    def _safe_type(self, field, value):
        try:
            field.clear()
        except Exception:
            pass
        try:
            for ch in str(value):
                field.send_keys(ch)
                time.sleep(0.02 + random.random() * 0.05)  # human-like typing
            field.send_keys(Keys.TAB)
            logger.debug(f"[FormFiller] Typed '{value}' into {field.get_attribute('name') or field.get_attribute('id')}")
        except Exception as e:
            logger.debug(f"[FormFiller] Failed typing into field: {e}")

    def _safe_click(self, el):
        try:
            el.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.2)
                el.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                    return True
                except Exception:
                    return False

    # ---------- Special HubSpot handler ----------
    def _handle_hubspot(self):
        """Detect and fill HubSpot embedded forms inside iframe"""
        try:
            iframe = WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.hs-form-iframe"))
            )
            self.driver.switch_to.frame(iframe)
            logger.debug("[FormFiller] Switched into HubSpot iframe")

            # Fill common HubSpot fields
            if "name" in self.dataset:
                self._safe_type(
                    self.driver.find_element(By.CSS_SELECTOR, "input[name*='name'], input[name*='firstname']"),
                    self.dataset["name"]
                )
            if "email" in self.dataset:
                self._safe_type(self.driver.find_element(By.CSS_SELECTOR, "input[type='email']"),
                                self.dataset["email"])
            if "phone" in self.dataset:
                try:
                    self._safe_type(self.driver.find_element(By.CSS_SELECTOR, "input[type='tel']"),
                                    self.dataset["phone"])
                except Exception:
                    pass
            if "message" in self.dataset:
                try:
                    self._safe_type(self.driver.find_element(By.CSS_SELECTOR, "textarea"),
                                    self.dataset["message"])
                except Exception:
                    pass

            # Submit button
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button")
                self._safe_click(submit_btn)
                logger.debug("[FormFiller] Submitted HubSpot form")
            except Exception:
                logger.debug("[FormFiller] Could not find HubSpot submit button")

            self.driver.switch_to.default_content()
            return True
        except TimeoutException:
            self.driver.switch_to.default_content()
            return False
        except Exception as e:
            logger.debug(f"[FormFiller] HubSpot handler failed: {e}")
            self.driver.switch_to.default_content()
            return False

    # ---------- Fillers ----------
    def fill_inputs(self):
        inputs = self.driver.find_elements(By.CSS_SELECTOR, "form input")
        for field in inputs:
            try:
                if not field.is_displayed() or not field.is_enabled():
                    continue
                ftype = (field.get_attribute("type") or "").lower()
                if ftype in ["hidden", "file", "password", "submit", "button", "image", "reset"]:
                    continue

                placeholder = (field.get_attribute("placeholder") or "").lower()
                name_attr = (field.get_attribute("name") or "").lower()
                id_attr = (field.get_attribute("id") or "").lower()
                attr = " ".join([ftype, placeholder, name_attr, id_attr])

                val = self._choose_value(field, ftype, attr)
                self._safe_type(field, val)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue
            except Exception:
                continue

    def fill_textareas(self):
        textareas = self.driver.find_elements(By.CSS_SELECTOR, "form textarea")
        for ta in textareas:
            try:
                if ta.is_displayed() and ta.is_enabled():
                    msg = self.dataset.get("message", "Hello, this is a test message.")
                    self._safe_type(ta, msg)
            except Exception:
                continue

    def fill_checkboxes(self):
        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "form input[type='checkbox']")
        for cb in checkboxes:
            try:
                if cb.is_selected():
                    continue

                # Visible, clickable
                if cb.is_displayed() and cb.is_enabled():
                    if self._safe_click(cb):
                        logger.debug(f"[FormFiller] Checked {cb.get_attribute('name') or cb.get_attribute('id')}")
                        continue

                # Hidden → try its label
                cid = cb.get_attribute("id")
                if cid:
                    try:
                        label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{cid}']")
                        if label.is_displayed() and self._safe_click(label):
                            logger.debug(f"[FormFiller] Checked via label: {cid}")
                            continue
                    except Exception:
                        pass

                # Last resort: JS click
                try:
                    self.driver.execute_script("arguments[0].click();", cb)
                    logger.debug(f"[FormFiller] JS-clicked {cb.get_attribute('name') or cb.get_attribute('id')}")
                except Exception:
                    continue
            except Exception:
                continue

    def fill_radios(self):
        radios = self.driver.find_elements(By.CSS_SELECTOR, "form input[type='radio']")
        chosen = set()
        for r in radios:
            try:
                name = r.get_attribute("name") or id(r)
                if name in chosen:
                    continue
                if r.is_displayed() and r.is_enabled() and not r.is_selected():
                    self._safe_click(r)
                    chosen.add(name)
                    logger.debug(f"[FormFiller] Selected radio {name}")
            except Exception:
                continue

    def fill_selects(self):
        selects = self.driver.find_elements(By.CSS_SELECTOR, "form select")
        for sel in selects:
            try:
                if sel.is_displayed() and sel.is_enabled():
                    s = Select(sel)
                    opts = [opt for opt in s.options if opt.text.strip()
                            and "select" not in opt.text.lower()
                            and "choose" not in opt.text.lower()]
                    if opts:
                        choice = self.dataset.get("looking_for")
                        if choice and any(opt.text.strip().lower() == choice.lower() for opt in opts):
                            try:
                                s.select_by_visible_text(choice)
                                logger.debug(f"[FormFiller] Selected option '{choice}' (matched dataset)")
                            except Exception:
                                self._safe_click(random.choice(opts))
                        else:
                            rand_opt = random.choice(opts)
                            try:
                                s.select_by_visible_text(rand_opt.text.strip())
                                logger.debug(f"[FormFiller] Randomly selected '{rand_opt.text.strip()}'")
                            except Exception:
                                self._safe_click(rand_opt)
            except Exception:
                continue

    def fill_custom_dropdowns(self):
        containers = self.driver.find_elements(
            By.XPATH, "//*[contains(@class,'select2') or contains(@class,'choices') or @role='listbox']"
        )
        for c in containers[:4]:
            try:
                if c.is_displayed() and c.is_enabled():
                    self._safe_click(c)
                    time.sleep(0.4)
                    options = [o for o in self.driver.find_elements(By.XPATH, "//*[@role='option']") if o.is_displayed()]
                    if options:
                        opt = random.choice(options)
                        self._safe_click(opt)
                        logger.debug(f"[FormFiller] Picked custom dropdown option '{opt.text}'")
            except Exception:
                continue

    # ---------- Orchestrator ----------
    def run(self):
        """Run all filling steps, optimized for HubSpot & generic forms"""
        if self._handle_hubspot():
            logger.debug("[FormFiller] HubSpot form handled successfully")
            return True

        self.fill_inputs()
        self.fill_textareas()
        self.fill_checkboxes()
        self.fill_radios()
        self.fill_selects()
        self.fill_custom_dropdowns()
        logger.debug("[FormFiller] Finished filling generic form fields")
        return False
