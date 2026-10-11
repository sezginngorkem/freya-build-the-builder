"""B1 stress test: metamorphic round trip of the value readers. Random values are said in many spoken forms (digits,
words, digit-by-digit, ordinals, fillers, no punctuation, self-correction, split in two turns) and must read back to
the same value. Deterministic seed. Every failing form is a class to fix with a general rule, not a case.

    python sim/stress_normalize.py [--n 300]
"""
import argparse, collections, datetime as dt, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import normalize as N
from sim.styles import words, say_amount, say_date, ordinal, year_words

MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
DIG = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def dob_forms(d):
    y, m, day = d.year, d.month, d.day
    yw = year_words(y)
    ydig = " ".join(DIG[int(c)] for c in str(y))
    return {
        "digits": "%d %s %d" % (day, MON[m - 1], y),
        "us_order": "%s %d, %d" % (MON[m - 1], day, y),
        "words": "%s %s %s" % (words(day), MON[m - 1], yw),
        "ordinal": "the %s of %s %s" % (ordinal(day), MON[m - 1], yw),
        "year_digit_by_digit": "the %s of %s %s" % (ordinal(day), MON[m - 1], ydig),
        "filler": "um the %s of uh %s %s" % (ordinal(day), MON[m - 1], yw),
        "no_punct_lower": ("my date of birth is the %s of %s %s" % (ordinal(day), MON[m - 1], yw)).lower(),
        "correction": "the %s of %s, sorry, the %s of %s %s" % (ordinal(day % 28 + 1), MON[m - 1], ordinal(day), MON[m - 1], yw),
        "numeric_dmy": "%02d/%02d/%d" % (day, m, y),
        "two_turns": ("the %s of %s..." % (ordinal(day), MON[m - 1]), "%s." % yw),
    }


def amount_forms(a):
    whole, cents = int(a), int(round((a - int(a)) * 100))
    f = {"digits": "%.2f" % a if cents else "%d" % whole,
         "words": say_amount(a),
         "filler": "uh " + say_amount(a),
         "with_currency": ("$%.2f" % a) if cents else "$%d" % whole,
         "in_sentence": "I can pay %s on Friday" % say_amount(a),
         "correction": "%s, sorry, %s" % (say_amount(a + 10), say_amount(a))}
    if 100 <= whole < 1000 and not cents and whole % 100 >= 10:
        f["colloquial"] = "%s %s" % (words(whole // 100), words(whole % 100)) if whole % 100 else words(whole // 100) + " hundred"
    return f


def date_forms(d, now):
    wd = d.strftime("%A")
    return {"ordinal": "the %s" % ordinal(d.day), "digit_th": "the %d%s" % (d.day, "th" if 11 <= d.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")),
            "month_day": "%s %s" % (MON[d.month - 1], ordinal(d.day)), "day_of_month": "the %s of %s" % (ordinal(d.day), MON[d.month - 1]),
            "weekday_ordinal": "%s the %s" % (wd, ordinal(d.day)), "numeric": "%d/%d" % (d.day, d.month),
            "filler": "uh the %s of %s I think" % (ordinal(d.day), MON[d.month - 1]),
            "correction": "the %s, sorry, I mean the %s" % (ordinal((d.day % 27) + 1), ordinal(d.day)),
            "sentence_no_punct": ("i can pay on %s the %s" % (wd, ordinal(d.day))).lower()}


def relative_forms(now):
    """Relative expressions whose meaning does not depend on a spec convention."""
    t = dt.date.fromisoformat(now[:10])
    monday_next = t - dt.timedelta(days=t.weekday()) + dt.timedelta(days=7)
    out = {}
    for i, wd in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]):
        nd = monday_next + dt.timedelta(days=i)
        out["weekday_next_week:" + wd] = ("%s next week" % wd, nd)
        out["next_week_weekday:" + wd] = ("next week on %s" % wd, nd)
        out["weekday_of_next_week:" + wd] = ("%s of next week" % wd, nd)
    out["week_from_today"] = ("a week from today", t + dt.timedelta(days=7))
    out["in_three_days"] = ("in three days", t + dt.timedelta(days=3))
    out["in_5_days"] = ("in 5 days", t + dt.timedelta(days=5))
    nm = (t.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    out["day_of_next_month"] = ("the 23rd of next month", nm.replace(day=23))
    return out


def time_forms(h, m):
    h12 = h - 12 if h > 12 else h
    ampm = "pm" if h >= 12 else "am"
    f = {"digits": "%d:%02d" % (h, m), "ampm": "%d%s" % (h12, ampm) if m == 0 else "%d:%02d %s" % (h12, m, ampm),
         "words_morning": ("%s in the %s" % (words(h12), "morning" if h < 12 else "afternoon")) if m == 0 else None,
         "half_past": ("half past %s %s" % (words(h12), "in the morning" if h < 12 else "in the afternoon")) if m == 30 else None,
         "oclock": ("%s o'clock %s" % (words(h12), "in the morning" if h < 12 else "in the afternoon")) if m == 0 else None}
    return {k: v for k, v in f.items() if v}


def digit_forms(ds):
    pairs = [ds[i:i + 2] for i in range(0, len(ds), 2)]
    f = {"one_by_one": " ".join(DIG[int(c)] for c in ds), "commas": ", ".join(DIG[int(c)] for c in ds), "digits": ds,
         "oh_for_zero": " ".join("oh" if c == "0" else DIG[int(c)] for c in ds)}
    if all(p[0] != "0" for p in pairs) and len(ds) == 4:
        f["pairs"] = " ".join(words(int(p)) for p in pairs)
    dbl = []
    i = 0
    while i < len(ds):
        if i + 1 < len(ds) and ds[i] == ds[i + 1]:
            dbl.append("double " + DIG[int(ds[i])]); i += 2
        else:
            dbl.append(DIG[int(ds[i])]); i += 1
    if any(x.startswith("double") for x in dbl):
        f["double"] = " ".join(dbl)
    return f


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=300)
    a = ap.parse_args()
    rnd = random.Random(20261011)
    ok, bad, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    for _ in range(a.n):
        d = dt.date(1940, 1, 1) + dt.timedelta(days=rnd.randrange(0, 365 * 65))
        for k, s in dob_forms(d).items():
            got = N.parse_birth_date(" ".join(s)) if isinstance(s, tuple) else N.parse_birth_date(s)
            key = "dob:" + k
            (ok if got == d.isoformat() else bad)[key] += 1
            if got != d.isoformat() and len(ex[key]) < 3:
                ex[key].append((s, got, d.isoformat()))
        amt = rnd.choice([rnd.randrange(10, 3000), round(rnd.uniform(10, 3000), 2)])
        for k, s in amount_forms(amt).items():
            got = N.parse_amount(s)
            key = "amount:" + k
            good = got is not None and abs(got - amt) < 0.005
            (ok if good else bad)[key] += 1
            if not good and len(ex[key]) < 3:
                ex[key].append((s, got, amt))
    now = "2026-10-14T11:00"
    base = dt.date(2026, 10, 15)
    for _ in range(a.n):
        d = base + dt.timedelta(days=rnd.randrange(0, 40))
        nxt = N.parse_calendar_date("the %s" % ordinal(d.day), now).get("date")
        for k, f in date_forms(d, now).items():
            if k in ("ordinal", "digit_th", "correction") and nxt != d.isoformat():
                continue      # without a month or weekday the next such day is the right reading
            got = N.parse_calendar_date(f, now).get("date"); key = "date:" + k
            (ok if got == d.isoformat() else bad)[key] += 1
            if got != d.isoformat() and len(ex[key]) < 3:
                ex[key].append((f, got, d.isoformat()))
        h, m = rnd.randrange(9, 19), rnd.choice([0, 0, 30, 15])
        for k, f in time_forms(h, m).items():
            got = N.parse_time(f); key = "time:" + k
            (ok if got == "%02d:%02d" % (h, m) else bad)[key] += 1
            if got != "%02d:%02d" % (h, m) and len(ex[key]) < 3:
                ex[key].append((f, got, "%02d:%02d" % (h, m)))
        ds = "".join(str(rnd.randrange(10)) for _ in range(4))
        for k, f in digit_forms(ds).items():
            got = N.parse_digits(f); key = "digits:" + k
            (ok if got == ds else bad)[key] += 1
            if got != ds and len(ex[key]) < 3:
                ex[key].append((f, got, ds))
    for now2 in ("2026-10-14T11:00", "2026-11-20T16:00", "2026-12-28T10:00"):
        for k, (f, d) in relative_forms(now2).items():
            got = N.parse_calendar_date(f, now2).get("date"); key = "rel:" + k.split(":")[0]
            (ok if got == d.isoformat() else bad)[key] += 1
            if got != d.isoformat() and len(ex[key]) < 3:
                ex[key].append((f, now2[:10], got, d.isoformat()))
    neg = [("Not the 25th, the 20th", "2026-10-20"), ("not on the 25th but on the 20th", "2026-10-20"),
           ("I can't do Friday, how about Monday", "2026-10-19"), ("not Friday, Monday", "2026-10-19"),
           ("I don't know right now, maybe Friday", "2026-10-16"), ("Now that I think of it, Friday works", "2026-10-16"),
           ("Friday, not Monday", "2026-10-16"), ("I can pay now", "2026-10-14"), ("today", "2026-10-14")]
    for f, want in neg:
        got = N.parse_calendar_date(f, "2026-10-14T11:00").get("date"); key = "date:negation_and_now"
        (ok if got == want else bad)[key] += 1
        if got != want and len(ex[key]) < 4:
            ex[key].append((f, got, want))
    for wd_day in [("Monday", 20), ("Tuesday", 20)]:
        got = N.parse_calendar_date("%s the %dth" % wd_day, "2026-10-14T11:00").get("date"); key = "date:weekday_conflict"
        good = got is not None and got < "2027-01-01"
        (ok if good else bad)[key] += 1
        if not good: ex[key].append(("%s the %dth" % wd_day, got))
    for key in sorted(set(ok) | set(bad)):
        n = ok[key] + bad[key]
        print("%-28s %5.1f%%  (%d/%d)%s" % (key, 100.0 * ok[key] / n, ok[key], n, "" if not bad[key] else "   e.g. %r" % (ex[key][0],)))


if __name__ == "__main__":
    main()
