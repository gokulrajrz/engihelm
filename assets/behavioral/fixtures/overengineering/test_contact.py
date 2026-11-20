import unittest
from contact import contact_display,format_phone
class TestContact(unittest.TestCase):
    def test_display(self): self.assertEqual(contact_display("Mira","415-555-0123"),"Mira: (415) 555-0123")
    def test_validation(self):
        with self.assertRaises(ValueError):format_phone("123")
if __name__=='__main__':unittest.main()
