import unittest

from prenotazioni import Flotta, Veicolo, VeicoloNonTrovato

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