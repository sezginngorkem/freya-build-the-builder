"""Calendar and date arithmetic for policy rules.

Generic: no bank, brief or holiday is hard-coded here. A calendar is a dict
{"workdays": ["Mon", ...], "holidays": ["YYYY-MM-DD", ...]} built from the brief.
Standard library only (json, re, datetime) so the same file can run inside a Freya code node.
"""
import datetime as _dt

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAY_NAMES = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
DEFAULT_CALENDAR = {"workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"], "holidays": []}


def to_date(x):
    """Accept a date, a datetime, or an ISO string ('2026-10-14' or '2026-10-14T11:00')."""
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    s = str(x).strip()
    return _dt.date.fromisoformat(s[:10])


def to_datetime(x):
    if isinstance(x, _dt.datetime):
        return x
    if isinstance(x, _dt.date):
        return _dt.datetime(x.year, x.month, x.day)
    s = str(x).strip().replace("Z", "")
    if len(s) == 10:
        s += "T00:00"
    return _dt.datetime.fromisoformat(s)


def iso(d):
    return to_date(d).isoformat()


def weekday_index(name):
    i = _DAY_NAMES.get(str(name).strip().lower())
    if i is None:
        raise ValueError("unknown weekday: %r" % name)
    return i


def _holidays(cal):
    return set(str(h)[:10] for h in (cal or {}).get("holidays", []))


def _workdays(cal):
    days = (cal or {}).get("workdays") or DEFAULT_CALENDAR["workdays"]
    return set(weekday_index(d) for d in days)


def is_business_day(d, cal=None):
    d = to_date(d)
    return d.weekday() in _workdays(cal) and d.isoformat() not in _holidays(cal)


def is_holiday(d, cal=None):
    return to_date(d).isoformat() in _holidays(cal)


def add_business_days(d, n, cal=None):
    """The n-th business day AFTER d (d itself is not counted). n=0 returns d unchanged."""
    d = to_date(d)
    n = int(n)
    step = 1 if n >= 0 else -1
    left = abs(n)
    while left:
        d += _dt.timedelta(days=step)
        if is_business_day(d, cal):
            left -= 1
    return d


def next_business_day(d, cal=None, include_same=False):
    """First business day after d; with include_same=True, d itself if it is one."""
    d = to_date(d)
    if include_same and is_business_day(d, cal):
        return d
    d += _dt.timedelta(days=1)
    for _ in range(366):
        if is_business_day(d, cal):
            return d
        d += _dt.timedelta(days=1)
    raise ValueError("no business day within a year")


def prev_business_day(d, cal=None, include_same=False):
    d = to_date(d)
    if include_same and is_business_day(d, cal):
        return d
    d -= _dt.timedelta(days=1)
    for _ in range(366):
        if is_business_day(d, cal):
            return d
        d -= _dt.timedelta(days=1)
    raise ValueError("no business day within a year")


def week_start(d):
    """Monday of d's calendar week."""
    d = to_date(d)
    return d - _dt.timedelta(days=d.weekday())


def last_business_day_of_week(d, offset_weeks=0, cal=None):
    """Last business day of the calendar week (Mon-Sun) containing d, shifted by offset_weeks.
    Returns None if that week has no business day."""
    d = to_date(d)
    for extra in (0, 1):
        start = week_start(d) + _dt.timedelta(weeks=int(offset_weeks) + extra)
        found = None
        for i in range(6, -1, -1):
            day = start + _dt.timedelta(days=i)
            if is_business_day(day, cal):
                found = day
                break
        # on a weekend the business days of "this week" are already past; a date that is meant to be proposed can
        # never lie before the reference day (seen: a Sunday call proposed the Friday before)
        if found is not None and (found >= d or int(offset_weeks) != 0):
            return found
    return None


def weekday_in_week(name, which, ref):
    """'this <weekday>' = that weekday in ref's calendar week; 'next <weekday>' = that weekday
    in the following calendar week (so 'next Friday' said on a Friday is 7 days later)."""
    ref = to_date(ref)
    idx = weekday_index(name)
    start = week_start(ref)
    if which == "this":
        return start + _dt.timedelta(days=idx)
    if which == "next":
        return start + _dt.timedelta(weeks=1, days=idx)
    raise ValueError("which must be 'this' or 'next'")


def upcoming_weekday(name, ref, include_today=False):
    """The next occurrence of a weekday named without 'this'/'next' (e.g. 'on Friday')."""
    ref = to_date(ref)
    idx = weekday_index(name)
    delta = (idx - ref.weekday()) % 7
    if delta == 0 and not include_today:
        delta = 7
    return ref + _dt.timedelta(days=delta)


def between(x, lo, hi, inclusive=(True, True)):
    a = (x >= lo) if inclusive[0] else (x > lo)
    b = (x <= hi) if inclusive[1] else (x < hi)
    return a and b


def time_in_window(t, start, end, inclusive=(True, True)):
    """t, start, end as 'HH:MM' strings."""
    def m(s):
        h, mi = str(s).strip().split(":")[:2]
        return int(h) * 60 + int(mi)
    return between(m(t), m(start), m(end), inclusive)


def day_label(d):
    """'Friday 16 October' for speech."""
    d = to_date(d)
    return "%s %d %s" % (d.strftime("%A"), d.day, d.strftime("%B"))
