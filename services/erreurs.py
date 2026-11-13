import groq


class ErreurService(Exception):
    """Une erreur prévisible d'un service. Le message est en français, prêt à afficher."""


def traduire_erreur_groq(erreur: groq.APIError) -> ErreurService:
    """Transforme une exception du client Groq en ErreurService.

    Les messages sont fixes : on n'y met jamais str(erreur), qui pourrait contenir la clé.
    """
    # APITimeoutError hérite de APIConnectionError : à tester en premier
    if isinstance(erreur, groq.APITimeoutError):
        message = "Le service a mis trop de temps à répondre. Réessaie dans un instant."
    elif isinstance(erreur, groq.APIConnectionError):
        message = "Impossible de joindre le service. Vérifie ta connexion internet."
    elif isinstance(erreur, groq.AuthenticationError):
        message = "Clé API Groq refusée (401). Vérifie GROQ_API_KEY dans .env."
    elif isinstance(erreur, groq.RateLimitError):
        message = "Quota atteint (429). Attends quelques secondes avant de réessayer."
    elif isinstance(erreur, groq.BadRequestError):
        message = "La requête a été refusée (image ou message non accepté). Essaie autre chose."
    elif isinstance(erreur, groq.InternalServerError):
        message = "Le service Groq a un problème temporaire. Réessaie plus tard."
    else:
        message = "Une erreur est survenue avec le service. Réessaie."
    return ErreurService(message)
