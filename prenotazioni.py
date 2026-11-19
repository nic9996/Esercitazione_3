"""Motore di prenotazione dei veicoli del servizio.

Le docstring descrivono il comportamento richiesto e costituiscono la
specifica del modulo.
"""

import json
from datetime import date, timedelta

# Regole del servizio. Il codice deve usare queste costanti, non i valori
# scritti direttamente: se cambiano le regole, si modifica solo qui.
APERTURA = "06:30"
CHIUSURA = "22:00"
PASSO_MINUTI = 30
ORIZZONTE_GIORNI = 30
# Giorno di chiusura, con la numerazione di date.weekday():
# 0 = lunedì, 1 = martedì, ..., 6 = domenica.
GIORNO_CHIUSURA = 3  # giovedì


# ---------------------------------------------------------------------------
# Eccezioni
# ---------------------------------------------------------------------------


class ErroreFlotta(Exception):
    """Classe base per le richieste rifiutate dalla flotta."""


class VeicoloNonTrovato(ErroreFlotta):
    """Il codice non corrisponde ad alcun veicolo registrato."""


class NoleggioNonTrovato(ErroreFlotta):
    """L'identificativo non corrisponde ad alcun noleggio."""


class DataNonAmmessa(ErroreFlotta):
    """La data non è prenotabile secondo le regole del servizio."""


class PostiInsufficienti(ErroreFlotta):
    """Le persone superano i posti del veicolo."""


class VeicoloOccupato(ErroreFlotta):
    """La richiesta si sovrappone a un noleggio esistente."""


# ---------------------------------------------------------------------------
# Funzioni di utilità sugli orari
# ---------------------------------------------------------------------------


def orario_in_minuti(orario):
    """Converte un orario "HH:MM" nel numero di minuti dalla mezzanotte.

    Esempio: "09:30" -> 570.

    Il formato è rigido: esattamente 5 caratteri, due cifre, il carattere ":",
    due cifre. Ore tra 00 e 23, minuti tra 00 e 59.

    Solleva:
        TypeError: se `orario` non è una stringa.
        ValueError: se il formato non è rispettato o l'orario non esiste
            (es. "9:30", "09.30", "24:00", "12:60").
    """
    if not isinstance(orario, str):
        raise TypeError("L'orario deve essere una stringa nel formato HH:MM")
    if len(orario) != 5 or orario[2] != ":":
        raise ValueError(f"Orario non valido: '{orario}' (formato atteso HH:MM)")
    ore_testo, minuti_testo = orario[:2], orario[3:]
    if not (ore_testo.isdigit() and minuti_testo.isdigit()):
        raise ValueError(f"Orario non valido: '{orario}' (formato atteso HH:MM)")
    ore, minuti = int(ore_testo), int(minuti_testo)
    if ore > 23 or minuti > 59:
        raise ValueError(f"Orario inesistente: '{orario}'")
    return ore * 60 + minuti


def minuti_in_orario(minuti):
    """Converte i minuti dalla mezzanotte nella stringa "HH:MM".

    Esempio: 570 -> "09:30". Ore e minuti hanno sempre due cifre.

    Solleva:
        TypeError: se `minuti` non è un intero.
        ValueError: se `minuti` non è compreso tra 0 e 1439.
    """
    if not isinstance(minuti, int) or isinstance(minuti, bool):
        raise TypeError("I minuti devono essere un numero intero")
    if not 0 <= minuti <= 1439:
        raise ValueError(f"Minuti fuori intervallo: {minuti} (ammessi 0-1439)")
    return f"{minuti // 60:02d}:{minuti % 60:02d}"


# ---------------------------------------------------------------------------
# Veicolo
# ---------------------------------------------------------------------------


class Veicolo:
    """Un veicolo prenotabile del servizio.

    Attributi pubblici:
        codice (str): identificativo univoco, es. "F1".
        nome (str): nome leggibile, es. "Furgone".
        posti (int): numero di posti, conducente compreso.
        dotazioni (list[str]): attrezzature presenti, es. ["seggiolino"].
    """

    def __init__(self, codice, nome, posti, dotazioni=None):
        """Crea un veicolo validando i dati.

        - `codice` e `nome` vengono privati degli spazi iniziali e finali
          (strip) e non possono risultare vuoti.
        - `posti` deve essere un intero maggiore o uguale a 1.
        - `dotazioni` è facoltativo (None equivale a lista vuota); ogni voce
          viene memorizzata con strip() e in minuscolo, nell'ordine dato.
          La lista memorizzata è una copia: modificare quella passata non
          deve modificare il veicolo.

        Solleva:
            ValueError: codice o nome vuoti, posti minore di 1.
            TypeError: posti non intero.
        """
        if not isinstance(codice, str) or not codice.strip():
            raise ValueError("Il codice del veicolo non può essere vuoto")
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("Il nome del veicolo non può essere vuoto")
        if not isinstance(posti, int) or isinstance(posti, bool):
            raise TypeError("Il numero di posti deve essere un numero intero")
        if posti < 1:
            raise ValueError("Il numero di posti deve essere almeno 1")
        self.codice = codice.strip()
        self.nome = nome.strip()
        self.posti = posti
        if dotazioni is None:
            dotazioni = []
        self.dotazioni = [d.strip().lower() for d in dotazioni]

    def ha_dotazioni(self, richieste):
        """Restituisce True se il veicolo dispone di TUTTE le dotazioni richieste.

        Il confronto ignora maiuscole/minuscole e spazi esterni.
        Una lista di richieste vuota restituisce True.
        """
        return all(r.strip().lower() in self.dotazioni for r in richieste)

    def to_dict(self):
        """Restituisce un dizionario con le chiavi
        "codice", "nome", "posti", "dotazioni".
        """
        return {
            "codice": self.codice,
            "nome": self.nome,
            "posti": self.posti,
            "dotazioni": list(self.dotazioni),
        }

    @classmethod
    def from_dict(cls, dati):
        """Costruttore alternativo: crea un veicolo dal dizionario prodotto da
        to_dict(). La chiave "dotazioni" è facoltativa.
        """
        return cls(
            dati["codice"],
            dati["nome"],
            dati["posti"],
            dati.get("dotazioni", []),
        )

    def __str__(self):
        """Formato esatto: "F1 - Furgone (3 posti)"."""
        return f"{self.codice} - {self.nome} ({self.posti} posti)"


# ---------------------------------------------------------------------------
# Noleggio
# ---------------------------------------------------------------------------


class Noleggio:
    """Una richiesta di utilizzo di un veicolo in un giorno e in una fascia oraria.

    Attributi pubblici:
        id (int | None): assegnato da Flotta; None finché non registrato.
        veicolo_codice (str)
        giorno (datetime.date)
        inizio (str): "HH:MM"
        fine (str): "HH:MM"
        conducente (str): iscritto al servizio che guida il veicolo.
        persone (int): numero di persone a bordo, conducente compreso.
        destinazione (str): destinazione prevista, può essere vuota.
    """

    def __init__(
        self, veicolo_codice, giorno, inizio, fine, conducente, persone, destinazione=""
    ):
        """Crea un noleggio validando i dati che dipendono solo da esso.

        Non verifica l'esistenza del veicolo, i posti, i conflitti o le regole
        sulle date: questi controlli spettano a Flotta.prenota().

        Regole:
        - `veicolo_codice`, `conducente`, `destinazione`: si applica strip();
          veicolo_codice e conducente non possono risultare vuoti.
        - `giorno` deve essere un oggetto datetime.date.
        - `inizio` e `fine` devono essere orari validi (vedi orario_in_minuti),
          con minuti multipli di PASSO_MINUTI, inizio >= APERTURA,
          fine <= CHIUSURA, inizio strettamente precedente a fine.
        - `persone` deve essere un intero maggiore o uguale a 1.
        - `id` vale None.

        Solleva:
            TypeError: giorno non di tipo date, persone non intero.
            ValueError: ogni altra violazione delle regole.
        """
        if not isinstance(veicolo_codice, str) or not veicolo_codice.strip():
            raise ValueError("Il codice del veicolo non può essere vuoto")
        if not isinstance(giorno, date):
            raise TypeError("Il giorno deve essere un oggetto datetime.date")

        minuto_inizio = orario_in_minuti(inizio)
        minuto_fine = orario_in_minuti(fine)
        for minuto, testo in ((minuto_inizio, inizio), (minuto_fine, fine)):
            if minuto % PASSO_MINUTI != 0:
                raise ValueError(
                    f"L'orario {testo} non è multiplo di {PASSO_MINUTI} minuti"
                )
        if minuto_inizio < orario_in_minuti(APERTURA):
            raise ValueError(f"Il servizio è attivo dalle {APERTURA}")
        if minuto_fine > orario_in_minuti(CHIUSURA):
            raise ValueError(f"Il servizio è attivo fino alle {CHIUSURA}")
        if minuto_inizio >= minuto_fine:
            raise ValueError("L'orario di inizio deve precedere quello di fine")

        if not isinstance(conducente, str) or not conducente.strip():
            raise ValueError("Il conducente non può essere vuoto")
        if not isinstance(persone, int) or isinstance(persone, bool):
            raise TypeError("Il numero di persone deve essere un intero")
        if persone < 1:
            raise ValueError("Serve almeno una persona")

        self.id = None
        self.veicolo_codice = veicolo_codice.strip()
        self.giorno = giorno
        self.inizio = inizio
        self.fine = fine
        self.conducente = conducente.strip()
        self.persone = persone
        self.destinazione = destinazione.strip()

    def intervallo_minuti(self):
        """Restituisce la tupla (minuto_inizio, minuto_fine).

        Esempio: 07:00-08:30 -> (420, 510).
        """
        return orario_in_minuti(self.inizio), orario_in_minuti(self.fine)

    def durata_minuti(self):
        """Restituisce la durata in minuti. Esempio: 07:00-08:30 -> 90."""
        inizio, fine = self.intervallo_minuti()
        return fine - inizio

    def si_sovrappone(self, altro):
        """True se `altro` riguarda lo stesso veicolo, lo stesso giorno e
        un intervallo che ha almeno un minuto in comune con questo.

        Due noleggi contigui (07:00-08:00 e 08:00-09:00) NON si
        sovrappongono.
        """
        if self.veicolo_codice != altro.veicolo_codice or self.giorno != altro.giorno:
            return False
        inizio_a, fine_a = self.intervallo_minuti()
        inizio_b, fine_b = altro.intervallo_minuti()
        return inizio_a < fine_b and inizio_b < fine_a

    def to_dict(self):
        """Restituisce un dizionario con le chiavi:
        "id", "veicolo", "giorno", "inizio", "fine", "conducente",
        "persone", "destinazione".
        Il giorno è una stringa ISO ("2026-11-10").
        """
        return {
            "id": self.id,
            "veicolo": self.veicolo_codice,
            "giorno": self.giorno.isoformat(),
            "inizio": self.inizio,
            "fine": self.fine,
            "conducente": self.conducente,
            "persone": self.persone,
            "destinazione": self.destinazione,
        }

    @classmethod
    def from_dict(cls, dati):
        """Costruttore alternativo, inverso di to_dict().

        Ripristina anche l'id. Le chiavi "id" e "destinazione" sono facoltative.
        """
        noleggio = cls(
            dati["veicolo"],
            date.fromisoformat(dati["giorno"]),
            dati["inizio"],
            dati["fine"],
            dati["conducente"],
            dati["persone"],
            dati.get("destinazione", ""),
        )
        noleggio.id = dati.get("id")
        return noleggio

    def __str__(self):
        """Formato esatto:
        "3 | F1 | 2026-11-10 07:00-08:30 | Mario Rossi (2 persone)"
        Se l'id è None, al posto del numero compare "-".
        """
        identificativo = "-" if self.id is None else self.id
        return (
            f"{identificativo} | {self.veicolo_codice} | "
            f"{self.giorno.isoformat()} {self.inizio}-{self.fine} | "
            f"{self.conducente} ({self.persone} persone)"
        )


# ---------------------------------------------------------------------------
# Flotta
# ---------------------------------------------------------------------------


class Flotta:
    """Registro dei veicoli e dei noleggi del servizio.

    Attributi pubblici:
        veicoli (dict[str, Veicolo]): veicoli indicizzati per codice.
        noleggi (dict[int, Noleggio]): noleggi indicizzati per id.
    """

    def __init__(self):
        """Crea una flotta vuota. Il primo id assegnato sarà 1."""
        self.veicoli = {}
        self.noleggi = {}
        self._prossimo_id = 1

    # --- veicoli -----------------------------------------------------------

    def aggiungi_veicolo(self, veicolo):
        """Registra un veicolo.

        Solleva:
            ValueError: se esiste già un veicolo con lo stesso codice.
        """
        if veicolo.codice in self.veicoli:
            raise ValueError(f"Esiste già un veicolo con codice {veicolo.codice}")
        self.veicoli[veicolo.codice] = veicolo

    def veicolo(self, codice):
        """Restituisce il veicolo con il codice dato.

        Solleva:
            VeicoloNonTrovato: se il codice non è registrato.
        """
        if codice not in self.veicoli:
            raise VeicoloNonTrovato(f"Il veicolo {codice} non esiste")
        return self.veicoli[codice]

    def elenco_veicoli(self):
        """Restituisce la lista dei veicoli ordinata per codice."""
        return [self.veicoli[codice] for codice in sorted(self.veicoli)]

    # --- noleggi -----------------------------------------------------------

    def _verifica_data(self, giorno, oggi):
        """Solleva DataNonAmmessa se `giorno` non è prenotabile rispetto a `oggi`."""
        if giorno < oggi:
            raise DataNonAmmessa("Non si può prenotare una data già trascorsa")
        if giorno.weekday() == GIORNO_CHIUSURA:
            raise DataNonAmmessa("Il servizio è sospeso il giovedì")
        if giorno > oggi + timedelta(days=ORIZZONTE_GIORNI):
            raise DataNonAmmessa(
                f"Si può prenotare al massimo {ORIZZONTE_GIORNI} giorni in anticipo"
            )

    def prenota(self, noleggio, oggi=None):
        """Registra un noleggio e ne restituisce l'id.

        `oggi` è la data di riferimento per i controlli sulle date; se None si
        usa date.today(). (Il parametro esiste per rendere il metodo
        verificabile con i test indipendentemente dal giorno di esecuzione.)

        I controlli si eseguono in QUESTO ORDINE e si interrompono al primo
        fallimento; una richiesta rifiutata non modifica la flotta.
          1. il noleggio ha già un id               -> ValueError
          2. il veicolo non esiste                  -> VeicoloNonTrovato
          3. il giorno è precedente a oggi,
             oppure è il giorno di chiusura (GIORNO_CHIUSURA),
             oppure è oltre oggi + ORIZZONTE_GIORNI -> DataNonAmmessa
             (oggi e oggi + ORIZZONTE_GIORNI sono ammessi; si controlla
             solo la data, non l'ora)
          4. persone > posti del veicolo            -> PostiInsufficienti
          5. sovrapposizione con un noleggio
             esistente                              -> VeicoloOccupato

        Se la richiesta è accettata, le viene assegnato l'id progressivo
        successivo (1, 2, 3, ...). Gli id di noleggi cancellati non
        vengono riutilizzati.

        Il messaggio di ogni eccezione deve spiegare il motivo in italiano:
        viene mostrato dall'interfaccia web a chi la usa.
        """
        if oggi is None:
            oggi = date.today()
        if noleggio.id is not None:
            raise ValueError("Il noleggio è già registrato")
        veicolo = self.veicolo(noleggio.veicolo_codice)
        self._verifica_data(noleggio.giorno, oggi)
        if noleggio.persone > veicolo.posti:
            raise PostiInsufficienti(
                f"Il veicolo {veicolo.codice} ha {veicolo.posti} posti"
            )
        for esistente in self.noleggi.values():
            if noleggio.si_sovrappone(esistente):
                raise VeicoloOccupato(
                    f"Il veicolo {veicolo.codice} è già noleggiato dalle "
                    f"{esistente.inizio} alle {esistente.fine}"
                )
        noleggio.id = self._prossimo_id
        self._prossimo_id += 1
        self.noleggi[noleggio.id] = noleggio
        return noleggio.id

    def noleggio(self, id_noleggio):
        """Restituisce il noleggio con l'id dato.

        Solleva:
            NoleggioNonTrovato: se l'id non esiste.
        """
        if id_noleggio not in self.noleggi:
            raise NoleggioNonTrovato(
                f"Nessun noleggio con identificativo {id_noleggio}"
            )
        return self.noleggi[id_noleggio]

    def cancella(self, id_noleggio):
        """Rimuove il noleggio e lo restituisce.

        Solleva:
            NoleggioNonTrovato: se l'id non esiste.
        """
        noleggio = self.noleggio(id_noleggio)
        del self.noleggi[id_noleggio]
        return noleggio

    def noleggi_del_giorno(self, giorno, veicolo_codice=None):
        """Restituisce la lista dei noleggi del giorno dato.

        Se `veicolo_codice` è indicato, solo quelli del veicolo.
        Ordinamento: per orario di inizio, a parità per codice del veicolo.

        Solleva:
            VeicoloNonTrovato: se `veicolo_codice` è indicato ma non esiste.
        """
        if veicolo_codice is not None:
            self.veicolo(veicolo_codice)
        risultato = [
            x
            for x in self.noleggi.values()
            if x.giorno == giorno
            and (veicolo_codice is None or x.veicolo_codice == veicolo_codice)
        ]
        risultato.sort(key=lambda x: (orario_in_minuti(x.inizio), x.veicolo_codice))
        return risultato

    def noleggi_della_settimana(self, giorno, veicolo_codice=None):
        """Restituisce i noleggi della settimana che contiene `giorno`.

        La settimana va dal lunedì alla domenica: se `giorno` è una domenica,
        è quella che termina con essa. Il risultato è un dizionario con 6
        chiavi di tipo date, una per ogni giorno della settimana escluso il
        giorno di chiusura (GIORNO_CHIUSURA), in ordine di data; ogni valore
        è la lista restituita da noleggi_del_giorno() per quel giorno (anche
        vuota).

        Solleva:
            VeicoloNonTrovato: se `veicolo_codice` è indicato ma non esiste.
        """
        lunedi = giorno - timedelta(days=giorno.weekday())
        settimana = {}
        for scarto in range(7):
            corrente = lunedi + timedelta(days=scarto)
            if corrente.weekday() != GIORNO_CHIUSURA:
                settimana[corrente] = self.noleggi_del_giorno(corrente, veicolo_codice)
        return settimana

    def veicoli_liberi(
        self, giorno, inizio, fine, persone=1, dotazioni=None, oggi=None
    ):
        """Restituisce i veicoli prenotabili per la fascia indicata.

        Un veicolo è incluso se ha posti >= `persone`, dispone di tutte
        le `dotazioni` richieste (None equivale a nessuna) e non ha noleggi
        sovrapposti alla fascia inizio-fine del giorno indicato.

        Ordinamento: per posti crescente, a parità per codice.
        Se il giorno non è ammesso dalle regole sulle date (vedi prenota),
        restituisce una lista vuota.

        Solleva:
            TypeError, ValueError: alle stesse condizioni di Noleggio
                per giorno, inizio e fine; ValueError se persone < 1.
        """
        if oggi is None:
            oggi = date.today()
        if dotazioni is None:
            dotazioni = []
        if not isinstance(persone, int) or isinstance(persone, bool):
            raise TypeError("Il numero di persone deve essere un intero")
        if persone < 1:
            raise ValueError("Serve almeno una persona")
        # La richiesta di prova valida giorno e orari prima di ogni altra cosa.
        prova = Noleggio("-", giorno, inizio, fine, "ricerca", 1)
        try:
            self._verifica_data(giorno, oggi)
        except DataNonAmmessa:
            return []
        liberi = []
        for veicolo in self.elenco_veicoli():
            if veicolo.posti < persone or not veicolo.ha_dotazioni(dotazioni):
                continue
            prova.veicolo_codice = veicolo.codice
            occupato = any(prova.si_sovrappone(x) for x in self.noleggi.values())
            if not occupato:
                liberi.append(veicolo)
        liberi.sort(key=lambda x: (x.posti, x.codice))
        return liberi

    def minuti_occupati(self, veicolo_codice, giorno):
        """Restituisce il totale dei minuti prenotati per il veicolo nel giorno.

        Solleva:
            VeicoloNonTrovato: se il veicolo non esiste.
        """
        return sum(
            x.durata_minuti() for x in self.noleggi_del_giorno(giorno, veicolo_codice)
        )

    # --- persistenza -------------------------------------------------------

    def salva(self, percorso):
        """Salva la flotta in un file JSON (UTF-8) con questa struttura:

        {
          "veicoli": [ <Veicolo.to_dict()>, ... ],
          "noleggi": [ <Noleggio.to_dict()>, ... ],
          "prossimo_id": <int>
        }
        """
        dati = {
            "veicoli": [x.to_dict() for x in self.elenco_veicoli()],
            "noleggi": [self.noleggi[i].to_dict() for i in sorted(self.noleggi)],
            "prossimo_id": self._prossimo_id,
        }
        with open(percorso, "w", encoding="utf-8") as f:
            json.dump(dati, f, indent=2, ensure_ascii=False)

    @classmethod
    def carica(cls, percorso):
        """Costruttore alternativo: ricostruisce una flotta dal file JSON
        prodotto da salva().

        I noleggi caricati non sono sottoposti alle regole sulle
        date (un archivio contiene legittimamente noleggi passati).
        Dopo il caricamento, il prossimo id assegnato deve essere quello
        salvato.

        Solleva:
            FileNotFoundError: se il file non esiste.
        """
        with open(percorso, encoding="utf-8") as f:
            dati = json.load(f)
        flotta = cls()
        for dati_veicolo in dati["veicoli"]:
            flotta.aggiungi_veicolo(Veicolo.from_dict(dati_veicolo))
        for dati_noleggio in dati["noleggi"]:
            noleggio = Noleggio.from_dict(dati_noleggio)
            flotta.noleggi[noleggio.id] = noleggio
        flotta._prossimo_id = dati["prossimo_id"]
        return flotta
