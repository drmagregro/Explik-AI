"""Classe de base de tous les agents du coach (contrat du jour 1).

Un agent = un nom, une description (ce qu'il sait faire), un prompt (prompts/*.md)
et quelques outils. Il ne parle jamais aux API lui-même : run() passe par la boucle
agentique de services/llm.py.

Pour l'orchestrateur, chaque agent est simplement un outil de plus (comme_outil).
"""
from abc import ABC, abstractmethod

import config
from services.llm import ReponseAgent, ServiceLLM
from tools import BoiteAOutils, Outil


class Agent(ABC):
    nom: str             # identifiant court, sans espace : « quiz »
    description: str     # ce que l'agent sait faire : c'est ce qui aide l'orchestrateur à choisir
    fichier_prompt: str  # nom du fichier dans prompts/ : « quiz.md »

    def __init__(self, service: ServiceLLM | None = None):
        self.service = service or ServiceLLM()

    @abstractmethod
    def outils(self) -> list[Outil]:
        """Les outils que cet agent a le droit d'appeler."""

    def prompt(self) -> str:
        return self.service.charger_prompt_systeme(self.fichier_prompt)

    def run(self, messages: list[dict]) -> ReponseAgent:
        """Traite une conversation avec sa propre boucle, son prompt et ses outils."""
        return self.service.generer_avec_outils(
            messages, BoiteAOutils(self.outils()), prompt_systeme=self.prompt(),
        )

    def comme_outil(self, conversation: list[dict] | None = None,
                    journal: list[ReponseAgent] | None = None) -> Outil:
        """Présente l'agent à l'orchestrateur comme un outil « demander_agent_<nom> ».

        conversation : l'historique vu par l'orchestrateur. L'agent en reçoit les derniers
        échanges avant la consigne, pour garder le fil (ex. corriger la question de quiz
        qu'il a posée au message précédent).
        journal : si fourni, chaque réponse complète de l'agent y est ajoutée.
        """
        # Sans le dernier message : c'est la demande en cours, que la consigne reprend
        precedents = (conversation or [])[:-1][-config.CONTEXTE_AGENT_ECHANGES * 2:]

        def deleguer(consigne: str) -> dict:
            reponse = self.run(precedents + [{"role": "user", "content": consigne}])
            if journal is not None:
                journal.append(reponse)
            # La réponse en dernier : si le résultat est tronqué, c'est elle qui est coupée
            return {"agent": self.nom, "outils_utilises": [appel.nom for appel in reponse.appels],
                    "reponse": reponse.texte}

        parametres = {
            "type": "object",
            "properties": {"consigne": {
                "type": "string",
                "description": "La demande de l'élève reformulée pour l'agent, avec tout le "
                               "contexte utile (chapitre, matière, ce qu'il veut obtenir).",
            }},
            "required": ["consigne"],
        }
        return Outil(f"demander_agent_{self.nom}", self.description, parametres, deleguer)
