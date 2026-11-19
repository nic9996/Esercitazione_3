import unittest
from datetime import date, timedelta
from prenotazioni import Noleggio, GIORNO_CHIUSURA, DataNonAmmessa

class TestNoleggio(unittest.TestCase):
    def test_orari_non_ammessi(self):
        with self.assertRaises(ValueError):
            Noleggio("Furgone1", date(2026, 11, 19), "10:00", "10:00", "Giovanni", 1)

    def test_giorni_non_ammessi(self):
        giorno = (date(2026, 11, 16))  # è un lunedì
        for day in range(7):
            giorno_noleggio = giorno + timedelta(days=day)
            if giorno_noleggio.weekday() == GIORNO_CHIUSURA:
                with self.assertRaises(DataNonAmmessa):
                    Noleggio("Auto", giorno_noleggio, "10:00", "11:00", "Giovanni", 1)
            else:
                Noleggio("Auto", giorno_noleggio, "10:00", "11:00", "Giovanni", 1)