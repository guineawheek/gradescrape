import datetime
BASE_URL = "https://www.gradescope.com"

def date_at(dt=None, hour=23, minute=59):
    """Utility function that returns either today's date or a specific datetime with a certain hour and minute."""
    if not dt:
        dt = datetime.datetime.today()
    return datetime.datetime(dt.year, dt.month, dt.day, hour=hour, minute=minute)

def next_day(day_str, hour=23, minute=59):
    """Utility function to get the next of:
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    If today's date is the day_str, then we take a date a week from now.
    The hour and minute returned is by default 11:59 PM.
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    wd = days.index(day_str)
    now = datetime.datetime.now()
    return date_at(now + datetime.timedelta(days=((wd - now.weekday() - 1) % 7 + 1)))

def to_gradescope_time(d: datetime.datetime):
    """
    Converts datetime.datetime objects to gradescope's time/date format.

    Fun fact: it's a cursed time/date format that does not fit strftime.
    (Specifically, it does not zero-pad the day of the month.)
    It looks something like this:
      Sep 3 2021 12:08 PM
    This converts a datetime object into that cursed format, since it does not fit strftime.
    """

    # we use this to be locale-invariant. There's plenty of other bugs, but locale BS will nomt
    # be one of them.
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ampm = "AM" if d.hour < 12 else "PM"
    return f"{months[d.month-1]} {d.day} {d.year} " + d.strftime("%I:%M ") + ampm

def from_gradescope_time(gs_time: str):
    """Converts gradescope's date/time string format to datetime.datetime objects."""
    return datetime.datetime.strptime(gs_time.strip(), "%b %d %Y %I:%M %p")

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
        #if not leaderboard_enabled:
        #    raise ValueError("leaderboard_max_entries requires leaderboard_enabled to be True")
            
        if leaderboard_max_entries < 0:
            raise ValueError("leaderboard_max_entries should be non-negative")
        data['assignment[leaderboard_max_entries]'] = int(leaderboard_max_entries)

def form_from_value(soup, field_name, wrap=str):
    s = soup.find("input", {"name": field_name}).get("value", None)
    if s is None:
        return None
    return wrap(s)

def form_from_date(soup, field_name):
    return form_from_value(soup, field_name, from_gradescope_time)

def form_from_checkbox(soup, field_name, use_id=False):

    if use_id:
        attrs = {"id": field_name, "type": "checkbox"}
    else:
        attrs = {"name": field_name, "type": "checkbox"}
    box = soup.find("input", attrs=attrs)
    return "checked" in box.attrs

def form_from_textarea(soup, field_name):
    return soup.find("textarea", attrs={"name": field_name}).get("value", "")

def form_from_radio(soup, field_name):
    s = soup.find_all("input", attrs={"name": field_name, "type": "radio"})
    first = s[0]
    for rad in s:
        if "checked" in rad.attrs:
            return rad['value']
    return first['value']
        
def form_from_select(soup, field_name):
    sel = soup.find("select", attrs={"name": field_name})
    s = sel.find_all("option")
    first = s[0]
    for rad in s:
        if "selected" in rad.attrs:
            return rad['value']
    return first['value']