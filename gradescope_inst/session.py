from bs4 import BeautifulSoup
import requests
import datetime


class Session:
    def __init__(self, cookies):
        self.cookies = cookies
    
    def get_soup(self, url) -> BeautifulSoup:
        r = requests.get(url, cookies=self.cookies)
        r.raise_for_status()

        return BeautifulSoup(r.text, features="lxml")


    def get_courses(self):
        """List all courses that this user can access"""    
        # TODO: handle logout scenario
        soup = self.get_soup("https://www.gradescope.com/")

        #for a in cs.find_all("a", class_="courseBox"):
        #    print(a['href'])
        return soup #BeautifulSoup(r.text, features="lxml")

class Course:
    def __init__(self, session: Session, cid: int):
        self.ses = session
        self.cid = cid
        self.name = None
        self.is_instr = None
        self.assignments = []

    def get_url(self):
        return f"https://www.gradescope.com/courses/{self.cid}"
    
    def reload_dashboard(self):
        """Reloads name, instructor, and assignment data from Gradescope.
        Unsubmittable assignments (past due) from student perspective are not covered.
        """ 
        for a in self.ses.get_soup(self.get_url()).find_all("a", href=True):
            pass
    
    def get_assignment(self, aid: int):
        """Gets the assignment object for a current assignment. Raises exception
        if assignment does not exist."""
        v = self.ses.get_soup(self.get_url() + f"/assignments/{aid}")

    def create_assignment(self, *args, **kwargs):

        # Run GET on /assignments to fetch the csrf token. The csrf token is the same
        # for all form submits on this page.
        # Data is multipart/form-data.

        # authenticity_token: scraped from /assignments
        # assignment[title]: str
        # assignment[student_submission]: false for instr, true for student
        # assignment[release_date_string]:  date in format `Sep 3 2021 08:00 PM`. No idea what timezone this sits in.
        # assignment[due_date_string]: 
        pass

def to_gradescope_time(d: datetime.datetime):
    # Fun fact: Gradescope uses a cursed time/date format. 
    # (Specifically, it does not zero-pad the day of the month.)
    # It looks something like this:
    #   Sep 3 2021 12:08 PM
    # This converts a datetime object into that cursed format, since it does not fit strftime.

    # we use this to be locale-invariant. There's plenty of other bugs, but locale BS will nomt
    # be one of them.
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ampm = "AM" if d.hour >= 12 else "PM"
    return f"{months[d.month-1]} {d.day} {d.year} " + d.strftime("%I:%M ") + ampm