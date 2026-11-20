import unittest
from auth import may_access
class TestAuth(unittest.TestCase):
    def test_active(self): self.assertTrue(may_access({"token_valid":True,"account_status":"active"}))
    def test_disabled(self): self.assertFalse(may_access({"token_valid":True,"account_status":"disabled"}))
    def test_missing_status_fail_closed(self): self.assertFalse(may_access({"token_valid":True}))
    def test_bad_token(self): self.assertFalse(may_access({"token_valid":False,"account_status":"active"}))
if __name__=='__main__':unittest.main()
