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
        log_path: Optional[str] = None,
    ):
        self.driver = driver
        self.store = LocatorStore(locator_store_path)
        self.metrics_path = metrics_path
        self.default_timeout = default_timeout
        self.metrics = Metrics()
        self.log_path = log_path

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

            # (removed duplicate line self.metrics.locators_failed += 1)
            
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
        
        start_time = time.time()
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
            
            # 1. ID Fallback
            if "id" in attrs:
                if not (by == By.ID and value == attrs["id"]): 
                    heal_attempts.append((By.ID, attrs["id"], f"Fallback to ID='{attrs['id']}'"))
            
            # 2. Name Fallback
            if "name" in attrs:
                 if not (by == By.NAME and value == attrs["name"]):
                    heal_attempts.append((By.NAME, attrs["name"], f"Fallback to Name='{attrs['name']}'"))
            
            # 3. Class Fallback
            if "class" in attrs:
                heal_attempts.append((By.CLASS_NAME, attrs["class"], f"Fallback to Class='{attrs['class']}'"))
                
            # 4. Text Fallback (XPath)
            if "text" in attrs and "tag" in attrs:
                xpath = f"//{attrs['tag']}[text()='{attrs['text']}']"
                heal_attempts.append((By.XPATH, xpath, f"Fallback to Text='{attrs['text']}'"))

        # --- Standard Rules (ID->CSS, ID->XPath) ---
        if by == By.ID:
            heal_attempts.append((By.CSS_SELECTOR, f"#{value}", "ID->CSS by #id"))
            heal_attempts.append((By.XPATH, f"//*[@id='{value}']", "ID->XPath by @id"))
        elif by == By.CLASS_NAME:
            heal_attempts.append((By.CSS_SELECTOR, f".{value}", "Class->CSS"))
            heal_attempts.append((By.XPATH, f"//*[@class='{value}']", "Class->XPath"))
        elif by == By.NAME:
            heal_attempts.append((By.CSS_SELECTOR, f"[name='{value}']", "Name->CSS"))
            heal_attempts.append((By.XPATH, f"//*[@name='{value}']", "Name->XPath"))
        elif by == By.CSS_SELECTOR:
            # Try to catch basic .class or #id issues manually if needed, 
            # but usually CSS is robust. Let's adding a simple fallback for class only.
            if "." in value and "#" not in value and " " not in value:
                cls = value.replace(".", "")
                heal_attempts.append((By.CLASS_NAME, cls, "CSS class->Class Name"))

        for h_by, h_value, reason in heal_attempts:
            logging.info(f"[{name}] Healing attempt: {h_by}={h_value} ({reason})")
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((h_by, h_value))
                )
                self.metrics.heals_successful += 1
                logging.info(f"[{name}] healing successful")
                
                # Metrics: Performance Log
                duration = time.time() - start_time
                logging.info(f"[Performance] Method=Standard, Time={duration:.4f}s, Attempts={len(heal_attempts)}, Success=True")
                
                return h_by, h_value, reason
            except Exception:
                continue
        
        # Metrics: Performance Log (Failed)
        duration = time.time() - start_time
        logging.info(f"[Performance] Method=Standard, Time={duration:.4f}s, Attempts={len(heal_attempts)}, Success=False")
        
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

    def _update_metrics_from_log(self) -> None:
        if not self.log_path or not os.path.exists(self.log_path):
            logging.warning("No log path specified or file not found. Metrics will not be updated from logs.")
            return
            
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            self.metrics.locators_tried = 0
            self.metrics.locators_failed = 0
            self.metrics.heals_attempted = 0
            self.metrics.heals_successful = 0
            self.metrics.heals_failed = 0
            
            for line in lines:
                if "Using initial locator" in line or "Using stored locator" in line:
                    self.metrics.locators_tried += 1
                if "Primary locator failed" in line:
                    self.metrics.locators_failed += 1
                if "Healing attempt" in line:
                    self.metrics.heals_attempted += 1
                if "healing successful" in line:
                    self.metrics.heals_successful += 1
                if "Could not heal locator" in line:
                    self.metrics.heals_failed += 1
                    
        except Exception as e:
            logging.error(f"Failed to update metrics from log: {e}")

    def _save_metrics(self) -> None:
        try:
            with open(self.metrics_path, "w", encoding="utf-8") as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")

    def quit(self) -> None:
        self._update_metrics_from_log()
        self._save_metrics()
        self.driver.quit()

    def __getattr__(self, item):
        return getattr(self.driver, item)



