import unittest
from datetime import date
from prenotazioni import Noleggio

class TestNoleggio(unittest.TestCase):
    def test_orari_non_ammessi(self):
        with self.assertRaises(ValueError):
            Noleggio("Furgone1", date(2026, 11, 19), "10:00", "10:00", "Giovanni", 1)
