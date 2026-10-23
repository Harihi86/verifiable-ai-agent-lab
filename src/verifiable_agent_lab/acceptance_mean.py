"""Owner-side demonstration oracle, outside the submitted implementation tree."""

import os
import sys
import unittest

sys.path.insert(0, os.environ["VAAL_WORKSPACE"])
from mini_stats import mean  # noqa: E402


class Acceptance(unittest.TestCase):
    def test_ordinary(self):
        self.assertEqual(mean([1, 2, 3]), 2)

    def test_empty_is_rejected(self):
        with self.assertRaises(ValueError):
            mean([])

    def test_negative_and_singleton(self):
        self.assertEqual(mean([-4, 2]), -1)
        self.assertEqual(mean([0]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
