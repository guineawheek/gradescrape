import datetime
BASE_URL = "https://www.gradescope.com"
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

def validate_late_submissions(allow_late_submissions, late_due_date, data):
    if allow_late_submissions:
        if late_due_date is None:
            raise ValueError("allow_late_submissions requires a late due date")
        data['assignment[hard_due_date_string]'] = to_gradescope_time(late_due_date)

    
def validate_group_size(group_size, group_submission, data):
    if group_size is not None:
        if not group_submission:
            raise ValueError("group_size requires group_submission to be True")
        if group_size <= 1:
            raise ValueError("group_size should be larger than 1; if you want solo submissions, set group_submission=False")
        data['assignment[group_size]'] = int(group_size)


def validate_leaderboard(leaderboard_max_entries, leaderboard_enabled, data):
    if leaderboard_max_entries is not None:
        if not leaderboard_enabled:
            raise ValueError("leaderboard_max_entries requires leaderboard_enabled to be True")
        if leaderboard_max_entries < 0:
            raise ValueError("leaderboard_max_entries should be non-negative")
        data['assignment[leaderboard_max_entries]'] = int(leaderboard_max_entries)