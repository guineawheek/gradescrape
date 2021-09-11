from bs4 import BeautifulSoup
import requests
import datetime
from urllib.parse import urlparse


__all__ = ["Session", "Course", "Assignment"]
BASE_URL = "https://www.gradescope.com"

class Session:
    def __init__(self, cookies):
        if type(cookies) == list:
            self.cookies = {}
            for cookie in cookies:
                #if cookie['name'] in ("signed_token", "remember_me", "_gradescope_session"):
                self.cookies[cookie['name']] = cookie['value']
        else:
            self.cookies = cookies
    
    def get_soup(self, url) -> BeautifulSoup:
        r = requests.get(url, cookies=self.cookies)
        r.raise_for_status()

        return BeautifulSoup(r.text, features="lxml")
    
    def post_soup(self, url) -> BeautifulSoup:
        pass


    def get_courses(self):
        """List all courses that this user can access"""    
        # TODO: handle logout scenario
        soup = self.get_soup(BASE_URL)

        #for a in cs.find_all("a", class_="courseBox"):
        #    print(a['href'])
        return soup #BeautifulSoup(r.text, features="lxml")
    
    def get_course(self, cid):
        return Course(self, cid)

class Assignment:
    def __init__(self, session: Session, course, aid: int):
        self.ses = session
        self.course = course
        self.aid = aid
    
    def update_pdf_outline(self, outline: dict):
        raise NotImplementedError()

    def update_autograder_zip(self, autograder_zip: bytes, zip_name:str="autograder.zip"):
        page = self.ses.get_soup(self.get_url() + "/configure_autograder")
        csrf_token = page.find("meta", attrs={"name": "csrf-token"})['content'] 

        data = {
            'authenticity_token': csrf_token, # csrf token
            'utf8': "\u2713",
            '_method': "patch",
            'configuration': "zip",
            'assignment[image_name]': page.find("input", attrs={"name": "assignment[image_name]"})['value']
        }
        files = {"autograder_zip": (zip_name, autograder_zip, 'application/zip')}

        r = requests.post(self.get_url(), data=data, files=files, cookies=self.ses.cookies)
        r.raise_for_status()


    def get_url(self):
        return f"{BASE_URL}/courses/{self.course.cid}/assignments/{self.aid}"

class Course:
    def __init__(self, session: Session, cid: int):
        self.ses = session
        self.cid = cid
        self.name = None
        self.is_instr = None
        self.assignments = []

    def get_url(self):
        return f"{BASE_URL}/courses/{self.cid}"
    
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

    def create_prog_assignment(self, title: str, total_points: float, 
                                release_date: datetime.datetime, due_date: datetime.datetime,
                                allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True,
                                leaderboard_enabled=False, leaderboard_max_entries=None, group_submission=False, group_size=None) -> Assignment:

        """
        Creates a new programming assignment. Note that this does not include an autograder. 

        Positional arguments:

        title                   --  string of the assignment title.
        total_points            --  float of the total number of points of this assignment.
        release_date            --  datetime.datetime of the release date of the assignment.
        due_date                --  datetime.datetime of the due date of the assignment

        Keyword arguments:

        allow_late_submissions  -- whether to allow late submissions. Defaults False.
        late_due_date           -- datetime.datetime of the late submission due date, if any, otherwise None.
        student_submission      -- whether to allow students to submit at all, which is useful to disable for things like
                                   autograded progress trackers.  Defaults False.
        leaderboard_enabled     -- whether to enable a points leaderboard. Defaults False.
        leaderboard_max_entries -- the maximum number of entries to show on a leaderboard, or None for no max.
        group_submission        -- whether to allow groups in assignment submissions. Defaults False.
        group_size              -- integer describing the size of the group, or None.

        
        Returns: Assignment object with the current session object embedded and the newly created assignment id.
        """


        # pull csrf token from the assignments page
        page = self.ses.get_soup(self.get_url() + "/assignments")
        csrf_token = page.find("meta", attrs={"name": "csrf-token"})['content'] 

        data = {
            'authenticity_token': csrf_token, # csrf token
            'assignment[title]': title, # assignment title
            'assignment[total_points]': str(total_points), # total points of assignment
            'assignment[type]': "ProgrammingAssignment", # prog assignment
            'assignment[student_submission]': str(bool(student_submission)).lower(),
            'assignment[release_date_string]':  to_gradescope_time(release_date),
            'assignment[due_date_string]':  to_gradescope_time(due_date),
            'assignment[allow_late_submissions]': int(bool(allow_late_submissions)),
            'assignment[group_submission]': int(bool(group_submission)),
            'assignment[leaderboard_enabled]': int(bool(leaderboard_enabled)),
        }

        if allow_late_submissions:
            if late_due_date is None:
                raise ValueError("allow_late_submissions requires a late due date")
            data['assignment[hard_due_date_string]'] = to_gradescope_time(late_due_date)

        
        if group_size is not None:
            if not group_submission:
                raise ValueError("group_size requires group_submission to be True")
            if group_size <= 1:
                raise ValueError("group_size should be larger than 1; if you want solo submissions, set group_submission=False")
            data['assignment[group_size]'] = int(group_size)
        
        if leaderboard_max_entries is not None:
            if not leaderboard_enabled:
                raise ValueError("leaderboard_max_entries requires leaderboard_enabled to be True")
            if leaderboard_max_entries < 0:
                raise ValueError("leaderboard_max_entries should be non-negative")
            data['assignment[group_size]'] = int(group_size)
        r = requests.post(self.get_url() + "/assignments", data=data, cookies=self.ses.cookies)
        r.raise_for_status()

        aid = int(urlparse(r.url).path.split("/")[4])
        return Assignment(self.ses, self, aid)

    def create_pdf_assignment(self, title: str, template_pdf_name: str, template_pdf_data: bytes, 
                                release_date: datetime.datetime, due_date: datetime.datetime, submission_type: str="image", 
                                allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True,
                                enforce_time_limit=False, time_limit=None, group_submission=False, group_size=None,
                                template_visible=False) -> Assignment:

        """
        Creates a new PDF assignment. Students usually submit PDFs to this assignment to be graded manually.
        Note that this does not create an outline for the assignment which will give the assignment selectable questions
        in the page select screen; that must be done in a secondary call to Assignment.update_pdf_outline().

        So you might do something like...

        course = session.get_course(course_id)
        pdf_assgn = course.create_pdf_assignment(...)
        pdf_assgn.update_pdf_outline(outline)

        Positional arguments:

        title                   --  string of the assignment title.
        template_pdf_name       --  the display filename of the pdf template, like "Homework_1.pdf". Students will
                                    see this name when Gradescope tells them in the submit menu that there's a provided 
                                    pdf for them to reference.
        template_pdf_data       --  the bytes data of the template PDF. Typically read from an open(..., "rb") call.
        release_date            --  datetime.datetime of the release date of the assignment.
        due_date                --  datetime.datetime of the due date of the assignment


        Keyword arguments:

        template_visible        -- whether to suggest the template pdf to students when they open the submission dialog.
        submission_type         -- a string of either "pdf" or "image". "image" allows students to select pages. Defaults to "image"
        allow_late_submissions  -- whether to allow late submissions. Defaults False.
        late_due_date           -- datetime.datetime of the late submission due date, if any, otherwise None.
        student_submission      -- whether to allow students to submit at all, which is useful to disable for things like
                                   displaying graded in-person paper exams. Defaults True.
        time_limit              -- time in minutes to allow the student to submit the assignment once opened. Useful for things like
                                   online timed exams. None, if there is no time limit. Defaults None.
        enforce_time_limit      -- whether to enforce the assignment's time limit. Defaulse False.
        group_submission        -- whether to allow groups in assignment submissions. Defaults False.
        group_size              -- integer describing the size of the group, or None for no maximum or not applicable. Defaults None.

        
        Returns: Assignment object with the current session object embedded and the newly created assignment id.
        """

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
        
        r = requests.post(self.get_url() + "/assignments", data=data, files=files, cookies=self.ses.cookies)
        r.raise_for_status()

        aid = int(urlparse(r.url).path.split("/")[4])
        return Assignment(self.ses, aid)


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