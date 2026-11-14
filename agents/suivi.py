"""Agent Suivi (M4) : planning, répétitions et progression.

Version minimale pour l'orchestrateur (tâche 15) : il lit le profil, les objectifs
et les résultats. Génération du programme : tâche 26 ; répétition espacée : tâche 29.

Test seul : python -m agents.suivi
"""
from agents import Agent
from tools import Outil, choisir_outils


class AgentSuivi(Agent):
    nom = "suivi"
    description = (
        "Agent Suivi : gère le planning de révision, l'échéance, les objectifs et la progression "
        "de l'élève (notions fragiles, résultats). À utiliser pour toute question sur le planning, "
        "le temps restant, quoi réviser ensuite, les objectifs ou les progrès."
    )
    fichier_prompt = "suivi.md"

    def outils(self) -> list[Outil]:
        return choisir_outils("date_du_jour", "obtenir_profil", "lister_objectifs",
                              "lister_chapitres", "notions_a_revoir")


if __name__ == "__main__":
    reponse = AgentSuivi().run([{"role": "user", "content": "Combien de jours me reste-t-il avant mon échéance ?"}])
    print([appel.nom for appel in reponse.appels])
    print(reponse.texte)
