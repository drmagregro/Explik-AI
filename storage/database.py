"""Accès à la base SQLite du coach : le seul fichier qui écrit des requêtes SQL."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config

SCHEMA = Path(__file__).with_name("schema.sql")


class BaseDeDonnees:
    """Lit et écrit les données durables du coach (profil, cours, séances, scores)."""

    def __init__(self, chemin: Path | None = None):
        self.chemin = Path(chemin or config.DB_PATH)
        self.chemin.parent.mkdir(parents=True, exist_ok=True)  # crée data/ si besoin
        self.initialiser()

    # --- Outils internes ---------------------------------------------------

    @contextmanager
    def _connexion(self):
        """Ouvre une connexion, valide les changements, puis la referme."""
        con = sqlite3.connect(self.chemin)
        con.row_factory = sqlite3.Row            # lignes lisibles par nom de colonne
        con.execute("PRAGMA foreign_keys = ON")  # SQLite ne vérifie pas les liens sans ça
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _lire(self, requete: str, params: tuple = ()) -> list[dict]:
        with self._connexion() as con:
            return [dict(ligne) for ligne in con.execute(requete, params)]

    def _lire_un(self, requete: str, params: tuple = ()) -> dict | None:
        lignes = self._lire(requete, params)
        return lignes[0] if lignes else None

    def _ecrire(self, requete: str, params: tuple = ()) -> int:
        """Exécute une écriture et renvoie l'identifiant de la ligne créée."""
        with self._connexion() as con:
            return con.execute(requete, params).lastrowid

    def initialiser(self) -> None:
        """Crée les tables si elles n'existent pas encore."""
        with self._connexion() as con:
            con.executescript(SCHEMA.read_text(encoding="utf-8"))

    # --- Profil ------------------------------------------------------------

    def obtenir_profil(self) -> dict | None:
        return self._lire_un("SELECT * FROM profil WHERE id = 1")

    def enregistrer_profil(self, prenom: str, objectif: str, niveau_actuel: str,
                           niveau_vise: str, echeance: str, minutes_par_jour: int,
                           difficultes: str = "") -> None:
        """Crée le profil, ou le remplace s'il existe déjà."""
        self._ecrire(
            """INSERT INTO profil (id, prenom, objectif, niveau_actuel, niveau_vise,
                                   echeance, minutes_par_jour, difficultes)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   prenom = excluded.prenom, objectif = excluded.objectif,
                   niveau_actuel = excluded.niveau_actuel, niveau_vise = excluded.niveau_vise,
                   echeance = excluded.echeance, minutes_par_jour = excluded.minutes_par_jour,
                   difficultes = excluded.difficultes""",
            (prenom, objectif, niveau_actuel, niveau_vise, echeance, minutes_par_jour, difficultes),
        )

    # --- Matières, chapitres, notions --------------------------------------

    def ajouter_matiere(self, nom: str) -> int:
        return self._ecrire("INSERT INTO matieres (nom) VALUES (?)", (nom,))

    def lister_matieres(self) -> list[dict]:
        return self._lire("SELECT * FROM matieres ORDER BY nom")

    def ajouter_chapitre(self, matiere_id: int, titre: str, texte: str = "",
                         difficulte: int = 3, ordre: int = 0) -> int:
        return self._ecrire(
            "INSERT INTO chapitres (matiere_id, titre, texte, difficulte, ordre) VALUES (?, ?, ?, ?, ?)",
            (matiere_id, titre, texte, difficulte, ordre),
        )

    def lister_chapitres(self, matiere_id: int | None = None) -> list[dict]:
        if matiere_id is None:
            return self._lire("SELECT * FROM chapitres ORDER BY matiere_id, ordre")
        return self._lire(
            "SELECT * FROM chapitres WHERE matiere_id = ? ORDER BY ordre", (matiere_id,)
        )

    def obtenir_chapitre(self, chapitre_id: int) -> dict | None:
        return self._lire_un("SELECT * FROM chapitres WHERE id = ?", (chapitre_id,))

    def ajouter_notion(self, chapitre_id: int, nom: str) -> int:
        return self._ecrire(
            "INSERT INTO notions (chapitre_id, nom) VALUES (?, ?)", (chapitre_id, nom)
        )

    def lister_notions(self, chapitre_id: int) -> list[dict]:
        return self._lire("SELECT * FROM notions WHERE chapitre_id = ? ORDER BY nom", (chapitre_id,))

    # --- Contenus (fiches, flashcards) -----------------------------------------

    def ajouter_contenu(self, chapitre_id: int, type: str, titre: str, contenu: str,
                        reponse: str | None = None, notion_id: int | None = None) -> int:
        return self._ecrire(
            "INSERT INTO contenus (chapitre_id, notion_id, type, titre, contenu, reponse) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chapitre_id, notion_id, type, titre, contenu, reponse),
        )

    def lister_contenus(self, chapitre_id: int, type: str | None = None) -> list[dict]:
        """Contenus d'un chapitre, le plus récent en premier."""
        if type is None:
            return self._lire("SELECT * FROM contenus WHERE chapitre_id = ? ORDER BY id DESC",
                              (chapitre_id,))
        return self._lire("SELECT * FROM contenus WHERE chapitre_id = ? AND type = ? ORDER BY id DESC",
                          (chapitre_id, type))

    # --- Objectifs ---------------------------------------------------------

    def ajouter_objectif(self, intitule: str, date_limite: str | None = None,
                         priorite: str = "moyenne", indicateur: str | None = None,
                         seuil_reussite: float | None = None, chapitre_id: int | None = None,
                         matiere_id: int | None = None, difficulte: int | None = None) -> int:
        return self._ecrire(
            """INSERT INTO objectifs (intitule, date_limite, priorite, indicateur,
                                      seuil_reussite, chapitre_id, matiere_id, difficulte)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (intitule, date_limite, priorite, indicateur, seuil_reussite,
             chapitre_id, matiere_id, difficulte),
        )

    def lister_objectifs(self) -> list[dict]:
        return self._lire("SELECT * FROM objectifs ORDER BY date_limite IS NULL, date_limite")

    # --- Séances et réponses -----------------------------------------------

    def ajouter_seance(self, activite: str, chapitre_id: int | None = None,
                       date_prevue: str | None = None) -> int:
        return self._ecrire(
            "INSERT INTO seances (activite, chapitre_id, date_prevue) VALUES (?, ?, ?)",
            (activite, chapitre_id, date_prevue),
        )

    def terminer_seance(self, seance_id: int, score: float, score_max: float,
                        duree_minutes: int) -> None:
        self._ecrire(
            """UPDATE seances
               SET statut = 'faite', score = ?, score_max = ?, duree_minutes = ?,
                   terminee_le = datetime('now')
               WHERE id = ?""",
            (score, score_max, duree_minutes, seance_id),
        )

    def enregistrer_reponse(self, seance_id: int, question: str, correcte: bool,
                            notion_id: int | None = None) -> int:
        return self._ecrire(
            "INSERT INTO reponses (seance_id, notion_id, question, correcte) VALUES (?, ?, ?, ?)",
            (seance_id, notion_id, question, int(correcte)),
        )

    def lister_seances(self, statut: str | None = None) -> list[dict]:
        if statut is None:
            return self._lire("SELECT * FROM seances ORDER BY id")
        return self._lire("SELECT * FROM seances WHERE statut = ? ORDER BY id", (statut,))

    def taux_reussite_par_notion(self, chapitre_id: int) -> list[dict]:
        """Pour chaque notion d'un chapitre : nombre de réponses et part de réponses justes."""
        return self._lire(
            """SELECT n.id, n.nom,
                      COUNT(r.id)              AS nb_reponses,
                      AVG(r.correcte)          AS taux_reussite
               FROM notions n
               LEFT JOIN reponses r ON r.notion_id = n.id
               WHERE n.chapitre_id = ?
               GROUP BY n.id
               ORDER BY taux_reussite IS NULL, taux_reussite""",
            (chapitre_id,),
        )


if __name__ == "__main__":
    base = BaseDeDonnees()
    print(f"Base prête : {base.chemin}")
    print("Matières :", [m["nom"] for m in base.lister_matieres()])