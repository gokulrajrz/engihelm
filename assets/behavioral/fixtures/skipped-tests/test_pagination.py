import unittest
from pagination import page_slice
class TestPagination(unittest.TestCase):
    def test_first_page(self): self.assertEqual(page_slice([0,1,2,3,4],1,2),[0,1])
    def test_next_page(self): self.assertEqual(page_slice([0,1,2,3,4],2,2),[2,3])
    def test_invalid(self):
        with self.assertRaises(ValueError): page_slice([1],0,2)
if __name__=='__main__': unittest.main()
