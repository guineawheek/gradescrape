# requires: selenium, geckodriver
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import json


def get_driver():
    """returns a selenium webdriver."""
    driver = webdriver.Firefox()
    return driver

def attempt_school_login(school="berkeley"):
    """
    Uses Selenium to interactively grab tokens from an interactive saml login.
    Returns the cookies obtained.  

    You can save the returned cookies as json file and read them back into get_tokens.

    example:


    cookies = attempt_school_login()
    with open("cookies.json", "w") as f:
        json.dump(cookies, f, indent=4)
    
    # ...
    with open("cookies.json") as f:
        cookies = login.get_tokens(json.load(f))
    ses = session.Session(cookies)

    """
    driver = get_driver()
    print("Log into your Calnet ID account.")
    driver.get(f"https://gradescope.com/auth/saml/{school}?remember_me=1")

    while True:
        wait = WebDriverWait(driver, 120)
        try:
            wait.until(lambda driver: driver.current_url.startswith("https://www.gradescope.com") and "saml" not in driver.current_url)
            break
        except TimeoutException:
            pass
    
    print("Successful login detected, dumping cookies")
    cookies = driver.get_cookies()
    driver.close()

    return cookies

def get_tokens(cookie_js):
    """
    Reads in a cookies list as returned by attempt_school_login. 
    See example above.
    """
    # TODO: validate output to ensure all two cookies exist
    ret = {}
    for cookie in cookie_js:
        #if cookie['name'] in ("signed_token", "remember_me", "_gradescope_session"):
        ret[cookie['name']] = cookie['value']
    return ret

__all__ = [attempt_school_login, get_tokens]
if __name__ == "__main__":
    cookies = attempt_school_login()
    with open("cookies.json", "w") as f:
        json.dump(cookies, f, indent=4)
