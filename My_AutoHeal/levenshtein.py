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
        
        start_time = time.time()
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
            # Metrics: Performance Log (Failed - Unsupported)
            duration = time.time() - start_time
            logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned=0, Success=False")
            return None

        try:
            # Find all elements that possess this attribute
            elements = self.driver.find_elements(By.CSS_SELECTOR, f"[{search_attribute}]")
        except:
            # Metrics: Performance Log (Failed - Exception)
            duration = time.time() - start_time
            logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned=0, Success=False")
            return None

        candidates_count = len(elements)
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
            # Metrics: Performance Log (Failed - too weak)
            duration = time.time() - start_time
            logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned={candidates_count}, Success=False")
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
                
                # Metrics: Performance Log (Success)
                duration = time.time() - start_time
                logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned={candidates_count}, Success=True")
                
                return by, best_candidate, f"Levenshtein (dist={best_distance})"
            except: 
                # Metrics: Performance Log (Failed - Verification Failed)
                duration = time.time() - start_time
                logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned={candidates_count}, Success=False")
                pass
                
        # Metrics: Performance Log (Failed - No suitable candidate or verification failed)
        duration = time.time() - start_time
        logging.info(f"[Performance] Method=Levenshtein, Time={duration:.4f}s, Scanned={candidates_count}, Success=False")
            
        return None

# --- SCENARIO FUNCTIONS ---

def get_page_url(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return f"file:///{os.path.join(base_dir, filename)}"

def run_login_scenario(ah):
    logging.info("--- SCENARIO 1: LOGIN (Levenshtein) ---")
    print(f"\n--- SCENARIO 1: LOGIN (Levenshtein) ---")
    ah.get(get_page_url("index.html"))
    # Real: login-btn-primary. Typo: login-btn-prmary
    ah.find("login_button", By.ID, "login-btn-prmary").click()
    
    # Real: delete-alice-btn-primary. Typo: delete-alice-btn-prim
    ah.find("delete_alice_btn", By.ID, "delete-alice-btn-prim").click()
    
    # Real: profile_email. Typo: profile_emal
    ah.find("profile_email_input", By.ID, "profile_emal").send_keys("lvl@test.com")
    
    # Real: btn_save_profile. Typo: btn_save_prfile
    ah.find("save_profile_btn", By.ID, "btn_save_prfile").click()

def run_ecommerce_scenario(ah):
    logging.info("--- SCENARIO 2: E-COMMERCE (Levenshtein) ---")
    print(f"\n--- SCENARIO 2: E-COMMERCE (Levenshtein) ---")
    ah.get(get_page_url("page_ecommerce.html"))
    # Real: search_box_v2. Typo: search_box_v
    ah.find("search_box", By.ID, "search_box_v").send_keys("Laptop")
    # Real: add_to_cart_laptop. Typo: add_cart_laptop
    ah.find("add_laptop", By.ID, "add_cart_laptop").click()
    # Real: checkout_now. Typo: checkout_nw
    ah.find("checkout_btn", By.ID, "checkout_nw").click()

def run_blog_scenario(ah):
    logging.info("--- SCENARIO 3: BLOG (Levenshtein) ---")
    print(f"\n--- SCENARIO 3: BLOG (Levenshtein) ---")
    ah.get(get_page_url("page_blog.html"))
    # Real: read_more_link. Typo: read_more_lnk
    ah.find("read_more", By.ID, "read_more_lnk").click()
    # Real: comment_box. Typo: cmmnt_box
    ah.find("comment_box", By.ID, "cmmnt_box").send_keys("Nice!")
    # Real: post_comment_btn. Typo: post_commnt_btn
    ah.find("post_comment", By.ID, "post_commnt_btn").click()

def run_dashboard_scenario(ah):
    logging.info("--- SCENARIO 4: DASHBOARD (Levenshtein) ---")
    print(f"\n--- SCENARIO 4: DASHBOARD (Levenshtein) ---")
    ah.get(get_page_url("page_dashboard.html"))
    # Real: update_settings_btn. Typo: update_settngs_btn
    ah.find("update_settings", By.ID, "update_settngs_btn").click()
    # Real: toggle_dark_mode. Typo: togle_dark_mode
    ah.find("toggle_dark", By.ID, "togle_dark_mode").click()

def run_contact_scenario(ah):
    logging.info("--- SCENARIO 5: CONTACT (Levenshtein) ---")
    print(f"\n--- SCENARIO 5: CONTACT (Levenshtein) ---")
    ah.get(get_page_url("page_contact.html"))
    # Real: contact_name. Typo: cntact_name
    ah.find("contact_name", By.ID, "cntact_name").send_keys("Bob")
    # Real: send_message_btn. Typo: send_msg_btn
    ah.find("send_btn", By.ID, "send_msg_btn").click()

def main():
    # Setup Log
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    logging.basicConfig(
        filename=os.path.join("logs", "levenshtein.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        force=True
    )

    driver = webdriver.Chrome()
    ah = LevenshteinDriver(driver, locator_store_path="locator_store_levenshtein.json", metrics_path="metrics_levenshtein.json", log_path="logs/levenshtein.log")
    
    # NO MEMORY SEEDING -> Forces Levenshtein Healing
    ah.store._data = {}
    
    try:
        run_login_scenario(ah)
        run_ecommerce_scenario(ah)
        run_blog_scenario(ah)
        run_dashboard_scenario(ah)
        run_contact_scenario(ah)
        print("\nAll 5 Levenshtein scenarios completed.")
    except Exception as e:
        print(f"Levenshtein Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ah.quit()

if __name__ == "__main__":
    main()
