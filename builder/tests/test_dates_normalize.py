"""Calendar and parsing tests. Expected values come from the practice cases (public-test-set.json)
and the brief's own worked examples; the calendar under test is a fixture, not engine code."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import dates as D
from engine import normalize as N

CAL = {"workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
       "holidays": ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]}
NOW = "2026-10-14T11:00"   # a Wednesday


class Calendar(unittest.TestCase):
    def test_deadlines_from_cases(self):
        self.assertEqual(D.iso(D.add_business_days(NOW, 7, CAL)), "2026-10-23")    # PUB-04, PUB-13 late band
        self.assertEqual(D.iso(D.add_business_days(NOW, 12, CAL)), "2026-11-02")   # early band skips the 26th
        self.assertEqual(D.iso(D.add_business_days(NOW, 0, CAL)), "2026-10-14")

    def test_holiday_next_business_day(self):
        self.assertFalse(D.is_business_day("2026-10-26", CAL))
        self.assertEqual(D.iso(D.next_business_day("2026-10-26", CAL)), "2026-10-27")   # PUB-07
        self.assertEqual(D.iso(D.next_business_day("2026-10-17", CAL)), "2026-10-19")   # Saturday

    def test_last_business_day_of_week(self):
        self.assertEqual(D.iso(D.last_business_day_of_week(NOW, 0, CAL)), "2026-10-16")  # PUB-06, PUB-10
        self.assertEqual(D.iso(D.last_business_day_of_week("2026-10-16", 1, CAL)), "2026-10-23")

    def test_this_next_weekday(self):
        self.assertEqual(D.iso(D.weekday_in_week("Friday", "this", NOW)), "2026-10-16")
        self.assertEqual(D.iso(D.weekday_in_week("Friday", "next", NOW)), "2026-10-23")
        # brief: "next Friday" said on a Friday is the Friday of the following week
        self.assertEqual(D.iso(D.weekday_in_week("Friday", "next", "2026-10-16")), "2026-10-23")

    def test_callback_window(self):
        self.assertTrue(D.time_in_window("10:00", "10:00", "19:00"))
        self.assertTrue(D.time_in_window("19:00", "10:00", "19:00"))
        self.assertFalse(D.time_in_window("19:01", "10:00", "19:00"))

    def test_label(self):
        self.assertEqual(D.day_label("2026-10-16"), "Friday 16 October")


class Amounts(unittest.TestCase):
    def test_digits(self):
        for s, v in [("637.50", 637.5), ("$1,250", 1250.0), ("2125.10", 2125.1), ("it's 420 dollars", 420.0)]:
            self.assertEqual(N.parse_amount(s), v, s)

    def test_words(self):
        for s, v in [("six hundred thirty seven fifty", 637.5),
                     ("four hundred and fifty-five", 455.0),
                     ("twenty one hundred", 2100.0),
                     ("six hundred thirty-seven dollars and fifty cents", 637.5),
                     ("one thousand two hundred fifty", 1250.0),
                     ("three hundred sixty-five", 365.0),
                     ("seventy five", 75.0),
                     ("five hundred", 500.0)]:
            self.assertEqual(N.parse_amount(s), v, s)

    def test_none(self):
        self.assertIsNone(N.parse_amount("I can't pay"))


class Digits(unittest.TestCase):
    def test_digits(self):
        for s, v in [("4471", "4471"), ("four four seven one", "4471"), ("44 71", "4471"),
                     ("4-4-7-1", "4471"), ("double four seven one", "4471"), ("oh three five eight", "0358"),
                     ("forty four seventy one", "4471")]:
            self.assertEqual(N.parse_digits(s, 4), v, s)


class BirthDates(unittest.TestCase):
    def test_forms(self):
        for s, v in [("14 March 1988", "1988-03-14"), ("March 14th, 1988", "1988-03-14"),
                     ("14/03/1988", "1988-03-14"), ("1988-03-14", "1988-03-14"),
                     ("the fourteenth of March nineteen eighty-eight", "1988-03-14"),
                     ("12 July 1991", "1991-07-12"), ("21 August 1992", "1992-08-21"),
                     ("second of November 1979", "1979-11-02"),
                     ("03/14/1988", None)]:   # DMY reading: month 14 does not exist
            self.assertEqual(N.parse_birth_date(s, "DMY"), v, s)

    def test_spoken_compound_days_and_years(self):
        # seen on Freya: "Twenty-eight April nineteen ninety-three" looped forever (day read as part of the year)
        for text, iso in [("Twenty-eight April nineteen ninety-three", "1993-04-28"), ("twenty eight April 1993", "1993-04-28"),
                          ("28th April 93", "1993-04-28"), ("April twenty eight nineteen ninety three", "1993-04-28"),
                          ("December eleventh, eighty-three", "1983-12-11"), ("April twenty-first, sixty-eight", "1968-04-21"),
                          ("the 3rd of May two thousand and one", "2001-05-03"), ("seven July nineteen oh five", "1905-07-07"),
                          ("I was born on the twelfth of June, 1979", "1979-06-12"), ("thirty first of september 1990", None)]:
            self.assertEqual(N.parse_birth_date(text, "DMY"), iso, text)

    def test_self_corrections_last_value_wins(self):
        # simulated customer styles 'corrects' and 'talkative' (kit tools/run_cases.py STYLES)
        now = "2026-10-14T11:00"
        for text, iso in [("the 21st, sorry, I mean the 20th", "2026-10-20"), ("Friday, no wait, Thursday", "2026-10-15"),
                          ("my cousin's wedding is on the 30th, but I can pay on the 22nd", "2026-10-22"),
                          ("Traffic was awful today. I can pay Friday.", "2026-10-16"), ("I can pay Friday but only half", "2026-10-16")]:
            self.assertEqual(N.parse_calendar_date(text, now, "DMY")["date"], iso, text)
        self.assertEqual(N.parse_amount("three hundred, sorry, I mean two hundred and fifty"), 250.0)
        self.assertEqual(N.parse_amount("I can pay 300 but only on Friday"), 300.0)
        self.assertEqual(N.parse_birth_date("March 14th, no sorry, March 15th 1988", "DMY"), "1988-03-15")

    def test_mdy_order(self):
        self.assertEqual(N.parse_birth_date("03/14/1988", "MDY"), "1988-03-14")


class CalendarDates(unittest.TestCase):
    def d(self, s):
        return N.parse_calendar_date(s, NOW)

    def test_relative(self):
        self.assertEqual(self.d("today")["date"], "2026-10-14")
        self.assertEqual(self.d("tomorrow")["date"], "2026-10-15")
        self.assertEqual(self.d("this Friday")["date"], "2026-10-16")
        self.assertEqual(self.d("next Friday")["date"], "2026-10-23")
        self.assertEqual(self.d("on Friday")["date"], "2026-10-16")

    def test_absolute(self):
        self.assertEqual(self.d("6 November")["date"], "2026-11-06")          # PUB-04
        self.assertEqual(self.d("Monday the 26th")["date"], "2026-10-26")     # PUB-07
        self.assertEqual(self.d("the twenty-second of October")["date"], "2026-10-22")
        self.assertEqual(self.d("30 October")["date"], "2026-10-30")          # PUB-13
        self.assertEqual(self.d("the 30th")["date"], "2026-10-30")

    def test_vague(self):
        for s in ["the week after next", "next week", "end of the month", "when my salary comes"]:
            self.assertTrue(self.d(s)["vague"], s)


class Times(unittest.TestCase):
    def test_times(self):
        for s, v in [("around eleven", "11:00"), ("11am", "11:00"), ("3pm", "15:00"), ("15:30", "15:30"),
                     ("tomorrow morning around eleven", "11:00"), ("half past two", "14:30")]:
            self.assertEqual(N.parse_time(s), v, s)


if __name__ == "__main__":
    unittest.main()


class TestBirthDateNoYear(unittest.TestCase):
    def test_compound_day_without_year_is_not_a_date(self):
        # Freya PUB-03 pieces: "Twenty-one August." was read as 2001-08-20 and sent to the bank as an answer
        for t in ("Twenty-one August.", "twenty one July", "Thirty-one May", "the twenty-second of March"):
            self.assertIsNone(N.parse_birth_date(t), t)
        self.assertEqual(N.parse_birth_date("Twenty-one August nineteen ninety two"), "1992-08-21")
        self.assertEqual(N.parse_birth_date("twelfth of july ninety one"), "1991-07-12")
        self.assertEqual(N.parse_birth_date("July 12 05"), "2005-07-12")


class TestBirthDateSpokenNumbers(unittest.TestCase):
    """A date of birth said only in numbers, in words (seen on Freya: 'twelve, oh-five, seventy-five' was not read)."""
    def test_month_first(self):
        from engine import normalize as N
        self.assertEqual(N.parse_birth_date("twelve, oh-five, seventy-five", "MDY"), "1975-12-05")
        self.assertEqual(N.parse_birth_date("oh-eight, eleven, eighty-one", "MDY"), "1981-08-11")
        self.assertEqual(N.parse_birth_date("twelve oh five seventy five", "MDY"), "1975-12-05")

    def test_day_first_and_words_unchanged(self):
        from engine import normalize as N
        self.assertEqual(N.parse_birth_date("twelve, oh-five, seventy-five", "DMY"), "1975-05-12")
        self.assertEqual(N.parse_birth_date("14 March 1988", "DMY"), "1988-03-14")
        self.assertIsNone(N.parse_birth_date("4471", "DMY"))
