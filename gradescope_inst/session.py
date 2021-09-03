from bs4 import BeautifulSoup
import requests

class Session:
    def __init__(self, cookies):
        self.cookies = cookies

    def get_courses(self):
        """List all courses that this user can access"""    
        # TODO: handle logout scenario
        r = requests.get("https://www.gradescope.com/", cookies=self.cookies)
        return BeautifulSoup(r.text)