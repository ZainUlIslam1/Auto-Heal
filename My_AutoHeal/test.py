import os
from selenium import webdriver
from selenium.webdriver.common.by import By

from driver import AutoHealingDriver


def main():
    driver = webdriver.Chrome()
    ah = AutoHealingDriver(driver)

    try:
        page_path = os.path.abspath("index.html")
        url = f"file:///{page_path}"

        print(f"Opening {url}")
        ah.get(url)

        login_button = ah.find(
            name="login_button",
            by=By.ID,
            value="login-btn",
        )
        print("Found login button, clicking...")
        login_button.click()

        username_input = ah.find(
            name="username_field",
            by=By.ID,
            value="username",
        )
        login_button = ah.find(
        name="login_button",
        by=By.CSS_SELECTOR,
        value="btn primary",
        )

        username_input.send_keys("test_user")
        print("Typed username")

    finally:
        ah.quit()
        print("Run finished. Check locator_store.json, metrics.json and logs/auto_heal.log")


if __name__ == "__main__":
    main()
