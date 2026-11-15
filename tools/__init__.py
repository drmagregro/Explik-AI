"""Outils que le modèle peut demander à appeler (tool calling).

Un outil = un nom, une description (c'est ce qui aide le modèle à choisir le bon),
des paramètres décrits en JSON Schema, et la fonction Python qui fait le travail.
Le modèle n'exécute jamais rien lui-même : il demande, BoiteAOutils exécute.

Validation humaine (tâche 16) : un outil irréversible ou visible par d'autres est marqué
sensible=True. La boucle agentique ne l'exécute jamais d'elle-même : elle s'arrête, l'interface
affiche son résumé, et l'outil ne tourne qu'après un clic sur « Confirmer ».
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
    sensible: bool = False            # irréversible ou visible par d'autres : validation humaine
    resumer: Callable | None = None   # arguments -> phrase que l'élève lit avant de confirmer

    def schema(self) -> dict:
        """Description de l'outil au format attendu par l'API."""
        return {
            "type": "function",
            "function": {"name": self.nom, "description": self.description,
                         "parameters": self.parametres},
        }


class ValidationRequise(Exception):
    """Un agent délégué attend la décision de l'élève sur une action sensible.

    BoiteAOutils la laisse remonter au lieu de la renvoyer au modèle comme une erreur :
    c'est l'orchestrateur qui la rattrape pour mettre toute la demande en pause.
    """

    def __init__(self, action):
        super().__init__(action.resume)
        self.action = action


class BoiteAOutils:
    """Un ensemble d'outils : donne leurs descriptions au modèle et exécute ses demandes."""

    def __init__(self, outils: list[Outil]):
        self._outils = {outil.nom: outil for outil in outils}

    def schemas(self) -> list[dict]:
        return [outil.schema() for outil in self._outils.values()]

    def est_sensible(self, nom: str) -> bool:
        outil = self._outils.get(nom)
        return outil is not None and outil.sensible

    def resumer(self, nom: str, arguments_json: str) -> str:
        """La phrase affichée à l'élève avant de confirmer une action sensible."""
        try:
            return self._outils[nom].resumer(**json.loads(arguments_json or "{}"))
        except Exception:
            return f"{nom}({arguments_json})"   # pas de résumé possible : on montre l'appel brut

    def executer(self, nom: str, arguments_json: str, confirme: bool = False) -> str:
        """Exécute un outil et renvoie son résultat en texte JSON.

        Ne lève jamais d'erreur (sauf ValidationRequise) : une erreur est renvoyée au modèle
        comme résultat, pour qu'il puisse corriger sa demande au tour suivant.
        Un outil sensible ne s'exécute qu'avec confirme=True, donné après le clic de l'élève.
        """
        outil = self._outils.get(nom)
        if outil is None:
            return json.dumps({"erreur": f"Outil inconnu : {nom}"}, ensure_ascii=False)
        if outil.sensible and not confirme:
            return json.dumps({"erreur": "Cette action demande la confirmation de l'élève."},
                              ensure_ascii=False)
        try:
            arguments = json.loads(arguments_json or "{}")
            resultat = outil.fonction(**arguments)
        except ValidationRequise:
            raise
        except (json.JSONDecodeError, TypeError) as erreur:
            return json.dumps({"erreur": f"Arguments invalides : {erreur}"}, ensure_ascii=False)
        except Exception as erreur:
            return json.dumps({"erreur": f"L'outil a échoué : {erreur}"}, ensure_ascii=False)
        texte = json.dumps(resultat, ensure_ascii=False, default=str)
        return texte[:TAILLE_MAX_RESULTAT]


# --- Les outils du coach -------------------------------------------------------

def lister_outils_coach(base: BaseDeDonnees | None = None) -> list[Outil]:
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

    def supprimer_objectif(objectif_id: int):
        if not base.supprimer_objectif(objectif_id):
            return {"erreur": f"Aucun objectif avec l'id {objectif_id}."}
        return {"supprime": objectif_id}

    def resumer_suppression(objectif_id: int) -> str:
        objectif = base.obtenir_objectif(objectif_id)
        if objectif is None:
            return f"Supprimer l'objectif n°{objectif_id} (introuvable)"
        return f"Supprimer définitivement l'objectif « {objectif['intitule']} »"

    id_chapitre = {"type": "object",
                   "properties": {"chapitre_id": {"type": "integer",
                                                  "description": "Identifiant du chapitre, donné par lister_chapitres."}},
                   "required": ["chapitre_id"]}
    aucun = {"type": "object", "properties": {}}
    id_objectif = {"type": "object",
                   "properties": {"objectif_id": {"type": "integer",
                                                  "description": "Identifiant de l'objectif, donné par lister_objectifs."}},
                   "required": ["objectif_id"]}

    return [
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
        Outil("supprimer_objectif", "Supprime définitivement un objectif de l'élève. Uniquement "
              "s'il le demande. L'appel affiche lui-même une confirmation à l'élève : ne la demande "
              "pas par écrit avant.",
              id_objectif, supprimer_objectif, sensible=True, resumer=resumer_suppression),
    ]


def creer_outils_coach(base: BaseDeDonnees | None = None) -> BoiteAOutils:
    """Tous les outils du coach dans une seule boîte."""
    return BoiteAOutils(lister_outils_coach(base))


def choisir_outils(*noms: str, base: BaseDeDonnees | None = None) -> list[Outil]:
    """Les outils du coach dont le nom est donné : chaque agent n'a accès qu'à ceux-là."""
    outils = {outil.nom: outil for outil in lister_outils_coach(base)}
    inconnus = set(noms) - outils.keys()
    if inconnus:
        raise ValueError(f"Outils inconnus : {', '.join(sorted(inconnus))}")
    return [outils[nom] for nom in noms]