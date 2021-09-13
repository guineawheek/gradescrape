from typing import TYPE_CHECKING
import datetime
from .util import to_gradescope_time, BASE_URL

if TYPE_CHECKING:
    from .session import Session

__all__ = ["Assignment", "PDFAssignment", "AutograderAssignment"]
class Assignment:
    def __init__(self, session: Session, course, aid: int):
        self.ses = session
        self.course = course
        self.aid = aid

class PDFAssignment(Assignment):
    def update_pdf_outline(self, outline: dict):
        raise NotImplementedError()

class AutograderAssignment(Assignment):
    def update_autograder_zip(self, autograder_zip: bytes, zip_name:str="autograder.zip"):

        csrf_token, page = self.ses.get_csrf(self.get_url() + "/configure_autograder", True) # csrf token

        data = {
            'authenticity_token': csrf_token,
            'utf8': "\u2713",
            '_method': "patch",
            'configuration': "zip",
            'assignment[image_name]': page.find("input", attrs={"name": "assignment[image_name]"}).get("value", "")
        }
        files = {"autograder_zip": (zip_name, autograder_zip, 'application/zip')}
        return self.ses.post_soup(self.get_url(), data=data, files=files)
    
    def update_settings(self, title: str, total_points: float, 
                        release_date: datetime.datetime, due_date: datetime.datetime,
                        allow_late_submissions=False, late_due_date: datetime.datetime=None, student_submission=True, manual_grading=False,
                        leaderboard_enabled=False, leaderboard_max_entries=None, group_submission=False, group_size=None,
                        submission_methods=("upload", "github", "bitbucket"), ignored_files="", memory_limit=768, autograder_timeout=600 
                        ) -> Assignment:
        # TODO: make the above mandatory settings optional
        csrf_token, page = self.ses.get_csrf(self.get_url() + "/edit", True) # csrf token

        data = {
            'authenticity_token': csrf_token,
            'utf8': "\u2713",
            '_method': "patch",
            'configuration': "zip",
            'assignment[title]': title, # assignment title
            'assignment[total_points]': str(total_points), # total points of assignment
            'assignment[type]': "ProgrammingAssignment", # prog assignment
            'assignment[student_submission]': str(bool(student_submission)).lower(),
            'assignment[release_date_string]':  to_gradescope_time(release_date),
            'assignment[due_date_string]':  to_gradescope_time(due_date),
            'assignment[allow_late_submissions]': "on" if allow_late_submissions else "0",
            'assignment[group_submission]': int(bool(group_submission)),
            'assignment[manual_grading]': int(bool(manual_grading)),
            'assignment[leaderboard_enabled]': int(bool(leaderboard_enabled)),
            'assignment[rubric_visibility_setting]': "show_all_rubric_items",
            'assignment[ignored_files]': ignored_files,
            'assignment[autograder_timeout]': int(autograder_timeout),
            'assignment[memory_limit]': int(memory_limit),
            'commit': "Save"
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
        
        for sub_method in ("upload", "github", "bitbucket"):
            data['assignment[submission_methods[' + sub_method + ']]'] = int(sub_method in submission_methods)
        

        return self.ses.post_soup(self.get_url(), data=data)
        #r = requests.post(self.get_url(), data=data, cookies=self.ses.cookies)
        #r.raise_for_status()
        #return r


    def get_url(self):
        return f"{BASE_URL}/courses/{self.course.cid}/assignments/{self.aid}"