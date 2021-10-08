
import datetime
from urllib.parse import urlparse
from .util import BASE_URL, to_gradescope_time, validate_late_submissions, validate_group_size, validate_leaderboard
import typing
from .assignment import Assignment, AutograderAssignment, PDFAssignment
if typing.TYPE_CHECKING:
    from .session import Session
__all__ = ["Course"]
class Course:
    def __init__(self, session, cid: int):
        self.ses: Session = session
        self.cid: int = cid
        #self.name: str = None
        #self.is_instr: str = None
        #self.assignment: str = []

    def get_url(self) -> str:
        return f"{BASE_URL}/courses/{self.cid}"
    
    #def reload_dashboard(self):
    #    """Reloads name, instructor, and assignment data from Gradescope.
    #    Unsubmittable assignments (past due) from student perspective are not covered.
    #    """ 
    #    for a in self.ses.get_soup(self.get_url()).find_all("a", href=True):
    #        pass
    
    def list_assignments(self) -> typing.Dict[str, int]:
        """Lists the current assignment names -> ids for the current course.
        Returns a mapping of assignment name to assignment id.
        
        (It's a more likely use case to select an assignment by name to get the id rather
        than the other way around, and assignment names are guarenteed to be unique.)
        """
        assgn_table = self.ses.get_soup(self.get_url() + f"/assignments")
        d = {}
        for a in assgn_table.find("table", id="assignments-instructor-table").find_all("a"):
            href = a['href']
            assgn_base = f"/courses/{self.cid}/assignments/"
            if href.startswith(assgn_base):
                rest = href[len(assgn_base):]
                if "/" in rest:
                    continue
                try:
                    aid = int(rest)
                except ValueError:
                    continue
                d[a.text] = aid
        return d


    def get_assignment_by_name(self, assign_name: str, assign_type=Assignment):
        """Gets the assignment object for a current assignment. 
        The assignment object returned will be of the type specified in `assign_type`.
        Returns None if assignment does not exist."""

        assignments = self.list_assignments()
        if assign_name not in assignments:
            return None
        return assign_type(self, assignments[assign_name])
        #v = self.ses.get_soup(self.get_url() + f"/assignments/{aid}")


    def create_prog_assignment(self, title: str, total_points: float, 
                                release_date: datetime.datetime, due_date: datetime.datetime,
                                allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True,
                                leaderboard_enabled=False, leaderboard_max_entries=None, group_submission=False, group_size=None) -> AutograderAssignment:

        """
        Creates a new programming assignment. Note that this does not include an autograder. 

        Positional arguments:

        title                   --  string of the assignment title.
        total_points            --  float of the total number of points of this assignment.
        release_date            --  datetime.datetime of the release date of the assignment.
        due_date                --  datetime.datetime of the due date of the assignment

        Keyword arguments:

        allow_late_submissions  -- whether to allow late submissions. Defaults False.
        late_due_date           -- datetime.datetime of the late submission due date, 
                                   if any, otherwise None.
        student_submission      -- whether to allow students to submit at all, which 
                                   is useful to disable for things like
                                   autograded progress trackers.  Defaults False.
        leaderboard_enabled     -- whether to enable a points leaderboard. Defaults False.
        leaderboard_max_entries -- the maximum number of entries to show on a leaderboard,
                                   or None for no max.
        group_submission        -- whether to allow groups in assignment submissions. 
                                   Defaults False.
        group_size              -- integer describing the size of the group, or None.

        
        Returns: AutograderAssignment object with the current session object embedded and the 
        newly created assignment id.
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
        validate_late_submissions(allow_late_submissions, late_due_date, data)
        validate_group_size(group_size, group_submission, data)
        validate_leaderboard(leaderboard_max_entries, leaderboard_enabled, data)

        r = self.ses.req.post(self.get_url() + "/assignments", data=data)
        r.raise_for_status()

        aid = int(urlparse(r.url).path.split("/")[4])
        return AutograderAssignment(self, aid)

    def create_pdf_assignment(self, title: str, template_pdf_name: str, template_pdf_data: bytes, 
                                release_date: datetime.datetime, due_date: datetime.datetime, submission_type: str="image", 
                                allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True,
                                enforce_time_limit=False, time_limit=None, group_submission=False, group_size=None, anon_grading=False,
                                template_visible=False) -> PDFAssignment:

        """
        Creates a new PDF assignment. Students usually submit PDFs to this assignment to be graded manually.
        Note that this does not create an outline for the assignment which will give the assignment selectable questions
        in the page select screen; that must be done in a secondary call to PDFAssignment.update_pdf_outline().

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
        anon_grading            -- whether to anonymize student submissions when grading
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
            'assignment[submissions_anonymized]': int(bool(anon_grading)),
        }
        validate_late_submissions(allow_late_submissions, late_due_date, data)
        validate_group_size(group_size, group_submission, data)

        if enforce_time_limit:
            if time_limit is None or time_limit < 1:
                raise ValueError("enforce_time_limit requires time_limit to be an integer >= 1")
            data['assignment[time_limit_in_minutes]'] = int(time_limit)
        
        r = self.ses.req.post(self.get_url() + "/assignments", data=data, files=files)
        r.raise_for_status()

        aid = int(urlparse(r.url).path.split("/")[4])
        return PDFAssignment(self, aid)