import unittest
from main import (
    print_hi,
    print_good_morning,
    print_good_evening,
    print_motivational_quote,
)
from io import StringIO
from contextlib import redirect_stdout

class TestGreetings(unittest.TestCase):
    def test_print_hi(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_hi("Jasper")
        self.assertEqual(buffer.getvalue().strip(), "Hi, Jasper")

    def test_print_good_morning(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_good_morning("Jasper")
        self.assertEqual(buffer.getvalue().strip(), "Good morning, Jasper")

    def test_print_good_evening(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_good_evening("Jasper")
        self.assertEqual(buffer.getvalue().strip(), "Good evening, Jasper")

    def test_motivational_quote(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            print_motivational_quote()
        self.assertEqual(
            buffer.getvalue().strip(),
            "All our dreams can come true, if we have the courage to pursue them",
        )

if __name__ == "__main__":
    unittest.main()