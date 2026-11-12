import time
from dataclasses import dataclass

import groq

import config


class ErreurTranscription(Exception):
    """L'audio n'a pas pu être transcrit. Le message est prêt à afficher."""


@dataclass
class Transcription:
    texte: str
    duree_secondes: float


class ServiceSTT:

    def __init__(self, modele=None, langue=None):
        self._client = groq.Groq(api_key=config.GROQ_API_KEY,
                                 timeout=config.STT_TIMEOUT_SECONDES)
        self.modele = modele or config.STT_MODEL
        self.langue = langue or config.STT_LANGUE

    def transcrire(self, octets_audio, nom_fichier="message.wav"):
        if not octets_audio:
            raise ErreurTranscription("L'enregistrement est vide.")

        debut = time.perf_counter()
        try:
            texte = self._client.audio.transcriptions.create(
                file=(nom_fichier, octets_audio),
                model=self.modele,
                language=self.langue,
                response_format="text",
                temperature=0,
            )
        except groq.AuthenticationError as erreur:
            raise ErreurTranscription("Clé API Groq refusée : vérifie .env.") from erreur
        except groq.RateLimitError as erreur:
            raise ErreurTranscription("Quota atteint (429). Attends une minute.") from erreur
        except groq.APIConnectionError as erreur:
            raise ErreurTranscription("Impossible de joindre le service de transcription.") from erreur
        except groq.APIStatusError as erreur:
            raise ErreurTranscription("La transcription a échoué.") from erreur
        duree = time.perf_counter() - debut

        texte = texte.strip()
        if not texte:
            raise ErreurTranscription("Je n'ai rien entendu. Parle un peu plus fort.")
        return Transcription(texte=texte, duree_secondes=duree)