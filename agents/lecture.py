"""Agent Lecture (M2) : transforme un cours en contenu structuré.

Version minimale pour l'orchestrateur (tâche 15) : il lit les chapitres déjà en base.
La lecture d'une photo de cours arrive avec la tâche 20.

Test seul : python -m agents.lecture
"""
from agents import Agent
from tools import Outil, choisir_outils


class AgentLecture(Agent):
    nom = "lecture"
    description = (
        "Agent Lecture : lit et structure un cours (photo, PDF ou chapitre déjà importé) "
        "et en extrait les notions clés, définitions et formules. À utiliser quand l'élève "
        "envoie ou mentionne un support de cours, ou demande un résumé ou les notions d'un chapitre."
    )
    fichier_prompt = "lecture.md"

    def outils(self) -> list[Outil]:
        return choisir_outils("lister_chapitres", "lire_chapitre")


if __name__ == "__main__":
    reponse = AgentLecture().run([{"role": "user", "content": "Quelles sont les notions clés du chapitre Dérivées ?"}])
    print([appel.nom for appel in reponse.appels])
    print(reponse.texte)
