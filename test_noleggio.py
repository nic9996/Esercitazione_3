import unittest
from datetime import date, timedelta
from prenotazioni import Noleggio, GIORNO_CHIUSURA, DataNonAmmessa, Flotta, Veicolo

class TestNoleggio(unittest.TestCase):
    def test_orari_non_ammessi(self):
        with self.assertRaises(ValueError):
            Noleggio("Furgone1", date(2026, 11, 19), "10:00", "10:00", "Giovanni", 1)

        # il costruttore solleva ValueError per orari non ammessi: inizio non multiplo di 30 minuti, inizio prima dell'apertura, fine dopo la chiusura, fine precedente all'inizio;
        orari_non_ammessi = [
            ("7:15", "08:00"),
            ("4:00", "12:00"),
            ("12:00", "23:00"),
            ("12:00", "11:00")
        ]
        for inizio, fine in orari_non_ammessi:
            with self.assertRaises(ValueError):
                Noleggio("F1", date(2026, 11, 18), inizio, fine, "Giovanni", 1)

    def test_giorni_non_ammessi(self):
        giorno = (date(2026, 11, 16))  # è un lunedì
        for day in range(7):
            giorno_noleggio = giorno + timedelta(days=day)
            veicolo = Veicolo("Auto", "ttt", 5)
            noleggio = Noleggio("Auto", giorno_noleggio, "10:00", "11:00", "Giovanni", 1)
            flotta = Flotta()
            flotta.aggiungi_veicolo(veicolo)
            if giorno_noleggio.weekday() == GIORNO_CHIUSURA:
                with self.assertRaises(DataNonAmmessa):
                    flotta.prenota(noleggio, giorno)
            else:
                flotta.prenota(noleggio, giorno)

    def test_giorno_non_data(self):
        with self.assertRaises(TypeError):
            Noleggio("F1", "2026-11-18", "07:00", "08:00", "Giovanni", 1)

    def test_durata_minuti(self):
        noleggio = Noleggio("A", date(2026, 11, 18), "09:00", "12:30", "Giovanni", 1)
        self.assertEqual(noleggio.durata_minuti(), 210)  # durata in minuti 210

    def test_si_sovrappone(self):
        # si_sovrappone restituisce False per veicoli diversi e per giorni diversi, True per un intervallo contenuto in un altro
        noleggio_a = Noleggio("A", date(2026, 11, 18), "09:00", "12:30", "Giovanni", 1)
        noleggio_b = Noleggio("B", date(2026, 11, 18), "09:00", "12:30", "Giovanni", 1)
        self.assertFalse(noleggio_a.si_sovrappone(noleggio_b))
        noleggio_c = Noleggio("A", date(2026, 11, 17), "09:00", "12:30", "Giovanni", 1)
        self.assertFalse(noleggio_a.si_sovrappone(noleggio_c))
        noleggio_d = Noleggio("A", date(2026, 11, 18), "10:00", "11:30", "Giovanni", 1)
        self.assertTrue(noleggio_a.si_sovrappone(noleggio_d))