from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()
driver.get("file:/testpage.html")

try:
    login_button = driver.find_element(By.ID, "loginBtn")
    login_button.click()
    print("Button found and clicked successfully.")
except Exception as e:
    print("Error occurred:", e)

driver.quit()

