"""Génération de contenus de révision (fiches) à partir du texte d'un chapitre."""
import json

import config
from services.erreurs import ErreurService
from services.llm import ServiceLLM
from storage.database import BaseDeDonnees


def lire_flashcards(texte: str) -> list[dict]:
    """Valide la sortie JSON du modèle. Lève ValueError si elle est inutilisable."""
    texte = texte.strip()
    if texte.startswith("```"):   # le modèle ajoute parfois un bloc de code markdown
        texte = texte.strip("`").removeprefix("json").strip()
    cartes = json.loads(texte)
    if not isinstance(cartes, list) or not cartes:
        raise ValueError("Une liste de cartes est attendue.")
    propres = []
    for carte in cartes:
        if not isinstance(carte, dict):
            raise ValueError("Chaque carte doit être un objet.")
        champs = {cle: str(carte.get(cle) or "").strip() for cle in ("question", "reponse", "notion")}
        if not champs["question"] or not champs["reponse"]:
            raise ValueError("Une carte n'a pas de question ou de réponse.")
        propres.append(champs)
    return propres


class GenerateurContenus:

    def __init__(self, service: ServiceLLM | None = None, base: BaseDeDonnees | None = None):
        self.service = service or ServiceLLM()
        self.base = base or BaseDeDonnees()

    def _demander(self, chapitre_id: int, fichier_prompt: str) -> tuple[dict, str]:
        """Envoie le cours d'un chapitre au modèle avec une consigne. Renvoie (chapitre, réponse)."""
        chapitre = self.base.obtenir_chapitre(chapitre_id)
        if chapitre is None:
            raise ErreurService(f"Le chapitre {chapitre_id} n'existe pas.")
        if not chapitre["texte"].strip():
            raise ErreurService(f"Le chapitre « {chapitre['titre']} » n'a pas de texte de cours.")

        # Le cours est encadré par des balises : le modèle le traite comme une donnée.
        # La consigne est dans le message user car ServiceLLM impose déjà le prompt système.
        consigne = (config.PROMPTS_DIR / fichier_prompt).read_text(encoding="utf-8")
        demande = (f"{consigne}\n\n"
                   f"Chapitre : {chapitre['titre']}\n"
                   f"<cours>\n{chapitre['texte']}\n</cours>")
        return chapitre, self.service.generer([{"role": "user", "content": demande}]).texte.strip()

    def generer_fiche(self, chapitre_id: int) -> dict:
        """Génère la fiche d'un chapitre, l'enregistre et la renvoie."""
        chapitre, fiche = self._demander(chapitre_id, "fiches.md")
        if not fiche:
            raise ErreurService("Le modèle n'a pas renvoyé de fiche. Réessaie.")

        contenu_id = self.base.ajouter_contenu(chapitre_id, "fiche", f"Fiche : {chapitre['titre']}", fiche)
        return {"id": contenu_id, "titre": chapitre["titre"], "fiche": fiche}

    def generer_flashcards(self, chapitre_id: int) -> list[dict]:
        """Génère les flashcards d'un chapitre et remplace les précédentes.

        Le JSON du modèle est validé ; s'il est mal formé, on relance une fois, puis on signale.
        """
        for essai in (1, 2):
            chapitre, brut = self._demander(chapitre_id, "flashcards.md")
            try:
                cartes = lire_flashcards(brut)
                break
            except ValueError as erreur:   # json.JSONDecodeError en est un
                if essai == 2:
                    raise ErreurService("Le modèle n'a pas renvoyé de flashcards lisibles. "
                                        "Réessaie dans un instant.") from erreur

        notions = {n["nom"].lower(): n["id"] for n in self.base.lister_notions(chapitre_id)}
        self.base.supprimer_contenus(chapitre_id, "flashcard")
        for carte in cartes:
            nom = carte["notion"]
            if nom and nom.lower() not in notions:
                notions[nom.lower()] = self.base.ajouter_notion(chapitre_id, nom)
            self.base.ajouter_contenu(chapitre_id, "flashcard", chapitre["titre"], carte["question"],
                                      reponse=carte["reponse"], notion_id=notions.get(nom.lower()))
        return cartes
