import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.machine import echo_of


class TestEcho(unittest.TestCase):
    def test_cut_message_is_said_back_in_second_person(self):
        self.assertEqual(echo_of("I've been running around all day trying to get"),
                         "...you've been running around all day trying to get...?")
        self.assertEqual(echo_of("My date of birth is the seventeenth of"), "...your date of birth is the seventeenth of...?")

    def test_only_the_last_sentence(self):
        self.assertEqual(echo_of("Yes, this is Tomas Novak. I have had such"), "...you have had such...?")

    def test_a_word_cut_in_the_middle_keeps_its_apostrophe(self):
        self.assertTrue(echo_of("I really can'").endswith("can'...?"))

    def test_finished_message_has_no_echo(self):
        self.assertIsNone(echo_of("I can pay on Friday."))
        self.assertIsNone(echo_of(""))


if __name__ == "__main__":
    unittest.main()
