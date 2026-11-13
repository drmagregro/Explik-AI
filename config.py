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
VISION_MODEL = "qwen/qwen3.8-27b"   

TEMPERATURE = 0.7
MAX_TOKENS = 1024
MAX_ECHANGES_HISTORIQUE = 50   
REASONING_EFFORT = "low"   


PARAMETRES_RAISONNEMENT = {
    "openai/gpt-oss-120b": {"reasoning_effort": REASONING_EFFORT, "include_reasoning": False},
    "qwen/qwen3.8-27b": {"reasoning_effort": REASONING_EFFORT, "reasoning_format": "hidden"},
}

LLM_TIMEOUT_SECONDES = 30

# Transcription vocale (Whisper chez Groq)
STT_MODEL = "whisper-large-v3-turbo"
STT_LANGUE = "fr"
STT_TIMEOUT_SECONDES = 30
AUDIO_FREQUENCE_HZ = 16000
IMAGE_COTE_MAX = 1600       
IMAGE_QUALITE_JPEG = 85    

# Boucle agentique (tool calling)
MAX_TOURS_AGENT = 5   # appels d'outils au maximum avant de forcer une réponse finale
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "coach.db" 