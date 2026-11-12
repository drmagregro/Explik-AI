import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent


load_dotenv(ROOT_DIR / ".env")


def _cle_obligatoire(nom: str) -> str:
    """Renvoie la variable d'environnement, ou arrête avec un message clair."""
    valeur = os.getenv(nom)
    if not valeur:
        raise RuntimeError(
            f"La variable {nom} est absente. "
            "Copie .env.example en .env, puis colle ta clé dedans."
        )
    return valeur


GROQ_API_KEY = _cle_obligatoire("GROQ_API_KEY")

LLM_MODEL = "openai/gpt-oss-120b"


TEMPERATURE = 0.7
MAX_TOKENS = 1024   
REASONING_EFFORT = "low" 


PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"