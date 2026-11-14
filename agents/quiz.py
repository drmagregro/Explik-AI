"""Agent Quiz (M3) : interroge l'élève, corrige et explique.

Version minimale pour l'orchestrateur (tâche 15) : il pose des questions à partir
du texte du chapitre. Génération en JSON et enregistrement des scores : tâches 23 et 24.

Test seul : python -m agents.quiz
"""
from agents import Agent
from tools import Outil, choisir_outils


class AgentQuiz(Agent):
    nom = "quiz"
    description = (
        "Agent Quiz : interroge l'élève sur un chapitre (quiz, QCM, questions ouvertes), "
        "corrige ses réponses et explique une notion mal comprise avec des exemples. "
        "À utiliser quand l'élève veut être interrogé, s'entraîner ou se faire expliquer une notion."
    )
    fichier_prompt = "quiz.md"

    def outils(self) -> list[Outil]:
        return choisir_outils("obtenir_profil", "lister_chapitres", "lire_chapitre", "notions_a_revoir")


if __name__ == "__main__":
    reponse = AgentQuiz().run([{"role": "user", "content": "Fais-moi un quiz de 3 questions sur la cellule."}])
    print([appel.nom for appel in reponse.appels])
    print(reponse.texte)
