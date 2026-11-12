from dataclasses import dataclass
from groq import Groq
import config


@dataclass
class ReponseLLM:

    texte: str
    tokens_entree: int
    tokens_sortie: int

    @property
    def tokens_total(self) -> int:
        return self.tokens_entree + self.tokens_sortie


class ServiceLLM:

    def __init__(self, modele: str | None = None, temperature: float | None = None):
        self._client = Groq(api_key=config.GROQ_API_KEY)
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

    def generer(self, messages: list[dict], temperature: float | None = None) -> ReponseLLM:
        messages = self.preparer_messages(messages)
        reponse = self._client.chat.completions.create(
            model=self.modele,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            max_completion_tokens=config.MAX_TOKENS,
            reasoning_effort=config.REASONING_EFFORT,
            include_reasoning=False,  
        )
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
        reponse = self._client.chat.completions.create(**self._parametres(messages, temperature))
        usage = reponse.usage
        return ReponseLLM(
            texte=reponse.choices[0].message.content or "",
            tokens_entree=usage.prompt_tokens,
            tokens_sortie=usage.completion_tokens,
        )

    def generer_stream(self, messages: list[dict], temperature: float | None = None):
        """Produit la réponse morceau par morceau, au fil de la génération."""
        messages = self.preparer_messages(messages)
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


if __name__ == "__main__":

    service = ServiceLLM()
    question = input("Pose ta question :\n> ")
    conversation = [{"role": "user", "content": question}]
    print("\n--- réponse en streaming ---")
    for morceau in service.generer_stream(conversation):
        print(morceau, end="", flush=True)
    print()