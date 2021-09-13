# requires: selenium, geckodriver
import json
from .session import Session
import requests
from bs4 import BeautifulSoup


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
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException
    driver = webdriver.Firefox()
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

def login_session(username: str, password: str):
    """
    Logs in with a regular old Gradescope username and password. 
    SAML is difficult to script anyway.
    """
    #TODO: this flow is non-functional for some reason -- gradescope returns 301 instead of 302

    s = requests.Session()
    url = "https://www.gradescope.com/"
    page = BeautifulSoup(s.get(url).text)
    csrf_token = page.find("meta", attrs={"name": "csrf-token"})['content'] 
    data = {
        "authenticity_token": csrf_token,
        "session[email]": username,
        "session[password]": password,
        "session[remember_me]": "1",
        "commit": "Log In",
        "session[remember_me_sso]": "0"
    }

    r = s.post(url + "/login", data=data)
    return Session(s.cookies)

__all__ = [attempt_school_login, get_tokens]
if __name__ == "__main__":
    cookies = attempt_school_login()
    with open("cookies.json", "w") as f:
        json.dump(cookies, f, indent=4)
