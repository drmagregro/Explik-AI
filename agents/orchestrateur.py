"""Orchestrateur (M1) : comprend la demande de l'élève et la confie au bon agent.

Pour lui, chaque agent spécialisé est un outil « demander_agent_<nom> » : appeler cet outil
lance la boucle de l'agent, avec son propre prompt et ses propres outils. Chaque niveau
garde sa limite de tours (config.MAX_TOURS_AGENT).

Test seul : python -m agents.orchestrateur
"""
from agents import Agent
from agents.lecture import AgentLecture
from agents.quiz import AgentQuiz
from agents.suivi import AgentSuivi
from services.llm import ReponseAgent, ServiceLLM
from tools import BoiteAOutils, Outil


class Orchestrateur(Agent):
    nom = "orchestrateur"
    description = "Comprend la demande de l'élève et la délègue au bon agent spécialisé."
    fichier_prompt = "orchestrateur.md"

    def __init__(self, service: ServiceLLM | None = None):
        super().__init__(service)
        # Un seul client Groq partagé par l'orchestrateur et ses agents
        self.agents = [AgentLecture(self.service), AgentQuiz(self.service), AgentSuivi(self.service)]

    def outils(self) -> list[Outil]:
        return [agent.comme_outil() for agent in self.agents]

    def prompt(self) -> str:
        # La personnalité du coach (system.md) + les règles de délégation
        return self.service.charger_prompt_systeme() + "\n\n" + super().prompt()

    def run(self, messages: list[dict]) -> ReponseAgent:
        """Comme Agent.run, avec deux différences :

        - chaque agent reçoit aussi les derniers échanges de la conversation ;
        - si un agent a répondu, c'est sa réponse qu'on renvoie telle quelle. En la
          réécrivant, l'orchestrateur perdait parfois tout son contenu (un planning
          réduit à « Voici ton planning »).

        Les outils sont recréés à chaque appel plutôt que de stocker la conversation
        dans l'objet : l'orchestrateur est partagé par toutes les sessions Streamlit.
        """
        journal: list[ReponseAgent] = []
        outils = [agent.comme_outil(messages, journal) for agent in self.agents]
        reponse = self.service.generer_avec_outils(
            messages, BoiteAOutils(outils), prompt_systeme=self.prompt(),
        )
        if journal:
            reponse.texte = journal[-1].texte
        return reponse


if __name__ == "__main__":
    # Les 4 demandes de la validation clé de la tâche 15
    orchestrateur = Orchestrateur()
    for demande in ["Fais-moi un quiz sur la cellule", "Voici une photo de mon cours",
                    "Quel est mon planning ?", "Bonjour"]:
        reponse = orchestrateur.run([{"role": "user", "content": demande}])
        agents = [appel.nom for appel in reponse.appels] or ["aucun agent"]
        print(f"\n« {demande} » -> {', '.join(agents)}")
        print("   " + reponse.texte[:150].replace("\n", " "))
