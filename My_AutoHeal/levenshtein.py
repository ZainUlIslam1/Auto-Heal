import os
import time
import logging
from typing import Optional, Tuple, List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from driver import AutoHealingDriver, LocatorInfo

# --- ALGORITHM ---

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculates the Levenshtein distance between two strings using iterative approach
    to avoid recursion depth issues.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

# --- DRIVER OVERRIDE ---

class LevenshteinDriver(AutoHealingDriver):
    """
    Subclass of AutoHealingDriver that overrides the healing logic
    to use Levenshtein Distance instead of hardcoded rules.
    """
    
    def _heal_locator(
        self,
        name: str,
        by: str,
        value: str,
        timeout: int,
    ) -> Optional[Tuple[str, str, str]]:
        
        logging.info(f"[{name}] (Levenshtein) Healing attempt for {by}={value}")
        self.metrics.heals_attempted += 1

        # We primarily support ID/Class/Name matching for this demo
        search_attribute = ""
        if by == By.ID: 
            search_attribute = "id"
        elif by == By.NAME: 
            search_attribute = "name"
        elif by == By.CLASS_NAME: 
            search_attribute = "class"
        else:
            # Fallback: if we can't map 'by' to a simple attribute, we can't easily scan everything strings
            return None

        try:
            # Find all elements that possess this attribute
            elements = self.driver.find_elements(By.CSS_SELECTOR, f"[{search_attribute}]")
        except:
            return None

        best_distance = float('inf')
        best_candidate: Optional[str] = None

        for el in elements:
            try:
                attr_val = el.get_attribute(search_attribute)
                if not attr_val: continue
                
                dist = levenshtein_distance(value, attr_val)
                if dist < best_distance:
                    best_distance = dist
                    best_candidate = attr_val
            except:
                continue

        # Threshold to avoid matching noise (e.g. login -> footer)
        # Distance > 70% of length is probably bad
        limit = max(2, len(value) * 0.7)
        
        if best_distance > limit:
            logging.info(f"[{name}] Best match '{best_candidate}' (dist={best_distance}) was too weak.")
            return None
            
        if best_candidate and best_candidate != value:
            logging.info(f"[{name}] Found Levenshtein match: '{best_candidate}' (dist={best_distance})")
            
            # Verify if it works
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, best_candidate))
                )
                self.metrics.heals_successful += 1
                logging.info(f"[{name}] healing successful")
                return by, best_candidate, f"Levenshtein (dist={best_distance})"
            except:
                pass
                
        return None

# --- TEST SUITE (Identical to test.py but using LevenshteinDriver) ---

def main():
    # 0. Setup Separate Logging for Levenshtein
    # This overrides the default logging config from driver.py
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    logging.basicConfig(
        filename=os.path.join("logs", "levenshtein.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True
    )
    
    # 1. Start Driver (Custom Levenshtein Version)
    driver = webdriver.Chrome()
    ah = LevenshteinDriver(driver, locator_store_path="locator_store_levenshtein.json", metrics_path="metrics_levenshtein.json")
    ah.store._data = {}
    print("Levenshtein Driver initialized.")
    currentTime = time.time()
    
    # LOGIN SEED
    # Seeding the REAL ID found in local index.html
    ah.store.set("login_button", LocatorInfo(
        By.ID, 
        "login-btn-primary", 
        last_success_ts=currentTime,
        attributes={"class": "btn-primary", "text": "Login", "tag": "button"}
    ))
    
    # TABLE SEED
    ah.store.set("delete_alice_btn", LocatorInfo(By.ID, "delete-alice-btn-primary", last_success_ts=currentTime))
    
    # FORM SEED
    ah.store.set("profile_email_input", LocatorInfo(
        By.ID, 
        "profile_email", 
        last_success_ts=currentTime,
        attributes={"name": "email", "type": "email", "tag": "input"}
    ))
    ah.store.set("save_profile_btn", LocatorInfo(By.ID, "btn_save_profile", last_success_ts=currentTime))
    
    # TEXT SEED
    ah.store.set("logout_link", LocatorInfo(By.XPATH, "//a[text()='Logout']", last_success_ts=currentTime))

    print("Memory seeded for Login, Table, Form, and Text scenarios.")
    
    try:
        # --- PHASE 1: LOGIN ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Point to the LOCAL index.html in My_AutoHeal to avoid missing file error
        page_path = os.path.join(base_dir, "index.html")
        url = f"file:///{page_path}"
        
        print(f"\n--- PHASE 1: LOGIN ---")
        ah.get(url)
        ah.find("username_field", By.ID, "username").send_keys("test.user")
        
        print("Clicking login (using broken locator 'login-btn-broken')...")
        # Real ID in local index.html: login-btn-primary
        # We try 'login-btn-broken' (Dist=6: 'primary' vs 'broken')
        ah.find("login_button", By.ID, "login-btn-broken").click()  
        
        print("Login successful. Proceeding to inner scenarios...")
        time.sleep(1) 

        # --- PHASE 2: TABLE (Row Action) ---
        print(f"\n--- PHASE 2: TABLE ---")
        # Broken locator: 'delete-btn-1'
        # Memory says: 'delete-alice-btn-primary'
        print("Clicking Alice's delete button (using broken locator 'delete-btn-1')...")
        ah.find("delete_alice_btn", By.ID, "delete-btn-1").click()
        
        # --- PHASE 3: FORM (Input + Submit) ---
        print(f"\n--- PHASE 3: FORM ---")
        # Broken locator: 'email_field'
        # Memory says: 'profile_email'
        print("Filling email (using broken locator 'email_field')...")
        ah.find("profile_email_input", By.ID, "email_field").clear()
        ah.find("profile_email_input", By.ID, "email_field").send_keys("new.email@example.com")
        
        # Broken locator: 'save-btn'
        # Memory says: 'btn_save_profile'
        print("Clicking save profile (using broken locator 'save-btn')...")
        ah.find("save_profile_btn", By.ID, "save-btn").click()
        
        # --- PHASE 4: TEXT (Logout) ---
        print(f"\n--- PHASE 4: TEXT ---")
        # Broken locator: //a[text()='Sign Out']
        # Memory says: //a[text()='Logout']
        print("Clicking logout (using broken locator 'Sign Out' link)...")
        ah.find("logout_link", By.XPATH, "//a[text()='Sign Out']").click()
        
        print("All scenarios completed successfully.") 
        
        # --- PHASE 5: ATTRIBUTES FALLBACK ---
        print(f"\n--- PHASE 5: ATTRIBUTES FALLBACK ---")
        # Seeding a memory entry that has a WRONG ID, but CORRECT attributes (class='btn-primary')
        # We target the Login Button again (it has class="btn-primary")
        ah.store.set("fallback_login_btn", LocatorInfo(
            by=By.ID, 
            value="wrong_memory_id_123", 
            last_success_ts=currentTime,
            attributes={"class": "btn-primary", "text": "Login", "tag": "button"}
        ))
        
        # Runtime broken locator
        print("Clicking login button (forcing fallback to attributes: class='btn-primary')...")
        # 1. 'broken-locator-999' -> Fail
        # 2. 'wrong_memory_id_123' -> Fail
        # 3. Heal using attributes -> Success
        ah.find("fallback_login_btn", By.ID, "broken-locator-999").click()
        print("Attribute fallback successful!") 

        



        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        ah.quit()
        print("\nRun finished. Check logs/auto_heal.log for full healing trace.")

if __name__ == "__main__":
    main()

