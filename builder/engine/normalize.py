"""Turn what a customer says into values: amounts, dates, digit strings.

People say "six hundred thirty-seven fifty", "the twenty-second of October", "four four, seven one",
"14/03/88", "Monday the 26th", "next Friday". The model may also already give a clean value.
Every parser returns None when it cannot read the value; it never guesses silently.
Standard library only.
"""
import re
import datetime as _dt

from . import dates as D

_UNITS = {
    "zero": 0, "oh": 0, "o": 0, "nought": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000}
_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20, "thirtieth": 30,
}
MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9,
    "sep": 9, "sept": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_DAYWORDS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun"


def _clean(text):
    t = str(text or "").lower()
    t = t.replace("’", "'").replace("-", " ")
    t = re.sub(r"[^\w\s.,/'$:]", " ", t)
    # sentence punctuation is not part of a word ("the twenty sixth." must end in the token "sixth");
    # a point or comma between digits is (637.50, 4,471, 14.03.1988)
    t = re.sub(r"(?<!\d)[.,]|[.,](?!\d)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- number words

def words_to_int(tokens):
    """['six','hundred','thirty','seven'] -> 637. Returns None if a token is not a number word."""
    total, cur, seen = 0, 0, False
    for w in tokens:
        if w == "and":
            continue
        if w in _UNITS:
            cur += _UNITS[w]; seen = True
        elif w in _TENS:
            cur += _TENS[w]; seen = True
        elif w == "hundred":
            cur = (cur or 1) * 100; seen = True
        elif w in ("thousand", "million"):
            total += (cur or 1) * _SCALES[w]; cur = 0; seen = True
        elif w in _ORDINALS:
            cur += _ORDINALS[w]; seen = True
        elif w.endswith("ieth") and w[:-4] + "y" in _TENS:
            cur += _TENS[w[:-4] + "y"]; seen = True
        else:
            return None
    return total + cur if seen else None


def _is_numword(w):
    return (w in _UNITS or w in _TENS or w in _SCALES or w == "and" or w in _ORDINALS
            or (w.endswith("ieth") and w[:-4] + "y" in _TENS))


# ---------------------------------------------------------------- amounts

def parse_amount(text):
    """'637.50', '$1,250', 'six hundred thirty seven fifty', 'four hundred and fifty-five dollars',
    'twenty one hundred', '637 dollars and 50 cents'. Returns float rounded to 2 decimals or None."""
    t = _clean(text)
    if not t:
        return None
    m = re.search(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?", t)
    if m:
        whole = int(m.group(1).replace(",", ""))
        frac = m.group(2)
        cents = int(frac.ljust(2, "0")) if frac else 0
        rest = t[m.end():]
        mc = re.search(r"(?:and\s+)?(\d{1,2})\s*cents?", rest)
        if not frac and mc:
            cents = int(mc.group(1))
        return round(whole + cents / 100.0, 2)
    toks = [w for w in t.replace(",", " ").split() if w not in ("dollars", "dollar", "bucks", "usd", "euros", "euro", "pounds", "pound")]
    # "X dollars and Y cents" / "X point Y" / "X fifty" (cents spoken after the dollars)
    if "point" in toks:
        i = toks.index("point")
        a = words_to_int([w for w in toks[:i] if _is_numword(w)])
        dec = [w for w in toks[i + 1:] if w in _UNITS]
        if a is not None and dec:
            cents_str = "".join(str(_UNITS[w]) for w in dec)[:2].ljust(2, "0")
            return round(a + int(cents_str) / 100.0, 2)
    if "cents" in toks or "cent" in toks:
        j = toks.index("cents") if "cents" in toks else toks.index("cent")
        left = toks[:j]
        if "and" in left:
            k = len(left) - 1 - left[::-1].index("and")
            a, c = words_to_int([w for w in left[:k] if _is_numword(w)]), words_to_int([w for w in left[k + 1:] if _is_numword(w)])
            if a is not None and c is not None and c < 100:
                return round(a + c / 100.0, 2)
    # the amount is ONE number phrase: the first run of number words (ordinals are days: "two hundred on the fifth")
    runs, cur = [], []
    for w in toks:
        if _is_numword(w) and w not in _ORDINALS and not (w.endswith("ieth") and w[:-4] + "y" in _TENS):
            cur.append(w)
        else:
            if [x for x in cur if x != "and"]:
                runs.append(cur)
            cur = []
    if [x for x in cur if x != "and"]:
        runs.append(cur)
    if not runs:
        return None
    nums = runs[0]
    while nums and nums[0] == "and":
        nums = nums[1:]
    if not any(w in _SCALES for w in nums):
        # spoken without "hundred": "one seventy-three" = 173, "six thirty-seven fifty" = 637.50
        groups, i = [], 0
        while i < len(nums):
            w = nums[i]
            if w == "and":
                i += 1; continue
            if w in _TENS and i + 1 < len(nums) and nums[i + 1] in _UNITS and 0 < _UNITS[nums[i + 1]] < 10:
                groups.append(_TENS[w] + _UNITS[nums[i + 1]]); i += 2
            elif w in _TENS:
                groups.append(_TENS[w]); i += 1
            elif w in _UNITS:
                groups.append(_UNITS[w]); i += 1
            else:
                groups = None; break
        if groups and len(groups) >= 2 and 1 <= groups[0] <= 9 and all(10 <= g <= 99 for g in groups[1:]) and len(groups) <= 3:
            v = groups[0] * 100 + groups[1]
            return round(float(v) + (groups[2] / 100.0 if len(groups) == 3 else 0), 2)
    # "twenty one hundred" = 2100
    if len(nums) >= 2 and nums[-1] == "hundred" and "thousand" not in nums:
        head = words_to_int(nums[:-1])
        if head is not None and head >= 11 and "hundred" not in nums[:-1]:
            return float(head * 100)
    # split trailing cents: "six hundred thirty seven fifty" -> 637 + .50
    v = words_to_int(nums)
    if "hundred" in nums or "thousand" in nums:
        last_scale = max(i for i, w in enumerate(nums) if w in ("hundred", "thousand"))
        tail = nums[last_scale + 1:]
        for cut in range(1, len(tail)):
            a = words_to_int(nums[:last_scale + 1] + tail[:cut])
            c = words_to_int(tail[cut:])
            if a is not None and c is not None and 10 <= c < 100 and tail[cut] in _TENS:
                if words_to_int(tail[:cut]) is not None and words_to_int(tail[:cut]) < 100:
                    return round(a + c / 100.0, 2)
    return float(v) if v is not None else None


# ---------------------------------------------------------------- digits

# Turkish number words (with and without diacritics, as speech-to-text writes them): a code said digit by digit
_TR_DIGITS = {"sifir": 0, "sıfır": 0, "bir": 1, "iki": 2, "uc": 3, "üç": 3, "dort": 4, "dört": 4, "bes": 5, "beş": 5,
              "alti": 6, "altı": 6, "yedi": 7, "sekiz": 8, "dokuz": 9}
_TR_TENS = {"on": 10, "yirmi": 20, "otuz": 30, "kirk": 40, "kırk": 40, "elli": 50, "altmis": 60, "altmış": 60,
            "yetmis": 70, "yetmiş": 70, "seksen": 80, "doksan": 90}


def parse_digits(text, length=None):
    """'four four seven one', '44 71', '4-4-7-1', 'double four seven one' -> '4471'."""
    t = _clean(text)
    out = []
    toks = t.replace(",", " ").replace(".", " ").split()
    i = 0
    while i < len(toks):
        w = toks[i]
        if w in ("double", "triple") and i + 1 < len(toks):
            n = 2 if w == "double" else 3
            nxt = toks[i + 1]
            d = nxt if nxt.isdigit() and len(nxt) == 1 else (str(_UNITS[nxt]) if nxt in _UNITS and _UNITS[nxt] < 10 else None)
            if d is not None:
                out.append(d * n); i += 2; continue
        if w.isdigit():
            out.append(w)
        elif w in _UNITS and _UNITS[w] < 10:
            out.append(str(_UNITS[w]))
        elif w in _TR_DIGITS:
            out.append(str(_TR_DIGITS[w]))
        elif w in _TR_TENS:
            val = _TR_TENS[w]
            if i + 1 < len(toks) and toks[i + 1] in _TR_DIGITS and 0 < _TR_DIGITS[toks[i + 1]] < 10:
                val += _TR_DIGITS[toks[i + 1]]; i += 1
            out.append(str(val))
        elif w in _TENS or (w in _UNITS and _UNITS[w] >= 10):
            val = _TENS.get(w, _UNITS.get(w))
            if w in _TENS and i + 1 < len(toks) and toks[i + 1] in _UNITS and 0 < _UNITS[toks[i + 1]] < 10:
                val += _UNITS[toks[i + 1]]; i += 1
            out.append(str(val))
        i += 1
    s = "".join(out)
    if not s:
        return None
    if length and len(s) > length:
        return None
    return s


# ---------------------------------------------------------------- dates

def _month_in(t):
    for w in re.findall(r"[a-z]+", t):
        if w in MONTHS and not (w == "may" and re.search(r"\bmay\s+(i|we|you|be)\b", t)):
            return MONTHS[w]
    return None


def _year_in(t):
    m = re.search(r"\b(19\d{2}|20\d{2})\b", t)
    if m:
        return int(m.group(1))
    # "nineteen eighty-eight", "two thousand and one"
    toks = t.split()
    for i in range(len(toks)):
        if toks[i] in ("nineteen", "twenty") and i + 1 < len(toks):
            tail = []
            for w in toks[i + 1:i + 3]:
                if w in _TENS or w in _UNITS:
                    tail.append(w)
                else:
                    break
            v = words_to_int(tail) if tail else None
            if v is not None and v < 100 and not (toks[i + 1] in _UNITS and _UNITS[toks[i + 1]] < 10 and len(tail) == 1 and toks[i] == "twenty"):
                return (1900 if toks[i] == "nineteen" else 2000) + v
        if toks[i] == "two" and i + 1 < len(toks) and toks[i + 1] == "thousand":
            tail = [w for w in toks[i + 2:i + 5] if w in _UNITS or w in _TENS or w == "and"]
            v = words_to_int(tail) if [w for w in tail if w != "and"] else 0
            return 2000 + (v or 0)
    return None


def _day_in(t, month_known):
    m = re.search(r"(?<![\d.,])\b(\d{1,2})(?:st|nd|rd|th)\b", t) or (re.search(r"(?<![\d.,])\b(\d{1,2})\b(?![.,]\d)", t) if month_known else None)
    if m:
        v = int(m.group(1))
        if 1 <= v <= 31:
            return v
    toks = t.split()
    for i, w in enumerate(toks):
        if w in _ORDINALS or (w.endswith("ieth") and w[:-4] + "y" in _TENS):
            v = words_to_int(([toks[i - 1]] if i > 0 and toks[i - 1] in _TENS else []) + [w])
            if v and 1 <= v <= 31:
                return v
    if month_known:
        for i, w in enumerate(toks):
            if w in _TENS and i + 1 < len(toks) and toks[i + 1] in _UNITS and 0 < _UNITS[toks[i + 1]] < 10:
                v = _TENS[w] + _UNITS[toks[i + 1]]
                if v <= 31:
                    return v
            if (w in _UNITS and 1 <= _UNITS[w] <= 31) or (w in _TENS and _TENS[w] <= 30):
                if not (i > 0 and toks[i - 1] in ("nineteen", "twenty")):
                    return _UNITS.get(w, _TENS.get(w))
    return None


def _safe_date(y, m, d):
    try:
        return _dt.date(y, m, d)
    except ValueError:
        return None


def _num_tok(w):
    return bool(re.fullmatch(r"\d+(st|nd|rd|th)?", w)) or (w != "and" and _is_numword(w))


def _small(toks):
    """1..99 said as one number: 'seven', 'twenty eight', 'twenty-eighth', '28th', '93'."""
    if len(toks) == 1:
        m = re.fullmatch(r"(\d{1,2})(st|nd|rd|th)?", toks[0])
        if m:
            return int(m.group(1))
        v = words_to_int(toks)
        return v if v is not None and v < 100 and toks[0] not in _SCALES else None
    if len(toks) == 2 and toks[0] in _TENS and (toks[1] in _UNITS or toks[1] in _ORDINALS) and words_to_int(toks[1:]) < 10:
        return _TENS[toks[0]] + words_to_int(toks[1:])
    return None


def _day_of(toks):
    v = _small(toks)
    return v if v is not None and 1 <= v <= 31 else None


def _year_of(toks):
    """'1993', 'nineteen ninety three', 'two thousand and five', 'twenty twelve', two-digit '93' / 'sixty eight'."""
    toks = [w for w in toks if w != "and"] if toks[:2] == ["two", "thousand"] else toks
    if len(toks) == 1 and re.fullmatch(r"(19|20)\d{2}", toks[0]):
        return int(toks[0])
    if toks[:2] == ["two", "thousand"]:
        rest = toks[2:]
        v = _small(rest) if rest else 0
        return 2000 + v if v is not None and v < 100 else None
    if len(toks) >= 2 and toks[0] in ("nineteen", "twenty"):
        v = _small(toks[1:])
        if v is not None and v >= 10:
            return (1900 if toks[0] == "nineteen" else 2000) + v
        if toks[1:] in (["hundred"],):
            return 1900 if toks[0] == "nineteen" else 2000
        if len(toks) == 3 and toks[1] in ("oh", "o", "zero") and toks[2] in _UNITS and _UNITS[toks[2]] < 10:
            return (1900 if toks[0] == "nineteen" else 2000) + _UNITS[toks[2]]
        return None
    v = _small(toks)
    # a two-digit year is said as two digits ("sixty eight", "93", "05"); a lone "one" is not a year ("Twenty-one
    # August" is a day and a month, not the 20th of August 2001 -- seen on Freya: a wrong answer sent to the bank)
    two_digit = v is not None and (v >= 10 or (len(toks) == 1 and re.fullmatch(r"\d{2}", toks[0])))
    if two_digit and len(toks) <= 2 and not re.fullmatch(r"\d+(st|nd|rd|th)", toks[0]) and toks[-1] not in _ORDINALS:
        return v + (1900 if v > 30 else 2000)
    return None


def _spoken_date(t):
    """Day + month word + year in any spoken order. Returns (y, m, d) or None."""
    toks = [w for w in re.split(r"[\s,.]+", t) if w and w not in ("the", "of", "on", "in", "born", "year")]
    mi = next((i for i, w in enumerate(toks) if w in MONTHS and not (w == "may" and i + 1 < len(toks) and toks[i + 1] in ("i", "we", "you", "be"))), None)
    if mi is None:
        return None
    left = []
    for w in reversed(toks[:mi]):
        if _num_tok(w) or w == "and":
            left.insert(0, w)
        else:
            break
    right = []
    for w in toks[mi + 1:]:
        if _num_tok(w) or w in ("and", "oh", "o", "zero"):
            right.append(w)
        else:
            break
    mon = MONTHS[toks[mi]]
    if left and right:
        d, y = _day_of(left), _year_of(right)
        return (y, mon, d) if d and y else None
    if right and not left and _year_of(right) and right[0] in ("nineteen", "twenty", "two") :
        return None   # "March, nineteen eighty-eight": a whole year, no day (not 19 March '88)
    if right:
        for k in range(1, len(right)):
            d, y = _day_of(right[:k]), _year_of(right[k:])
            if d and y:
                return (y, mon, d)
    if left:   # 'twenty eight nineteen ninety three of april' is rare; '28 1993 april' too
        for k in range(1, len(left)):
            d, y = _day_of(left[:k]), _year_of(left[k:])
            if d and y:
                return (y, mon, d)
    return None


def _spoken_numeric_date(text):
    """'twelve, oh-five, seventy-five' / 'oh one, oh eight, ninety-one' / 'twelve oh five seventy five' -> '12/05/75':
    a date said only in numbers, each number in words (customers say codes and dates digit by digit). Three groups
    separated by commas or slashes, or six / eight digits in a row. None if it is not that."""
    raw = str(text or "")
    parts = [p for p in re.split(r"\s*[,/]\s*|\s+-\s+", raw) if p.strip()]
    if len(parts) == 3:
        ds = [parse_digits(p) for p in parts]
        if all(ds) and all(1 <= len(x) <= 4 for x in ds) and len(ds[2]) in (2, 4):
            return "%s/%s/%s" % tuple(ds)
    d = parse_digits(raw)
    if d and len(d) in (6, 8):
        return "%s/%s/%s" % (d[:2], d[2:4], d[4:])
    return None


def parse_birth_date(text, numeric_order="DMY"):
    """A full date with year: '14 March 1988', 'March 14th, 1988', '14/03/1988', '1988-03-14',
    'fourteenth of march nineteen eighty eight'. Numeric-only dates are read in numeric_order
    (the brief says which; e.g. 'day, then month, then year' = DMY). Returns ISO string or None."""
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", str(text or ""))
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return d.isoformat() if d else None
    t = _clean(text)
    num = _spoken_numeric_date(text) if not _month_in(t) else None
    if num:      # a date said only in numbers, in words: "twelve, oh-five, seventy-five" = 12/05/75
        t = num
    m = re.search(r"\b(\d{1,2})[/. ](\d{1,2})[/. ](\d{2,4})\b", t)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 1900 if y > 30 else 2000
        day, mon = (a, b) if numeric_order.upper().startswith("D") else (b, a)
        d = _safe_date(y, mon, day)
        return d.isoformat() if d else None
    sp = _spoken_date(t)
    if sp:
        d = _safe_date(*sp)
        if d:
            return d.isoformat()
    mon = _month_in(t)
    y = _year_in(t)
    if mon and y:
        t_no_year = re.sub(r"\b(19|20)\d{2}\b", " ", t)
        t_no_year = re.sub(r"\b(nineteen|twenty)\s+(\w+)(\s+(one|two|three|four|five|six|seven|eight|nine))?\b(?!\s+of)", lambda mm: " " if (mm.group(2) in _TENS or mm.group(2) in _UNITS) else mm.group(0), t_no_year)
        day = _day_in(t_no_year, True)
        if day:
            d = _safe_date(y, mon, day)
            return d.isoformat() if d else None
    return None


_VAGUE = re.compile(r"\b(next week|end of (the )?month|end of (the )?week|when (my )?(salary|pay|paycheck|wages)|week after next|"
                    r"in a few days|soon|later|sometime|next month|payday|pay day|beginning of|middle of|mid month|"
                    r"in a couple of weeks|in two weeks|couple of weeks|few weeks)\b")


def is_vague_period(text):
    """'next week', 'the week after next', 'when my salary comes': a period, not a day."""
    return bool(_VAGUE.search(_clean(text)))


def resolve_weekday(name, which, today, conv=None):
    """A weekday word resolved under the spec's own convention (IR calendar.weekday_words):
    this: 'calendar_week' (the one in today's Mon-Sun week, default) | 'upcoming' (first such day after today);
    next: 'following_calendar_week' (default) | 'this_plus_7' (seven days after 'this');
    bare (no this/next): 'upcoming' (default) | 'this' (same as 'this')."""
    conv = conv or {}
    if which is None:
        if conv.get("bare") == "this":
            which = "this"
        else:
            return D.upcoming_weekday(name, today, include_today=False)
    if which in ("this", "coming"):
        if conv.get("this") == "upcoming" or which == "coming":
            return D.upcoming_weekday(name, today, include_today=False)
        return D.weekday_in_week(name, "this", today)
    if conv.get("next") == "this_plus_7":
        return resolve_weekday(name, "this", today, conv) + _dt.timedelta(days=7)
    return D.weekday_in_week(name, "next", today)


def parse_calendar_date(text, now, numeric_order="DMY", weekday_words=None):
    """A payment/callback date relative to the call's 'now' (never the real clock).
    Returns {'date': ISO or None, 'kind': ..., 'vague': bool}.
    kind: absolute | relative | weekday_this | weekday_next | weekday_bare | vague | none."""
    t = _clean(text)
    today = D.to_date(now)
    if not t:
        return {"date": None, "kind": "none", "vague": False}
    # "I can't pay that today" / "not today": a negated today is not a date
    t = re.sub(r"\b(not|no|can't|cant|cannot|won't|wont|unable to|couldn't|isn't|don't|dont|do not)\b([^.;!?]*?)\b(today|right now)\b", r"\1\2 ", t)
    # a day under negation is not the day: "not the 25th, the 20th", "I can't do Friday, how about Monday" (the
    # negated phrase runs to the next comma/conjunction); kept only if nothing else is left
    t_neg = re.sub(r"\b(not|no|can't|cant|cannot|won't|wont|couldn't|isn't)\b( (do|make|manage|pay))?( (it|that))?( on)?( the)?"
                   r"\s+[^,;.!?]*?(?=,|;|\bbut\b|\bhow about\b|\bwhat about\b|\binstead\b|$)", " ", t)
    if t_neg.strip() and t_neg != t and re.search(r"\d|" + _DAYWORDS + "|" + "|".join(_ORDINALS) + r"|tomorrow|today", t_neg):
        t = t_neg
    # "now" alone is not a day ("Now that I think of it", "I don't know right now"): only "pay (it) now" / "right now"
    t = re.sub(r"\bnow\b(?! that)", "now", t)
    if re.search(r"\b(today|right now|(pay|do|make)( it| that)? now|tonight|later today|this (morning|afternoon|evening))\b", t) \
            and not re.search(r"\bfrom (today|now)\b", t):
        return {"date": today.isoformat(), "kind": "relative", "vague": False}
    # fixed-meaning relative expressions (no spec convention involved)
    if re.search(r"\b(?:a|one) week from (?:today|now)\b|\bin a week(?:'s time)?\b", t):
        return {"date": (today + _dt.timedelta(days=7)).isoformat(), "kind": "relative", "vague": False}
    m_rel = re.search(r"\bin (\d{1,2}|" + "|".join(k for k in _UNITS if 1 < _UNITS[k] < 20) + r") days?\b", t)
    if m_rel:
        n = int(m_rel.group(1)) if m_rel.group(1).isdigit() else _UNITS[m_rel.group(1)]
        return {"date": (today + _dt.timedelta(days=n)).isoformat(), "kind": "relative", "vague": False}
    wd_rel = re.search(r"\b(" + _DAYWORDS + r")\b", t)
    if wd_rel and re.search(r"\bweek after next\b", t):
        d = D.weekday_in_week(wd_rel.group(1), "next", today) + _dt.timedelta(days=7)
        return {"date": d.isoformat(), "kind": "relative", "vague": False}
    if wd_rel and re.search(r"\bnext week\b", t):
        # "Friday next week" / "next week on Friday": that weekday in the following calendar week, in any convention
        return {"date": D.weekday_in_week(wd_rel.group(1), "next", today).isoformat(), "kind": "relative", "vague": False}
    if re.search(r"\bnext month\b", t):
        dn = _day_in(re.sub(r"\bnext month\b", " ", t), False)
        if dn:
            ny, nmo = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
            d = _safe_date(ny, nmo, dn)
            if d:
                return {"date": d.isoformat(), "kind": "absolute", "vague": False}
    if re.search(r"\bday after tomorrow\b", t):
        return {"date": (today + _dt.timedelta(days=2)).isoformat(), "kind": "relative", "vague": False}
    if re.search(r"\btomorrow\b", t):
        return {"date": (today + _dt.timedelta(days=1)).isoformat(), "kind": "relative", "vague": False}
    m = re.search(r"\b(this|next|coming)?\s*(" + _DAYWORDS + r")\b", t)
    explicit_month = _month_in(t)
    has_day_number = bool(re.search(r"(?<![\d.,])\b\d{1,2}(st|nd|rd|th)?\b(?![.,]\d)", t)) or any(w in _ORDINALS for w in t.split())
    if m and not (explicit_month or has_day_number):
        which = m.group(1)
        d = resolve_weekday(m.group(2), which, today, weekday_words)
        return {"date": d.isoformat(), "kind": "weekday_" + (which or "bare"), "vague": False}
    if is_vague_period(t):
        return {"date": None, "kind": "vague", "vague": True}
    # ISO / numeric
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", str(text or ""))
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return {"date": d.isoformat() if d else None, "kind": "absolute", "vague": False}
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        if y < 100:
            y += 2000
        day, mon = (a, b) if numeric_order.upper().startswith("D") else (b, a)
        d = _safe_date(y, mon, day)
        if d and not m.group(3) and d < today:
            d = _safe_date(y + 1, mon, day)
        return {"date": d.isoformat() if d else None, "kind": "absolute", "vague": False}
    mon = explicit_month
    day = _day_in(t, bool(mon))
    if day:
        y = _year_in(t) or today.year
        if mon:
            d = _safe_date(y, mon, day)
            if d and not _year_in(t) and d < today:
                d = _safe_date(y + 1, mon, day)
        else:
            d = _safe_date(today.year, today.month, day)
            if d is None or d < today:
                nm = today.month % 12 + 1
                ny = today.year + (1 if today.month == 12 else 0)
                d = _safe_date(ny, nm, day)
            wdm = re.search(r"\b(" + _DAYWORDS + r")\b", t)
            if wdm and d is not None:
                # "Thursday the 19th": the weekday tells which month is meant: the first such date from today on
                want = D.upcoming_weekday(wdm.group(1), today, include_today=True).weekday()
                y2, m2 = today.year, today.month
                for _ in range(3):      # only the next couple of months: a far month means the weekday was a slip
                    c = _safe_date(y2, m2, day)
                    if c and c >= today and c.weekday() == want:
                        d = c
                        break
                    m2 += 1
                    if m2 > 12:
                        y2, m2 = y2 + 1, 1
        return {"date": d.isoformat() if d else None, "kind": "absolute", "vague": False}
    return {"date": None, "kind": "none", "vague": False}


def parse_time(text):
    """'eleven', '11', '11am', 'around eleven', '3pm', '15:30', 'half past two' -> 'HH:MM' or None.
    Bare hours 1-7 are read as afternoon (business context)."""
    t = _clean(text)
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ap = (m.group(3) or "").replace(".", "")
    else:
        m = re.search(r"\b(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.|o'?clock)?\b", t)
        if m:
            h, mi, ap = int(m.group(1)), 0, (m.group(2) or "").replace(".", "")
        else:
            half = re.search(r"\bhalf past (\w+)", t)
            words = [w for w in t.split() if w in _UNITS or w in _TENS]
            if half and half.group(1) in _UNITS:
                h, mi, ap = _UNITS[half.group(1)], 30, ""
            elif words:
                h = words_to_int(words[:1]); mi = 0; ap = ""
                if len(words) > 1:
                    rest = words_to_int(words[1:])
                    if rest is not None and rest < 60:
                        mi = rest
                if h is None:
                    return None
            else:
                if "noon" in t or "midday" in t:
                    return "12:00"
                return None
            if re.search(r"\b(pm|afternoon|evening)\b", t):
                ap = "pm"
            elif re.search(r"\b(am|morning)\b", t):
                ap = "am"
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if not ap and 1 <= h <= 7:
        h += 12
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return "%02d:%02d" % (h, mi)


# ---------------------------------------------------------------- self-corrections: the last stated value wins
# "the 21st, sorry, I mean the 20th" / "three hundred, sorry, two fifty" / "Traffic was awful today. I can pay Friday."
_CORRECTION = re.compile(r"\bsorry\b|\bi mean\b|\bactually\b|\bwait\b|\bmake it\b|\brather\b|\bcorrection\b|\bno\b,?|\bbut\b|\binstead\b|[.;!?](?=\s)", re.I)


def _last_wins(fn, ok):
    def wrapped(text, *a, **k):
        s = str(text or "")
        for m in reversed(list(_CORRECTION.finditer(s))):
            tail = s[m.end():]
            if tail.strip():
                v = fn(tail, *a, **k)
                if ok(v):
                    return v
        return fn(s, *a, **k)
    wrapped.__doc__ = fn.__doc__
    return wrapped


parse_amount = _last_wins(parse_amount, lambda v: v is not None)
_parse_birth_date_words = parse_birth_date


def _parse_birth_date_itn(text, numeric_order="DMY"):
    v = _parse_birth_date_words(text, numeric_order)
    if v is None:
        w = itn(text)
        if w != _clean(text):
            v = _parse_birth_date_words(w, numeric_order)
    return v


parse_birth_date = _last_wins(_parse_birth_date_itn, lambda v: v is not None)
parse_time = _last_wins(parse_time, lambda v: v is not None)
parse_calendar_date = _last_wins(parse_calendar_date, lambda v: bool(v) and (v.get("date") is not None or v.get("vague")))


# ---------------------------------------------------------------- evidence: which numbers did the customer say?

def numbers_said(text):
    """Every number the words of a message can stand for: digit tokens and every run of number words (each sub-run
    too: 'nineteen eighty one' -> 19, 80, 81, 1, 1981, ...), ordinals, years, and the message's amount reading.
    Used to check that a value the language model wrote is grounded in what was said (it may invent a month or a
    year nobody said)."""
    t = _clean(text)
    out = set()
    for m in re.finditer(r"\d+(?:[.,]\d+)?", t):
        try:
            out.add(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    toks = t.split()
    for i in range(len(toks)):
        for j in range(i + 1, min(len(toks), i + 6) + 1):
            run = toks[i:j]
            if not all(_is_numword(w) for w in run) or run[0] == "and":
                break
            v = words_to_int(run)
            if v is not None:
                out.add(float(v))
            y = _year_of(run)
            if y:
                out.add(float(y))
    for m in re.finditer(r"\b(\d{1,2})(st|nd|rd|th)\b", t):
        out.add(float(m.group(1)))
    y = _year_in(t)
    if y:
        out.add(float(y))
    a = parse_amount(text)
    if a is not None:
        out.add(float(a))
    w = itn(text)
    if w != _clean(text):
        for m in re.finditer(r"\d+", w):
            out.add(float(m.group(0)))
    return out


def month_said(text):
    return _month_in(_clean(text))


# ---------------------------------------------------------------- inverse text normalisation (spoken -> written)
_DIGIT_WORDS = {"zero": "0", "oh": "0", "o": "0", "nought": "0", "one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"}


def itn(text):
    """Spoken numbers to written ones, as speech systems do before reading values: 'one nine eight four' -> 1984,
    'nineteen eighty-four' -> 1984, 'the twenty sixth' -> the 26th, 'four hundred and fifty' -> 450. Words that are not
    numbers are kept. Used as a second reading when a parser cannot read the words as they are."""
    toks = _clean(text).split()
    out, i = [], 0
    while i < len(toks):
        w = toks[i]
        # a run of single digits said one by one (years, codes): two or more digit words in a row
        j = i
        while j < len(toks) and toks[j] in _DIGIT_WORDS:
            j += 1
        if j - i >= 2 and not (toks[i] in ("o", "oh") and j - i == 2 and i > 0 and toks[i - 1] in ("nineteen", "twenty")):
            out.append("".join(_DIGIT_WORDS[t] for t in toks[i:j]))
            i = j
            continue
        # a year said as two numbers: 'nineteen eighty four', 'twenty twelve', 'two thousand and five'
        done = False
        for k in (4, 3, 2):
            if i + k <= len(toks) and toks[i] in ("nineteen", "twenty", "two"):
                y = _year_of(toks[i:i + k])
                if y and (k > 2 or toks[i] != "twenty" or toks[i + 1] in _TENS or toks[i + 1] in ("ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")):
                    out.append(str(y)); i += k; done = True
                    break
        if done:
            continue
        # an ordinal ('thirtieth', 'twenty sixth') -> 30th, 26th
        if i + 1 < len(toks) and toks[i] in _TENS and toks[i + 1] in _ORDINALS and _ORDINALS[toks[i + 1]] < 10:
            out.append("%dth" % (_TENS[toks[i]] + _ORDINALS[toks[i + 1]])); i += 2
            continue
        if w in _ORDINALS or (w.endswith("ieth") and w[:-4] + "y" in _TENS):
            out.append("%dth" % words_to_int([w])); i += 1
            continue
        # a cardinal number made of several words
        j = i
        while j < len(toks) and _is_numword(toks[j]) and toks[j] not in _ORDINALS:
            j += 1
        while j > i and toks[j - 1] == "and":
            j -= 1
        if j > i and toks[i] != "and":
            v = words_to_int(toks[i:j])
            if v is not None:
                out.append(str(v)); i = j
                continue
        out.append(w); i += 1
    return " ".join(out)
