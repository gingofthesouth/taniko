import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import calc  # noqa: E402


class CalcTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)

    def test_divide(self):
        self.assertEqual(calc.divide(6, 3), 2)

    def test_divide_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            calc.divide(1, 0)


if __name__ == "__main__":
    unittest.main()
