import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple, Any

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement



os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=os.path.join("logs", "auto_heal.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

@dataclass
class LocatorInfo:
    by: str
    value: str
    healed: bool = False
    heal_reason: Optional[str] = None
    last_success_ts: Optional[float] = None
    attributes: Optional[Dict[str, str]] = None


@dataclass
class Metrics:
    locators_tried: int = 0
    locators_failed: int = 0
    heals_attempted: int = 0
    heals_successful: int = 0
    heals_failed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


class LocatorStore:
    """
    Maps logical element names -> LocatorInfo, stored as JSON.
    This is the 'memory' that makes the system adapt between runs.
    """

    def __init__(self, path: str = "locator_store.json"):
        self.path = path
        self._data: Dict[str, LocatorInfo] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for name, info in raw.items():
                self._data[name] = LocatorInfo(**info)
        except Exception as e:
            logging.error(f"Failed to load locator store: {e}")

    def save(self) -> None:
        try:
            raw = {k: asdict(v) for k, v in self._data.items()}
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save locator store: {e}")

    def get(self, name: str) -> Optional[LocatorInfo]:
        return self._data.get(name)

    def set(self, name: str, info: LocatorInfo) -> None:
        self._data[name] = info
        self.save()

class AutoHealingDriver:
    """
    Wraps a Selenium WebDriver to add:
      - Error detection (HTTP-like and JS errors)
      - Self-healing locators
      - Persistent memory of successful locators
      - Metrics exported to JSON
    """

    def __init__(
        self,
        driver: WebDriver,
        locator_store_path: str = "locator_store.json",
        metrics_path: str = "metrics.json",
        default_timeout: int = 10,
    ):
        self.driver = driver
        self.store = LocatorStore(locator_store_path)
        self.metrics_path = metrics_path
        self.default_timeout = default_timeout
        self.metrics = Metrics()

    def get(self, url: str) -> None:
        logging.info(f"Navigating to {url}")
        self.driver.get(url)
        self._check_http_like_errors()
        self._check_simple_js_errors()

    def find(
        self,
        name: str,
        by: str,
        value: str,
        timeout: Optional[int] = None,
    ):
        """
        Find an element with self-healing support.

        name   = logical element name (e.g. "login_button")
        by     = Selenium By strategy (e.g. By.ID, By.CSS_SELECTOR)
        value  = the locator string
        """

        timeout = timeout or self.default_timeout
        self.metrics.locators_tried += 1

        # If we have a stored locator for this logical element, prefer that
        stored = self.store.get(name)
        using_memory_healing = False
        if stored:
            if stored.by != by or stored.value != value:
                using_memory_healing = True
            by, value = stored.by, stored.value
            logging.info(f"[{name}] Using stored locator: {by}={value}")
        else:
            logging.info(f"[{name}] Using initial locator: {by}={value}")

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            self._on_success(name, by, value, healed=stored.healed if stored else False, element=element)
            
            if using_memory_healing:
                 logging.info(f"[{name}] healing successful")
                 
            return element

        except (NoSuchElementException, TimeoutException, StaleElementReferenceException) as e:
            logging.warning(f"[{name}] Primary locator failed: {by}={value} ({e.__class__.__name__})")
            self.metrics.locators_failed += 1

            self.metrics.locators_failed += 1
            
            healed_locator = self._heal_locator(name, by, value, timeout)

            if healed_locator:
                healed_by, healed_value, heal_reason = healed_locator
                logging.info(f"[{name}] Healed locator: {healed_by}={healed_value} ({heal_reason})")

                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((healed_by, healed_value))
                    )
                    self._on_success(name, healed_by, healed_value, healed=True, heal_reason=heal_reason, element=element)
                    return element
                except Exception as e2:
                    logging.error(f"[{name}] Element not interactable even after healing: {e2}")
                    self.metrics.heals_failed += 1
                    raise

            logging.error(f"[{name}] Could not heal locator.")
            self.metrics.heals_failed += 1
            raise


    def _on_success(
        self,
        name: str,
        by: str,
        value: str,
        healed: bool,
        heal_reason: Optional[str] = None,
        element: Optional[WebElement] = None,
    ) -> None:
        attributes = {}
        if element:
            try:
                # Capture useful attributes for future healing
                for attr in ["id", "name", "class", "type"]:
                    val = element.get_attribute(attr)
                    if val:
                        attributes[attr] = str(val)
                attributes["tag"] = element.tag_name
                
                # Capture text for non-inputs
                if element.tag_name not in ["input", "select", "textarea"]:
                    txt = element.text
                    if txt:
                        attributes["text"] = txt[:50] # Limit length
            except Exception as e:
                logging.warning(f"[{name}] Failed to capture attributes: {e}")

        info = LocatorInfo(
            by=by,
            value=value,
            healed=healed,
            heal_reason=heal_reason,
            last_success_ts=time.time(),
            attributes=attributes if attributes else None
        )
        self.store.set(name, info)

    def _heal_locator(
        self,
        name: str,
        by: str,
        value: str,
        timeout: int,
    ) -> Optional[Tuple[str, str, str]]:
        
        heal_attempts = []
        self.metrics.heals_attempted += 1

        stored = self.store.get(name)
        if stored and (stored.by != by or stored.value != value):
            heal_attempts.append(
                (stored.by, stored.value, "Reusing previous successful locator")
            )

        # --- NEW: Attribute-based Fallbacks ---
        if stored and stored.attributes:
            attrs = stored.attributes
            
            # 1. ID Fallback (if stored ID differs from current failed one)
            if "id" in attrs:
                # Avoid trying the exact same ID if that's what failed
                if not (by == By.ID and value == attrs["id"]): 
                    heal_attempts.append((By.ID, attrs["id"], f"Fallback to ID='{attrs['id']}'"))
            
            # 2. Name Fallback
            if "name" in attrs:
                 heal_attempts.append((By.NAME, attrs["name"], f"Fallback to Name='{attrs['name']}'"))

            # 3. Class Fallback
            if "class" in attrs:
                cls_val = attrs["class"].strip()
                if cls_val:
                    # Use the first class token for simplicity
                    first_class = cls_val.split()[0]
                    heal_attempts.append((By.CLASS_NAME, first_class, f"Fallback to Class='{first_class}'"))

            # 4. Text Fallback
            if "text" in attrs and "tag" in attrs:
                txt = attrs["text"].strip()
                if len(txt) > 3: # minimal validity
                     heal_attempts.append(
                        (By.XPATH, f"//*[contains(text(), '{txt}')]", f"Fallback to Text='{txt}...'")
                     )
        # --------------------------------------

        if by == By.ID:
            element_id = value
            heal_attempts.append((By.CSS_SELECTOR, f"#{element_id}", "ID->CSS by #id"))
            heal_attempts.append((By.XPATH, f"//*[@id='{element_id}']", "ID->XPath by @id"))

        
        elif by == By.CSS_SELECTOR:
            css = value
            if "." in css and "#" not in css:
                last_class = css.split(".")[-1]
                heal_attempts.append(
                    (
                        By.XPATH,
                        f"//*[contains(@class, '{last_class}')]",
                        "CSS class->XPath contains(@class)",
                    )
                )

        
        elif by == By.XPATH:
            xpath = value
            if "text()" in xpath and "'" in xpath:
                try:
                    text_piece = xpath.split("text()=")[1].split("'")[1]
                    heal_attempts.append(
                        (
                            By.XPATH,
                            f"//*[contains(normalize-space(text()), '{text_piece}')]",
                            "XPath text()->contains(text())",
                        )
                    )
                except Exception:
                    pass


        for heal_by, heal_value, reason in heal_attempts:
            try:
                logging.info(f"[{name}] Healing attempt: {heal_by}={heal_value} ({reason})")
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((heal_by, heal_value))
                )
                self.metrics.heals_successful += 1
                return heal_by, heal_value, reason
            except Exception:
                continue

        return None


 

    def _check_http_like_errors(self) -> None:
      
        html = self.driver.page_source.lower()
        indicators = [
            "404 not found",
            "500 internal server error",
            "service unavailable",
        ]
        for ind in indicators:
            if ind in html:
                logging.error(f"HTTP-like error detected: {ind}")
                break

    def _check_simple_js_errors(self) -> None:
       
        try:
            logs = self.driver.get_log("browser")
        except Exception:
            return

        for entry in logs:
            level = entry.get("level", "").upper()
            message = entry.get("message", "")
            if "ERROR" in level:
                logging.error(f"JS error: {message}")

    def _save_metrics(self) -> None:
        try:
            with open(self.metrics_path, "w", encoding="utf-8") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")

    def quit(self) -> None:
        self._save_metrics()
        self.driver.quit()

    def __getattr__(self, item):
        return getattr(self.driver, item)



