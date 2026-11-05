"""Configuration centrale du projet : clés API, modèles et paramètres.

Règle du projet : aucun autre fichier ne contient de nom de modèle ni de clé.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Dossier racine du projet (celui qui contient ce fichier)
ROOT_DIR = Path(__file__).resolve().parent

# Charge les variables du fichier .env dans l'environnement
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


# --- Clés API (lues dans .env, jamais écrites ici) ---
GROQ_API_KEY = _cle_obligatoire("GROQ_API_KEY")

# --- Modèles (vérifier les noms sur console.groq.com/docs/models) ---
LLM_MODEL = "openai/gpt-oss-120b"

# --- Paramètres de génération ---
TEMPERATURE = 0.7   # 0 = réponses stables, 1 = réponses plus variées
MAX_TOKENS = 1024   # longueur maximale d'une réponse
REASONING_EFFORT = "low" # effort de réflexion de gpt-oss : "low", "medium", "high"

# --- Chemins ---
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"