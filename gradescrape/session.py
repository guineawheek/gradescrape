from bs4 import BeautifulSoup
import requests
from .util import BASE_URL 
from typing import TYPE_CHECKING
from .course import Course


# TODO: 
# * Make Session (and all other requests)use a single requests.Session
#  * Other general code cleanup
# * Have configuration read scripts.
# * Have some sort of get_assignment_by_name for a Course

__all__ = ["Session"]

class Session:
    def __init__(self, ses: requests.Session=None):
        self.req : requests.Session = ses if ses else requests.Session()
        #if type(cookies) == list:
        #    self.cookies = {}
        #    for cookie in cookies:
        #        #if cookie['name'] in ("signed_token", "remember_me", "_gradescope_session"):
        #        self.cookies[cookie['name']] = cookie['value']
        #else:
        #    self.cookies = cookies

    def login(self, username: str, password: str) -> requests.Response:
        """
        Logs in with a regular old Gradescope username and password. 
        SAML is difficult to script anyway.
        """

        page = self.get_soup(BASE_URL)
        csrf_token = page.find("meta", attrs={"name": "csrf-token"})['content'] 
        data = {
            "authenticity_token": csrf_token,
            "session[email]": username,
            "session[password]": password,
            "session[remember_me]": "1",
            "commit": "Log In",
            "session[remember_me_sso]": "0"
        }

        r = self.req.post(BASE_URL + "/login", data=data)
        r.raise_for_status()
        return r

    def get_soup(self, *args, **kwargs) -> BeautifulSoup:

        ret_r = False
        if "_return_request_object" in kwargs:
            ret_r = True
            del kwargs["_return_request_object"]
        r = self.req.get(*args, **kwargs)
        r.raise_for_status()
        if ret_r:
            return BeautifulSoup(r.text, features="lxml"), r

        return BeautifulSoup(r.text, features="lxml")
    
    def post_soup(self, *args, **kwargs) -> BeautifulSoup:
        ret_r = False
        if "_return_request_object" in kwargs:
            ret_r = True
            del kwargs["_return_request_object"]
        r = self.req.post(*args, **kwargs)
        r.raise_for_status()
        if ret_r:
            return BeautifulSoup(r.text, features="lxml"), r

        return BeautifulSoup(r.text, features="lxml")


    def get_courses(self):
        """List all courses that this user can access"""    
        # TODO: handle logout scenario
        soup = self.get_soup(BASE_URL)

        #for a in cs.find_all("a", class_="courseBox"):
        #    print(a['href'])
        return soup #BeautifulSoup(r.text, features="lxml")
    
    def get_course(self, cid) -> Course:
        return Course(self, cid)
    
    def get_csrf(self, url, return_page=False) -> str:
        page = self.get_soup(url)
        if return_page:
            return page.find("meta", attrs={"name": "csrf-token"})['content'], page
        else:
            return page.find("meta", attrs={"name": "csrf-token"})['content']

