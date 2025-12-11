import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.alert import Alert
from driver import AutoHealingDriver, LocatorInfo

def main():
    # 1. Start Driver
    driver = webdriver.Chrome()
    ah = AutoHealingDriver(driver)
    
    # 2. SEED MEMORY for Demo Reliability
    ah.store._data = {} # Reset
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
        # Point to LOCAL index.html (My_AutoHeal dir)
        page_path = os.path.join(base_dir, "index.html")
        url = f"file:///{page_path}"
        
        print(f"\n--- PHASE 1: LOGIN ---")
        ah.get(url)
        ah.find("username_field", By.ID, "username").send_keys("test.user")
        
        # BROKEN LOCATOR
        print("Clicking login (using broken locator 'submit_btn' backed by memory)...")
        ah.find("login_button", By.ID, "submit_btn").click() 
        
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
