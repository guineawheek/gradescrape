# requires: selenium, geckodriver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import json


def get_driver():
    driver = webdriver.Firefox()
    return driver

def attempt_school_login(school="berkeley"):
    driver = get_driver()
    print("Log into your Calnet ID account.")
    driver.get(f"https://gradescope.com/auth/saml/{school}?remember_me=1")

    while True:
        wait = WebDriverWait(driver, 120)
        try:
            wait.until(lambda driver: driver.current_url.startswith("https://www.gradescope.com"))
            break
        except TimeoutException:
            pass
    
    print("Successful login detected, dumping cookies")
    cookies = driver.get_cookies()
    driver.close()

    return cookies

def get_tokens(cookie_js):
    # TODO: validate output to ensure all two cookies exist
    ret = {}
    for cookie in cookie_js:
        if cookie['name'] in ("signed_token", "remember_me"):
            ret[cookie['name']] = cookie['value']
    return ret

__all__ = [attempt_school_login, get_tokens]
if __name__ == "__main__":
    cookies = attempt_school_login()
    with open("cookies.json", "w") as f:
        json.dump(cookies, f, indent=4)
