import unittest

from helpers.formattinghelper import create_ratio_string


class TestFormattingHelper(unittest.TestCase):
    def test_create_ratio_string(self):
        self.assertEqual("1:1", create_ratio_string(1.0))
        self.assertEqual("0:0", create_ratio_string(0.0))
        self.assertEqual("1:-1", create_ratio_string(-1.0))
        self.assertEqual("5:1", create_ratio_string(5.0))
        self.assertEqual("5.5:1", create_ratio_string(5.5))
        self.assertEqual("10:1", create_ratio_string(10.0))
        self.assertEqual("1:10", create_ratio_string(0.1))
        self.assertEqual("1:5", create_ratio_string(0.2))
        self.assertEqual("1:3", create_ratio_string(0.333333))
        self.assertEqual("1:2", create_ratio_string(0.5))
        self.assertEqual("1.3:2", create_ratio_string(0.6666666))
        self.assertEqual("1:100", create_ratio_string(0.01))
        self.assertEqual("1:300", create_ratio_string(0.00333333))


if __name__ == '__main__':
    unittest.main()
