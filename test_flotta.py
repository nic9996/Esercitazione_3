import unittest
from datetime import date, timedelta

from prenotazioni import Flotta, Veicolo, VeicoloNonTrovato, DataNonAmmessa, Noleggio, ORIZZONTE_GIORNI, NoleggioNonTrovato

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

    def test_id_non_progressivi(self):
        # gli id assegnati da prenota sono progressivi e non vengono riutilizzati dopo una cancellazione;
        giorno = date(2026, 11, 20)
        oggi = date(2026, 11, 18)
        flotta = Flotta()
        veicolo = Veicolo("A1", "Furgone", 3)
        flotta.aggiungi_veicolo(veicolo)
        noleggio_a = Noleggio("A1", giorno, "09:00", "12:00", "Giovanni0", 1)
        prima = flotta.prenota(noleggio_a, oggi)
        noleggio_b = Noleggio("A1", giorno, "12:00", "14:00", "Giovanni0", 1)
        seconda = flotta.prenota(noleggio_b, oggi)
        flotta.cancella(prima)
        noleggio_c = Noleggio("A1", giorno, "14:00", "14:30", "Giovanni0", 1)
        terza = flotta.prenota(noleggio_c, oggi)
        self.assertEqual(prima, 1)
        self.assertEqual(seconda, 2)
        self.assertEqual(terza, 3)

    def test_id_inesistente(self):
        # cancella e noleggio sollevano NoleggioNonTrovato per un id inesistente;
        flotta = Flotta()
        with self.assertRaises(NoleggioNonTrovato):
            flotta.noleggio("x")
        with self.assertRaises(NoleggioNonTrovato):
            flotta.cancella("x")

    def test_noleggi_del_giorno(self):
        # noleggi_del_giorno restituisce i noleggi ordinati per orario di inizio e, se indicato il veicolo, 
        # solo quelli del veicolo. I dati vanno scelti in modo che l'ordine per orario sia diverso da quello per codice: altrimenti 
        # il test non distingue i due comportamenti.
        giorno = date(2026, 11, 20)
        oggi = date(2026, 11, 18)
        flotta = Flotta()
        veicolo_a = Veicolo("A1", "Furgone", 3)
        flotta.aggiungi_veicolo(veicolo_a)
        veicolo_b = Veicolo("A2", "Furgone", 3)
        flotta.aggiungi_veicolo(veicolo_b)
        noleggio_b = Noleggio("A2", giorno, "12:00", "14:00", "Giovanni0", 1)  # questo ha id 1
        flotta.prenota(noleggio_b, oggi)
        noleggio_a = Noleggio("A1", giorno, "09:00", "12:00", "Giovanni0", 1)  # questo ha id 2
        flotta.prenota(noleggio_a, oggi)

        tutti = flotta.noleggi_del_giorno(giorno)
        filtrati = flotta.noleggi_del_giorno(giorno, "A1")
        
        self.assertEqual([x.id for x in tutti], [2, 1])  # nella lista di tutti appare prima l'id 2 perchè la lista è ordinata in ordine temporale
        self.assertEqual([x.id for x in filtrati], [2])  # questo si fa per vedere che il filtro funzioni