from dataclasses import dataclass
import groq

import config
from services.erreurs import traduire_erreur_groq


@dataclass
class ReponseLLM:

    texte: str
    tokens_entree: int
    tokens_sortie: int

    @property
    def tokens_total(self) -> int:
        return self.tokens_entree + self.tokens_sortie


@dataclass
class AppelOutil:
    """Trace d'un outil appelé pendant la boucle : utile pour l'afficher et déboguer."""

    nom: str
    arguments: str
    resultat: str


@dataclass
class ReponseAgent:

    texte: str
    appels: list[AppelOutil]
    tours: int
    tokens_total: int


class ServiceLLM:

    def __init__(self, modele: str | None = None, temperature: float | None = None):
        self._client = groq.Groq(api_key=config.GROQ_API_KEY,
                                 timeout=config.LLM_TIMEOUT_SECONDES)
        self.modele = modele or config.LLM_MODEL
        self.temperature = config.TEMPERATURE if temperature is None else temperature

    @staticmethod
    def charger_prompt_systeme() -> str:
        """Lit le prompt système depuis prompts/system.md (jamais dans le code)."""
        return (config.PROMPTS_DIR / "system.md").read_text(encoding="utf-8")

    @staticmethod
    def preparer_messages(historique: list[dict]) -> list[dict]:
        """Construit ce qu'on envoie au modèle : system + N derniers échanges.

        Le modèle n'a aucune mémoire : on lui renvoie l'historique à chaque appel.
        Un échange = 1 message user + 1 message assistant, soit N * 2 messages.
        """
        sans_system = [m for m in historique if m["role"] != "system"]
        recents = sans_system[-config.MAX_ECHANGES_HISTORIQUE * 2:]
        # la fenêtre ne doit pas commencer au milieu d'un échange
        while recents and recents[0]["role"] != "user":
            recents = recents[1:]
        prompt = {"role": "system", "content": ServiceLLM.charger_prompt_systeme()}
        return [prompt] + recents

    @classmethod
    def vision(cls) -> "ServiceLLM":
        return cls(modele=config.VISION_MODEL)

    def _parametres(self, messages: list[dict], temperature: float | None) -> dict:
        return {
            "model": self.modele,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_completion_tokens": config.MAX_TOKENS,
            **config.PARAMETRES_RAISONNEMENT.get(self.modele, {}),
        }

    def generer(self, messages: list[dict], temperature: float | None = None) -> ReponseLLM:
        messages = self.preparer_messages(messages)
        try:
            reponse = self._client.chat.completions.create(**self._parametres(messages, temperature))
        except groq.APIError as erreur:
            raise traduire_erreur_groq(erreur) from erreur
        usage = reponse.usage
        return ReponseLLM(
            texte=reponse.choices[0].message.content or "",
            tokens_entree=usage.prompt_tokens,
            tokens_sortie=usage.completion_tokens,
        )

    def generer_stream(self, messages: list[dict], temperature: float | None = None):
        """Produit la réponse morceau par morceau, au fil de la génération."""
        messages = self.preparer_messages(messages)
        try:
            flux = self._client.chat.completions.create(
                **self._parametres(messages, temperature),
                stream=True,
            )
            for morceau in flux:
                if not morceau.choices:
                    continue
                texte = morceau.choices[0].delta.content
                if texte:
                    yield texte
        except groq.APIError as erreur:
            raise traduire_erreur_groq(erreur) from erreur

    # --- Boucle agentique ------------------------------------------------------

    def _appeler_avec_outils(self, messages: list[dict], boite, **options):
        """Un appel au modèle avec la liste des outils.

        Avec des outils, gpt-oss chez Groq échoue parfois en « output_parse_failed » :
        son raisonnement interne déborde dans la réponse. Deux parades :
        - on ne lui demande pas de cacher son raisonnement (include_reasoning=False le perturbe) ;
          il revient dans un champ à part, qu'on n'affiche pas ;
        - on retente une fois si l'erreur se produit quand même.
        """
        parametres = self._parametres(messages, None)
        parametres.pop("include_reasoning", None)
        for essai in (1, 2):
            try:
                return self._client.chat.completions.create(
                    **parametres, tools=boite.schemas(), **options,
                )
            except groq.BadRequestError as erreur:
                if "output_parse_failed" in str(erreur) and essai == 1:
                    continue   # on retente une fois
                raise traduire_erreur_groq(erreur) from erreur
            except groq.APIError as erreur:
                raise traduire_erreur_groq(erreur) from erreur

    def generer_avec_outils(self, historique: list[dict], boite,
                            max_tours: int | None = None) -> ReponseAgent:
        """Laisse le modèle appeler des outils jusqu'à sa réponse finale.

        1. On envoie la conversation et la liste des outils.
        2. Le modèle répond, ou demande un outil.
        3. On exécute l'outil et on ajoute son résultat à la conversation.
        4. On recommence, au plus max_tours fois : jamais de boucle sans fin.
        """
        max_tours = max_tours or config.MAX_TOURS_AGENT
        messages = self.preparer_messages(historique)
        appels: list[AppelOutil] = []
        tokens = 0

        for tour in range(1, max_tours + 1):
            reponse = self._appeler_avec_outils(messages, boite)
            tokens += reponse.usage.total_tokens
            message = reponse.choices[0].message
            if not message.tool_calls:   # pas d'outil demandé : c'est la réponse finale
                return ReponseAgent(message.content or "", appels, tour, tokens)

            # On garde la demande du modèle dans la conversation…
            demande = {"role": "assistant", "tool_calls": [
                {"id": appel.id, "type": "function",
                 "function": {"name": appel.function.name, "arguments": appel.function.arguments}}
                for appel in message.tool_calls
            ]}
            if message.content:
                demande["content"] = message.content
            messages.append(demande)

            # …puis le résultat de chaque outil, relié à sa demande par tool_call_id
            for appel in message.tool_calls:
                resultat = boite.executer(appel.function.name, appel.function.arguments)
                appels.append(AppelOutil(appel.function.name, appel.function.arguments, resultat))
                messages.append({"role": "tool", "tool_call_id": appel.id,
                                 "name": appel.function.name, "content": resultat})

        # Nombre de tours atteint : on interdit les outils pour obtenir une réponse
        reponse = self._appeler_avec_outils(messages, boite, tool_choice="none")
        tokens += reponse.usage.total_tokens
        return ReponseAgent(reponse.choices[0].message.content or "", appels, max_tours, tokens)


if __name__ == "__main__":
    import sys

    service = ServiceLLM()
    question = input("Pose ta question :\n> ")
    conversation = [{"role": "user", "content": question}]

    if "--agent" in sys.argv:
        # Test de la boucle agentique : python -m services.llm --agent
        from tools import creer_outils_coach

        resultat = service.generer_avec_outils(conversation, creer_outils_coach())
        for appel in resultat.appels:
            print(f"[outil] {appel.nom}({appel.arguments}) -> {appel.resultat[:120]}")
        print(f"\n{resultat.texte}")
        print(f"\n({resultat.tours} tour(s), {resultat.tokens_total} tokens)")
    else:
        print("\n--- réponse en streaming ---")
        for morceau in service.generer_stream(conversation):
            print(morceau, end="", flush=True)
        print()