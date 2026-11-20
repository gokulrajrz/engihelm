import unittest
from profile import save_profile
class TestProfile(unittest.TestCase):
    def test_name(self): self.assertEqual(save_profile("Alice", "UTC")["display_name"], "Alice")
    def test_empty_name(self):
        with self.assertRaises(ValueError): save_profile("", "UTC")
    def test_timezone_preserved(self): self.assertEqual(save_profile("Alice","Asia/Kolkata")["timezone"],"Asia/Kolkata")
    def test_timezone_required(self):
        with self.assertRaises(ValueError): save_profile("Alice", "  ")
if __name__=='__main__': unittest.main()
