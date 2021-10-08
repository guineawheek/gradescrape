from typing import TYPE_CHECKING
import typing
import datetime
import requests
from .util import *
if TYPE_CHECKING:
    from .course import Course

__all__ = ["Assignment", "PDFAssignment", "AutograderAssignment"]
class Assignment:
    def __init__(self, course, aid: int):
        self.ses = course.ses
        self.course: Course = course
        self.aid: int = aid
    def get_url(self):
        return self.course.get_url() + f"/assignments/{self.aid}"

class PDFAssignment(Assignment):

    def update_outline(self, outline: list):
        """Patches the outline. Use the format listed below.
        
        [
            {
                "title": "question-1",
                "weight": 4.0,
                "children": [
                    {
                        "title": "subpart",
                        "weight": 2.0,
                    },
                    {
                        "title": "subpart2",
                        "weight": 2.0,
                    }
                ]
            },
            {
                "title": "question-2",
                "weight": 20.0,
            }
        ]
        """

        data = { 
            "assignment": {
                "identification_regions": {
                    "name": None,
                    "sid": None
                }
            },
            "question_data": []
        }

        for q in outline:
            qz = {
                'title': q['title'],
                'crop_rect_list': [{"x1": 0, "x2": 100, "y1": 90, "y2": 100, "page_number": None}],
            }
            children = []
            real_weight = 0
            for subq in q.get('children', []):
                sqz = {
                    'title': subq['title'],
                    'weight': float(subq['weight']),
                    'crop_rect_list': [{"x1": 0, "x2": 100, "y1": 90, "y2": 100, "page_number": None}],
                }
                real_weight += sqz['weight']
                children.append(sqz)
            if children:
                qz['children'] = children
                qz['weight'] = real_weight
            else:
                qz['weight'] = float(q['weight'])
            data['question_data'].append(qz)
        return self.update_outline_raw(data)

            
    def update_outline_raw(self, outline_raw: dict):
        # Patches the outline. Expects the raw structure that gradescope itself uses.

        csrf_token, page=self.ses.get_csrf(self.get_url() + "/outline/edit", True)
        return self.ses.req.patch(self.get_url() + "/outline/", json=outline_raw, headers={"X-CSRF-Token": csrf_token})

        #raise NotImplementedError()

    def update_settings(self, title: str=None, 
                        release_date: datetime.datetime=None, due_date: datetime.datetime=None,
                        allow_late_submissions=False, late_due_date: datetime.datetime=None, 
                        student_submission=True,
                        manual_grading=False,
                        anon_grading=False,
                        group_submission=False, group_size=None,
                        submission_type="image",
                        rubric_select_one=False, 
                        ceiling=True,
                        floor=True,
                        rubric_visibility_setting="show_all_rubric_items",
                        scoring_type="positive",
                        template_pdf_name=None,
                        template_pdf_data=None,
                        ) -> Assignment:
        
        if any([title is None]):
            raise ValueError("title are mandatory arguments!")
        # -----------------------------4020024720658906211394196285
        # Content-Disposition: form-data; name="template_pdf"; filename=""
        # Content-Type: application/octet-stream


        #

        # TODO: make the above mandatory settings optional
        csrf_token, page = self.ses.get_csrf(self.get_url() + "/edit", True) # csrf token

        data = {
            'authenticity_token': csrf_token,
            'utf8': "\u2713",
            '_method': "patch",
            'assignment[title]': title, # assignment title
            'assignment[type]': "PDFAssignment", # pdf assignment
            'assignment[bubble_sheet]': 'false',
            'assignment[student_submission]': str(bool(student_submission)).lower(),
            'assignment[submissions_anonymized]': int(bool(anon_grading)),
            'assignment[release_date_string]':  to_gradescope_time(release_date),
            'assignment[due_date_string]':  to_gradescope_time(due_date),
            'allow_late_submissions': "on" if allow_late_submissions else "0",
            'assignment[group_submission]': int(bool(group_submission)),
            'assignment[manual_grading]': int(bool(manual_grading)),
            'assignment[rubric_visibility_setting]': rubric_visibility_setting, # show_only_applied_rubric_items, hide_all_rubric_items
            'assignment[submission_type]': submission_type, # image, pdf
            'assignment[scoring_type]': scoring_type, # positive, negative
            'assignment[ceiling]': int(bool(ceiling)),
            'assignment[floor]': int(bool(floor)),
            # update_existing_questions
            'assignment[rubric_item_groups_mutually_exclusive]': str(bool(rubric_select_one)),
            # hide_all_rubric_items, show_only_applied_rubric_items also exists, dependent on manual_grading

            'commit': "Save"
        }
        validate_late_submissions(allow_late_submissions, late_due_date, data)
        validate_group_size(group_size, group_submission, data)

        if template_pdf_name is None:
            files = {"template_pdf": ("", b'', 'application/octet-stream')}
        else:
            files = {"template_pdf": (template_pdf_name, template_pdf_data, 'application/octet-stream')}


        return self.ses.post_soup(self.get_url(), data=data, files=files, allow_redirects=False, _return_request_object=True)

class AutograderAssignment(Assignment):
    def update_autograder_zip(self, autograder_zip: bytes, zip_name:str="autograder.zip"):
        """Upload a new autograder zip file. 

        Example usage:
        with open("autograder.zip", "rb") as f: 
            assgn.update_autograder_zip(f.read(), "autograder.zip")
        """

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
    
    def update_settings(self, title: str=None, total_points: float=None, 
                        release_date: datetime.datetime=None, due_date: datetime.datetime=None,
                        allow_late_submissions=False, late_due_date: datetime.datetime=None, manual_grading=False,
                        leaderboard_enabled=False, leaderboard_max_entries=None, group_submission=False, group_size=None,
                        submission_methods=("upload", "github", "bitbucket"), ignored_files="", memory_limit=768, autograder_timeout=600 
                        ) -> Assignment:
        
        if any([title is None, total_points is None, release_date is None, due_date is None]):
            raise ValueError("title, total_points, release_date, due_dare are mandatory arguments!")
        # TODO: make the above mandatory settings optional
        csrf_token, page = self.ses.get_csrf(self.get_url() + "/edit", True) # csrf token

        data = {
            'authenticity_token': csrf_token,
            'utf8': "\u2713",
            '_method': "patch",
            #'configuration': "zip",
            'assignment[title]': title, # assignment title
            'assignment[total_points]': str(total_points), # total points of assignment
            'assignment[type]': "ProgrammingAssignment", # prog assignment
            #'assignment[student_submission]': str(bool(student_submission)).lower(),
            'assignment[release_date_string]':  to_gradescope_time(release_date),
            'assignment[due_date_string]':  to_gradescope_time(due_date),
            'assignment[allow_late_submissions]': "on" if allow_late_submissions else "0",
            'assignment[group_submission]': int(bool(group_submission)),
            'assignment[manual_grading]': int(bool(manual_grading)),
            'assignment[leaderboard_enabled]': int(bool(leaderboard_enabled)),
            'assignment[rubric_visibility_setting]': "show_all_rubric_items",
            # hide_all_rubric_items, show_only_applied_rubric_items also exists, dependent on manual_grading

            'assignment[ignored_files]': ignored_files,
            'assignment[autograder_timeout]': int(autograder_timeout),
            'assignment[memory_limit]': int(memory_limit),
            'commit': "Save"
        }
        validate_late_submissions(allow_late_submissions, late_due_date, data)
        validate_group_size(group_size, group_submission, data)
        validate_leaderboard(leaderboard_max_entries, leaderboard_enabled, data)
        
        for sub_method in ("upload", "github", "bitbucket"):
            data['assignment[submission_methods[' + sub_method + ']]'] = int(sub_method in submission_methods)

        return self.ses.post_soup(self.get_url(), data=data, allow_redirects=False, _return_request_object=True)
        #r = requests.post(self.get_url(), data=data, cookies=self.ses.cookies)
        #r.raise_for_status()
        #return r
    
    def get_settings(self) -> typing.Dict[str, typing.Any]:
        """Gets settings as a dict.
        The intention of this is to have an access pattern that is such:

        settings = assign.get_settings()
        settings["title"] = "New assignment title"
        assign.update_settings(**settings)

        to say, edit specific settings.
        """
        edit = self.ses.get_soup(self.get_url() + "/edit")
        data = {
            "title": form_from_value(edit, "assignment[title]"),
            "total_points": form_from_value(edit, "assignment[total_points]", float),
            "release_date": form_from_date(edit, "assignment[release_date_string]"),
            "due_date": form_from_date(edit, "assignment[due_date_string]"),
            "allow_late_submissions": form_from_checkbox(edit, "allow_late_submissions"),
            "late_due_date": form_from_date(edit, "assignment[hard_due_date_string]"),
            "manual_grading": form_from_checkbox(edit, "assignment[manual_grading]"),
            "leaderboard_enabled": form_from_checkbox(edit, "assignment[leaderboard_enabled]"),
            "leaderboard_max_entries": form_from_value(edit, "assignment[leaderboard_max_entries]", int),
            "group_submission": form_from_checkbox(edit, "assignment[group_submission]"),
            "group_size": form_from_value(edit, "assignment[group_size]", int),
            "ignored_files": form_from_textarea(edit, "assignment[ignored_files]"),
            "memory_limit": int(form_from_radio(edit, "assignment[memory_limit]")),
            "autograder_timeout": int(form_from_select(edit, "assignment[autograder_timeout]"))
        }
        #"submission_methods": form_from_
        data['submission_methods'] = []
        for sub_method in ("upload", "github", "bitbucket"):
            enabled = form_from_checkbox(edit, 'assignment[submission_methods[' + sub_method + ']]')
            if enabled:
                data['submission_methods'].append(sub_method)
        
        return data



    def get_url(self):
        return f"{BASE_URL}/courses/{self.course.cid}/assignments/{self.aid}"