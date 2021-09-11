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

    def create_assignment(self, title: str, submission_type, template_pdf_name: str, template_pdf_data: bytes, 
                                release_date: datetime.datetime, due_date: datetime.datetime,
                                allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True,
                                enforce_time_limit=False, time_limit=None, group_submission=False, group_size=None,
                                template_visible=False):


        # Run GET on /assignments to fetch the csrf token. The csrf token is the same
        # for all form submits on this page.
        # Data is multipart/form-data.

        # authenticity_token: scraped from /assignments
        # template_pdf: the file template pdf, as a form file
        # For code, use  {'template_pdf': ('template.pdf', open('template.pdf','rb'), 'application/pdf')}

        # assignment[title]: str
        # assignment[student_submission]: false for instr, true for student. Only thing on form that uses true or false.
        # assignment[release_date_string]:  date in format `Sep 3 2021 08:00 PM`. No idea what timezone this sits in.
        # assignment[due_date_string]:  date in format `Sep 3 2021 08:00 PM`. No idea what timezone this sits in.
        # assignment[allow_late_submissions]: 0 or 1. self explanatory.
        # assignment[hard_due_date_string]:  the late submission due date or ""
        # assignment[enforce_time_limit]: 0 or 1
        # assignment[time_limit_in_minutes]: omitted or number, min 1
        # assignment[submission_type]: "image" or "pdf". "image" allows students to select pages.
        # assignment[group_submission]: 0 or 1
        # assignment[group_size]: omitted or number
        # assignment[template_visible_to_students]: 0 or 1
        #
        # strangely, gradescope forms send both 0 and 1 for enabled options. Let's hope the server-side
        # scripts specifically only check for the existence of ones.

        page = self.ses.get_soup(self.get_url() + "/assignments")
        csrf_token = page.find("meta", attrs={"name": "csrf-token"})['content'] 

        files = {"template_pdf": (template_pdf_name, template_pdf_data, 'application/pdf')}
        data = {
            'authenticity_token': csrf_token,
            'assignment[title]': title,
            'assignment[student_submission]': str(bool(student_submission)).lower(),
            'assignment[release_date_string]':  to_gradescope_time(release_date),
            'assignment[due_date_string]':  to_gradescope_time(due_date),
            'assignment[allow_late_submissions]': int(bool(allow_late_submissions)),
            'assignment[enforce_time_limit]': int(bool(enforce_time_limit)),
            'assignment[submission_type]': submission_type,
            'assignment[group_submission]': int(bool(group_submission)),
            'assignment[template_visible_to_students]': int(bool(template_visible)),
        }

        if allow_late_submissions:
            if late_due_date is None:
                raise ValueError("allow_late_submissions requires a late due date")
            data['assignment[hard_due_date_string]'] = to_gradescope_time(late_due_date)

        if enforce_time_limit:
            if time_limit is None or time_limit < 1:
                raise ValueError("enforce_time_limit requires time_limit to be an integer >= 1")
            data['assignment[time_limit_in_minutes]'] = int(time_limit)
        
        if group_size is not None:
            if not group_submission:
                raise ValueError("group_size requires group_submission to be True")
            if group_size <= 1:
                raise ValueError("group_size should be larger than 1; if you want solo submissions, set group_submission=False")
            data['assignment[group_size]'] = int(group_size)
        
        return requests.post(self.get_url() + "/assignments", data=data, files=files, cookies=self.ses.cookies)


def to_gradescope_time(d: datetime.datetime):
    # Fun fact: Gradescope uses a cursed time/date format. 
    # (Specifically, it does not zero-pad the day of the month.)
    # It looks something like this:
    #   Sep 3 2021 12:08 PM
    # This converts a datetime object into that cursed format, since it does not fit strftime.

    # we use this to be locale-invariant. There's plenty of other bugs, but locale BS will nomt
    # be one of them.
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ampm = "AM" if d.hour < 12 else "PM"
    return f"{months[d.month-1]} {d.day} {d.year} " + d.strftime("%I:%M ") + ampm