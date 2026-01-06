# baseline_tests.py
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def get_page_url(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return f"file:///{os.path.join(base_dir, filename)}"

def run_login_scenario(driver):
    print("\n--- BASELINE: LOGIN TEST ---")
    driver.get(get_page_url("index.html"))
    
    # Using broken locators on purpose (no healing)
    driver.find_element(By.ID, "btn-broken-1").click()
    driver.find_element(By.ID, "btn-broken-2").click()
    driver.find_element(By.ID, "inp-broken-3").send_keys("test@test.com")
    driver.find_element(By.ID, "btn-broken-3").click()

def main():
    driver = webdriver.Chrome()
    try:
        run_login_scenario(driver)
        print("\nBaseline test completed.")
    except Exception as e:
        print(f"\nBaseline FAILED: {e}")
    finally:
        time.sleep(2)
        driver.quit()

if __name__ == "__main__":
    main()
