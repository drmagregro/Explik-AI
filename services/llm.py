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

    def generer(self, messages: list[dict], temperature: float | None = None) -> ReponseLLM:
       
        reponse = self._client.chat.completions.create(
            model=self.modele,
            messages=messages,
            temperature=self.temperature if temperature is None else temperature,
            max_completion_tokens=config.MAX_TOKENS,
            reasoning_effort=config.REASONING_EFFORT,
            include_reasoning=False,  
        )
        usage = reponse.usage
        return ReponseLLM(
            texte=reponse.choices[0].message.content or "",
            tokens_entree=usage.prompt_tokens,
            tokens_sortie=usage.completion_tokens,
        )


if __name__ == "__main__":
   
    service = ServiceLLM()
    question = input("Pose ta question :\n> ")
    conversation = [
        {"role": "system", "content": "Tu es un assistant qui répond en français."},
        {"role": "user", "content": question},
    ]
    for temp in (0.0, 1.0):
        resultat = service.generer(conversation, temperature=temp)
        print(f"\n--- temperature {temp} ---")
        print(resultat.texte)
        print(f"[tokens : {resultat.tokens_entree} en entrée, "
              f"{resultat.tokens_sortie} en sortie, {resultat.tokens_total} au total]")