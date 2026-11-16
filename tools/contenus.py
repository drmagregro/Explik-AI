"""Outils de génération de contenus, exposés à l'agent Lecture."""
from coach.contenus import GenerateurContenus
from tools import Outil


def creer_outil_fiche(base) -> Outil:
    generateur = None   # créé au premier appel : pas de client API tant que l'outil n'est pas utilisé

    def generer_fiche(chapitre_id: int):
        nonlocal generateur
        generateur = generateur or GenerateurContenus(base=base)
        return generateur.generer_fiche(chapitre_id)

    return Outil(
        "generer_fiche",
        "Génère et enregistre une fiche de révision (notions, définitions, exemples, pièges, "
        "résumé) à partir du cours d'un chapitre, puis la renvoie.",
        {"type": "object",
         "properties": {"chapitre_id": {"type": "integer",
                                        "description": "Identifiant du chapitre, donné par lister_chapitres."}},
         "required": ["chapitre_id"]},
        generer_fiche,
    )
