import unittest
from datetime import date, timedelta

from prenotazioni import Flotta, Veicolo, VeicoloNonTrovato, DataNonAmmessa, Noleggio, ORIZZONTE_GIORNI

class TestFlotta(unittest.TestCase):
    # aggiungi_veicolo rifiuta un codice duplicato con ValueError ; veicolo solleva VeicoloNonTrovato per un codice inesistente;
    def test_veicoli(self):
        flotta = Flotta()
        veicolo_a = Veicolo("A1", "Furgone", 3)
        veicolo_b = Veicolo("A1", "Auto", 5)
        flotta.aggiungi_veicolo(veicolo_a)
        with self.assertRaises(ValueError):
            flotta.aggiungi_veicolo(veicolo_b)
        with self.assertRaises(VeicoloNonTrovato):
            flotta.veicolo("XX")

    def test_date_non_ammesse(self):
        # prenota solleva DataNonAmmessa per una data passata e una data oltre l'orizzonte, e accetta la data di oggi e la data limite 
        # dell'orizzonte, cioè oggi più ORIZZONTE_GIORNI giorni;
        giorno = date(2026, 11, 8)
        oggi = date(2026, 11, 18)
        flotta = Flotta()
        veicolo = Veicolo("A1", "Furgone", 3)
        flotta.aggiungi_veicolo(veicolo)
        noleggio = Noleggio("A1", giorno, "09:00", "12:00", "Giovanni0", 1)
        with self.assertRaises(DataNonAmmessa):
            flotta.prenota(noleggio, oggi=oggi)
        noleggio = Noleggio("A1", oggi + timedelta(days=ORIZZONTE_GIORNI + 1), "09:00", "12:00", "Giovanni0", 1)  # data dell'orizzonte +1 non è ammessa
        with self.assertRaises(DataNonAmmessa):
            flotta.prenota(noleggio, oggi=oggi)
        noleggio = Noleggio("A1", oggi, "09:00", "12:00", "Giovanni0", 1)  # data di oggi è ammessa
        flotta.prenota(noleggio, oggi=oggi)
        noleggio = Noleggio("A1", oggi + timedelta(days=ORIZZONTE_GIORNI), "09:00", "12:00", "Giovanni0", 1)  # data dell'orizzonte è ammessa
        flotta.prenota(noleggio, oggi=oggi)