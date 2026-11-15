import json
from dataclasses import dataclass, field
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
class EtatBoucle:
    """Où en est une boucle agentique : de quoi la mettre en pause, puis la reprendre."""

    messages: list[dict]
    boite: object
    max_tours: int
    tour: int = 0
    appels: list[AppelOutil] = field(default_factory=list)
    tokens: int = 0
    a_traiter: list[dict] = field(default_factory=list)   # outils demandés, pas encore exécutés


@dataclass
class ActionEnAttente:
    """Un outil sensible que le modèle veut appeler : rien ne s'exécute avant la décision de l'élève."""

    resume: str                # ce que l'élève lit : « Supprimer définitivement l'objectif … »
    etat: EtatBoucle
    agent: str | None = None   # l'agent qui la demande, quand elle vient d'une délégation


@dataclass
class ReponseAgent:

    texte: str
    appels: list[AppelOutil]
    tours: int
    tokens_total: int
    en_attente: ActionEnAttente | None = None   # rempli quand la boucle s'est mise en pause


class ServiceLLM:

    def __init__(self, modele: str | None = None, temperature: float | None = None):
        self._client = groq.Groq(api_key=config.GROQ_API_KEY,
                                 timeout=config.LLM_TIMEOUT_SECONDES)
        self.modele = modele or config.LLM_MODEL
        self.temperature = config.TEMPERATURE if temperature is None else temperature

    @staticmethod
    def charger_prompt_systeme(fichier: str = "system.md") -> str:
        """Lit un prompt depuis prompts/ (jamais dans le code). Par défaut, celui du coach."""
        return (config.PROMPTS_DIR / fichier).read_text(encoding="utf-8")

    @staticmethod
    def preparer_messages(historique: list[dict], prompt_systeme: str | None = None) -> list[dict]:
        """Construit ce qu'on envoie au modèle : system + N derniers échanges.

        Le modèle n'a aucune mémoire : on lui renvoie l'historique à chaque appel.
        Un échange = 1 message user + 1 message assistant, soit N * 2 messages.
        prompt_systeme permet à un agent d'utiliser son propre prompt à la place de system.md.
        """
        sans_system = [m for m in historique if m["role"] != "system"]
        recents = sans_system[-config.MAX_ECHANGES_HISTORIQUE * 2:]
        # la fenêtre ne doit pas commencer au milieu d'un échange
        while recents and recents[0]["role"] != "user":
            recents = recents[1:]
        contenu = prompt_systeme or ServiceLLM.charger_prompt_systeme()
        return [{"role": "system", "content": contenu}] + recents

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
                            max_tours: int | None = None,
                            prompt_systeme: str | None = None) -> ReponseAgent:
        """Laisse le modèle appeler des outils jusqu'à sa réponse finale.

        1. On envoie la conversation et la liste des outils.
        2. Le modèle répond, ou demande un outil.
        3. On exécute l'outil et on ajoute son résultat à la conversation.
        4. On recommence, au plus max_tours fois : jamais de boucle sans fin.

        Un outil sensible n'est pas exécuté : la boucle se met en pause et renvoie
        une réponse avec en_attente. On la reprend avec reprendre().
        """
        etat = EtatBoucle(self.preparer_messages(historique, prompt_systeme), boite,
                          max_tours or config.MAX_TOURS_AGENT)
        return self._boucle(etat)

    def reprendre(self, action: ActionEnAttente, accepte: bool) -> ReponseAgent:
        """Reprend une boucle en pause, une fois que l'élève a confirmé ou annulé.

        Confirmer exécute l'outil ; annuler renvoie au modèle un refus à la place du résultat.
        Dans les deux cas le modèle continue et peut en tenir compte dans sa réponse.
        """
        etat = action.etat
        appel = etat.a_traiter[0]["function"]
        if accepte:
            resultat = etat.boite.executer(appel["name"], appel["arguments"], confirme=True)
        else:
            resultat = json.dumps({"refus": "Action refusée par l'utilisateur. Ne la retente pas "
                                            "sans nouvelle demande de sa part."}, ensure_ascii=False)
        self._ajouter_resultat(etat, resultat)
        return self._boucle(etat)

    @staticmethod
    def _ajouter_resultat(etat: EtatBoucle, resultat: str) -> None:
        """Range le résultat du prochain outil à traiter, relié à sa demande par tool_call_id."""
        appel = etat.a_traiter.pop(0)
        nom, arguments = appel["function"]["name"], appel["function"]["arguments"]
        etat.appels.append(AppelOutil(nom, arguments, resultat))
        etat.messages.append({"role": "tool", "tool_call_id": appel["id"],
                              "name": nom, "content": resultat})

    def _boucle(self, etat: EtatBoucle) -> ReponseAgent:
        while True:
            # Les outils demandés au tour précédent ; un outil sensible met tout en pause
            while etat.a_traiter:
                appel = etat.a_traiter[0]["function"]
                if etat.boite.est_sensible(appel["name"]):
                    resume = etat.boite.resumer(appel["name"], appel["arguments"])
                    return ReponseAgent("", etat.appels, etat.tour, etat.tokens,
                                        en_attente=ActionEnAttente(resume, etat))
                self._ajouter_resultat(etat, etat.boite.executer(appel["name"], appel["arguments"]))

            if etat.tour == etat.max_tours:
                break
            etat.tour += 1
            reponse = self._appeler_avec_outils(etat.messages, etat.boite)
            etat.tokens += reponse.usage.total_tokens
            message = reponse.choices[0].message
            if not message.tool_calls:   # pas d'outil demandé : c'est la réponse finale
                return ReponseAgent(message.content or "", etat.appels, etat.tour, etat.tokens)

            # On garde la demande du modèle dans la conversation, puis on traite ses outils
            demande = {"role": "assistant", "tool_calls": [
                {"id": appel.id, "type": "function",
                 "function": {"name": appel.function.name, "arguments": appel.function.arguments}}
                for appel in message.tool_calls
            ]}
            if message.content:
                demande["content"] = message.content
            etat.messages.append(demande)
            etat.a_traiter = list(demande["tool_calls"])

        # Nombre de tours atteint : on interdit les outils pour obtenir une réponse
        reponse = self._appeler_avec_outils(etat.messages, etat.boite, tool_choice="none")
        etat.tokens += reponse.usage.total_tokens
        return ReponseAgent(reponse.choices[0].message.content or "", etat.appels,
                            etat.max_tours, etat.tokens)


if __name__ == "__main__":
    import sys

    service = ServiceLLM()
    question = input("Pose ta question :\n> ")
    conversation = [{"role": "user", "content": question}]

    print("\n--- réponse en streaming ---")
    for morceau in service.generer_stream(conversation):
        print(morceau, end="", flush=True)
    print()

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