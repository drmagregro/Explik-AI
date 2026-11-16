"""Génération de contenus de révision (fiches) à partir du texte d'un chapitre."""
import config
from services.erreurs import ErreurService
from services.llm import ServiceLLM
from storage.database import BaseDeDonnees


class GenerateurContenus:

    def __init__(self, service: ServiceLLM | None = None, base: BaseDeDonnees | None = None):
        self.service = service or ServiceLLM()
        self.base = base or BaseDeDonnees()

    @staticmethod
    def _consigne_fiche() -> str:
        """La consigne vient de prompts/fiches.md, jamais du code."""
        return (config.PROMPTS_DIR / "fiches.md").read_text(encoding="utf-8")

    def generer_fiche(self, chapitre_id: int) -> dict:
        """Génère la fiche d'un chapitre, l'enregistre et la renvoie."""
        chapitre = self.base.obtenir_chapitre(chapitre_id)
        if chapitre is None:
            raise ErreurService(f"Le chapitre {chapitre_id} n'existe pas.")
        if not chapitre["texte"].strip():
            raise ErreurService(f"Le chapitre « {chapitre['titre']} » n'a pas de texte de cours.")

        # Le cours est encadré par des balises : le modèle le traite comme une donnée.
        # La consigne est dans le message user car ServiceLLM impose déjà le prompt système.
        demande = (f"{self._consigne_fiche()}\n\n"
                   f"Chapitre : {chapitre['titre']}\n"
                   f"<cours>\n{chapitre['texte']}\n</cours>")
        fiche = self.service.generer([{"role": "user", "content": demande}]).texte.strip()
        if not fiche:
            raise ErreurService("Le modèle n'a pas renvoyé de fiche. Réessaie.")

        contenu_id = self.base.ajouter_contenu(chapitre_id, "fiche", f"Fiche : {chapitre['titre']}", fiche)
        return {"id": contenu_id, "titre": chapitre["titre"], "fiche": fiche}
