import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from driver import AutoHealingDriver, LocatorInfo

def seed_memory(ah):
    currentTime = time.time()
    # 1. Login Page (index.html) - Note: Page has intentional messed up ID "login1212btn-p]rimary"
    # We seed "login-btn-primary" (old ID) but MUST provide attributes for fallback healing to work.
    ah.store.set("login_button", LocatorInfo(
        By.ID, 
        "login-btn-primary", 
        last_success_ts=currentTime,
        attributes={"class": "btn-primary", "text": "Login", "tag": "button"}
    ))
    
    ah.store.set("delete_alice_btn", LocatorInfo(By.ID, "delete-alice-btn-primary", last_success_ts=currentTime))
    
    ah.store.set("profile_email_input", LocatorInfo(
        By.ID, 
        "profile_email", 
        last_success_ts=currentTime,
        attributes={"name": "email", "type": "email", "tag": "input"}
    ))
    
    ah.store.set("save_profile_btn", LocatorInfo(By.ID, "btn_save_profile", last_success_ts=currentTime))
    ah.store.set("logout_link", LocatorInfo(By.XPATH, "//a[text()='Logout']", last_success_ts=currentTime))

    # 2. Ecommerce Page
    ah.store.set("search_box", LocatorInfo(By.ID, "search_box_v2", last_success_ts=currentTime))
    ah.store.set("add_laptop", LocatorInfo(By.ID, "add_to_cart_laptop", last_success_ts=currentTime))
    ah.store.set("checkout_btn", LocatorInfo(By.ID, "checkout_now", last_success_ts=currentTime))

    # 3. Blog Page
    ah.store.set("read_more", LocatorInfo(By.ID, "read_more_link", last_success_ts=currentTime))
    ah.store.set("comment_box", LocatorInfo(By.ID, "comment_box", last_success_ts=currentTime))
    ah.store.set("post_comment", LocatorInfo(By.ID, "post_comment_btn", last_success_ts=currentTime))
    ah.store.set("subscribe_email", LocatorInfo(By.ID, "subscribe_email", last_success_ts=currentTime))

    # 4. Dashboard Page
    ah.store.set("update_settings", LocatorInfo(By.ID, "update_settings_btn", last_success_ts=currentTime))
    ah.store.set("toggle_dark", LocatorInfo(By.ID, "toggle_dark_mode", last_success_ts=currentTime))
    ah.store.set("view_stats", LocatorInfo(By.ID, "view_analytics", last_success_ts=currentTime))

    # 5. Contact Page
    ah.store.set("contact_name", LocatorInfo(By.ID, "contact_name", last_success_ts=currentTime))
    ah.store.set("contact_msg", LocatorInfo(By.ID, "contact_message", last_success_ts=currentTime))
    ah.store.set("send_btn", LocatorInfo(By.ID, "send_message_btn", last_success_ts=currentTime))

    print("Memory seeded for all 5 scenarios.")

def get_page_url(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return f"file:///{os.path.join(base_dir, filename)}"

def run_login_scenario(ah):
    logging.info("--- SCENARIO 1: LOGIN (index.html) ---")
    print(f"\n--- SCENARIO 1: LOGIN (index.html) ---")
    ah.get(get_page_url("index.html"))
    ah.find("login_button", By.ID, "btn-broken-1").click()
    ah.find("delete_alice_btn", By.ID, "btn-broken-2").click()
    ah.find("profile_email_input", By.ID, "inp-broken-3").send_keys("test@test.com")
    ah.find("save_profile_btn", By.ID, "btn-broken-3").click()

def run_ecommerce_scenario(ah):
    logging.info("--- SCENARIO 2: E-COMMERCE ---")
    print(f"\n--- SCENARIO 2: E-COMMERCE ---")
    ah.get(get_page_url("page_ecommerce.html"))
    ah.find("search_box", By.ID, "search_v1").send_keys("Laptop")
    ah.find("add_laptop", By.ID, "btn_add_laptop_old").click()
    ah.find("checkout_btn", By.ID, "btn_checkout_old").click()

def run_blog_scenario(ah):
    logging.info("--- SCENARIO 3: BLOG ---")
    print(f"\n--- SCENARIO 3: BLOG ---")
    ah.get(get_page_url("page_blog.html"))
    ah.find("read_more", By.ID, "link_read_old").click()
    ah.find("comment_box", By.ID, "txt_comment_old").send_keys("Nice post!")
    ah.find("post_comment", By.ID, "btn_post_old").click()
    ah.find("subscribe_email", By.ID, "inp_sub_old").send_keys("me@blog.com")

def run_dashboard_scenario(ah):
    logging.info("--- SCENARIO 4: DASHBOARD ---")
    print(f"\n--- SCENARIO 4: DASHBOARD ---")
    ah.get(get_page_url("page_dashboard.html"))
    ah.find("update_settings", By.ID, "btn_settings_v1").click()
    ah.find("toggle_dark", By.ID, "btn_dark_v1").click()
    ah.find("view_stats", By.ID, "btn_stats_v1").click()

def run_contact_scenario(ah):
    logging.info("--- SCENARIO 5: CONTACT ---")
    print(f"\n--- SCENARIO 5: CONTACT ---")
    ah.get(get_page_url("page_contact.html"))
    ah.find("contact_name", By.ID, "inp_name_old").send_keys("Alice")
    ah.find("contact_msg", By.ID, "inp_msg_old").send_keys("Hello!")
    ah.find("send_btn", By.ID, "btn_send_old").click()

def main():
    driver = webdriver.Chrome()
    ah = AutoHealingDriver(driver, metrics_path="metrics_rules.json", log_path="logs/auto_heal.log")
    
    # Clear store for clean run
    ah.store._data = {}
    
    seed_memory(ah)
    
    try:
        run_login_scenario(ah)
        run_ecommerce_scenario(ah)
        run_blog_scenario(ah)
        run_dashboard_scenario(ah)
        run_contact_scenario(ah)
        print("\nAll 5 scenarios completed.")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        ah.quit()

if __name__ == "__main__":
    main()
