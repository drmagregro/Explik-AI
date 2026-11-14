"""Outils que le modèle peut demander à appeler (tool calling).

Un outil = un nom, une description (c'est ce qui aide le modèle à choisir le bon),
des paramètres décrits en JSON Schema, et la fonction Python qui fait le travail.
Le modèle n'exécute jamais rien lui-même : il demande, BoiteAOutils exécute.

Ces outils ne font que LIRE la base. Un outil qui modifie ou envoie quelque chose
devra passer par la validation humaine (tâche 16).
"""
import json
from dataclasses import dataclass
from datetime import date
from typing import Callable

from storage.database import BaseDeDonnees

TAILLE_MAX_RESULTAT = 4000   # caractères renvoyés au modèle, pour ne pas exploser le contexte


@dataclass
class Outil:
    nom: str
    description: str
    parametres: dict          # JSON Schema des arguments
    fonction: Callable

    def schema(self) -> dict:
        """Description de l'outil au format attendu par l'API."""
        return {
            "type": "function",
            "function": {"name": self.nom, "description": self.description,
                         "parameters": self.parametres},
        }


class BoiteAOutils:
    """Un ensemble d'outils : donne leurs descriptions au modèle et exécute ses demandes."""

    def __init__(self, outils: list[Outil]):
        self._outils = {outil.nom: outil for outil in outils}

    def schemas(self) -> list[dict]:
        return [outil.schema() for outil in self._outils.values()]

    def executer(self, nom: str, arguments_json: str) -> str:
        """Exécute un outil et renvoie son résultat en texte JSON.

        Ne lève jamais d'erreur : une erreur est renvoyée au modèle comme résultat,
        pour qu'il puisse corriger sa demande au tour suivant.
        """
        outil = self._outils.get(nom)
        if outil is None:
            return json.dumps({"erreur": f"Outil inconnu : {nom}"}, ensure_ascii=False)
        try:
            arguments = json.loads(arguments_json or "{}")
            resultat = outil.fonction(**arguments)
        except (json.JSONDecodeError, TypeError) as erreur:
            return json.dumps({"erreur": f"Arguments invalides : {erreur}"}, ensure_ascii=False)
        except Exception as erreur:
            return json.dumps({"erreur": f"L'outil a échoué : {erreur}"}, ensure_ascii=False)
        texte = json.dumps(resultat, ensure_ascii=False, default=str)
        return texte[:TAILLE_MAX_RESULTAT]


# --- Les outils du coach (lecture seule) ----------------------------------------

def creer_outils_coach(base: BaseDeDonnees | None = None) -> BoiteAOutils:
    base = base or BaseDeDonnees()

    def date_du_jour():
        return {"date": date.today().isoformat()}

    def obtenir_profil():
        return base.obtenir_profil() or {"info": "Aucun profil enregistré."}

    def lister_chapitres():
        matieres = {m["id"]: m["nom"] for m in base.lister_matieres()}
        return [{"id": c["id"], "matiere": matieres.get(c["matiere_id"]), "titre": c["titre"],
                 "difficulte": c["difficulte"]} for c in base.lister_chapitres()]

    def lire_chapitre(chapitre_id: int):
        chapitre = base.obtenir_chapitre(chapitre_id)
        if chapitre is None:
            return {"erreur": f"Aucun chapitre avec l'id {chapitre_id}."}
        return {"titre": chapitre["titre"], "texte": chapitre["texte"]}

    def notions_a_revoir(chapitre_id: int):
        return base.taux_reussite_par_notion(chapitre_id)

    def lister_objectifs():
        return base.lister_objectifs()

    id_chapitre = {"type": "object",
                   "properties": {"chapitre_id": {"type": "integer",
                                                  "description": "Identifiant du chapitre, donné par lister_chapitres."}},
                   "required": ["chapitre_id"]}
    aucun = {"type": "object", "properties": {}}

    from tools.contenus import creer_outil_fiche   # import ici : tools.contenus importe ce fichier

    return BoiteAOutils([
        creer_outil_fiche(base),
        Outil("date_du_jour", "Donne la date d'aujourd'hui, pour calculer un délai ou planifier.",
              aucun, date_du_jour),
        Outil("obtenir_profil", "Lit le profil de l'élève : prénom, objectif, échéance, "
              "temps disponible par jour, difficultés.", aucun, obtenir_profil),
        Outil("lister_chapitres", "Liste les chapitres de cours de l'élève avec leur matière, "
              "leur identifiant et leur difficulté (1 à 5).", aucun, lister_chapitres),
        Outil("lire_chapitre", "Lit le texte du cours d'un chapitre. À utiliser avant d'expliquer "
              "ou d'interroger sur ce chapitre.", id_chapitre, lire_chapitre),
        Outil("notions_a_revoir", "Pour un chapitre, donne chaque notion avec le nombre de réponses "
              "et le taux de réussite aux quiz, de la moins maîtrisée à la mieux maîtrisée.",
              id_chapitre, notions_a_revoir),
        Outil("lister_objectifs", "Liste les objectifs de révision de l'élève, avec date limite "
              "et priorité.", aucun, lister_objectifs),
    ])