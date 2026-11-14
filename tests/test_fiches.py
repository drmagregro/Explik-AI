"""Tests de la génération de fiches. Lancer : python -m unittest tests.test_fiches -v"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("GROQ_API_KEY", "gsk_cle_de_test")

from coach.contenus import GenerateurContenus, lire_flashcards
from services.erreurs import ErreurService
from services.llm import ReponseLLM
from storage.database import BaseDeDonnees
from tools import creer_outils_coach


class TestFiches(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.base = BaseDeDonnees(Path(self.dossier.name) / "test.db")
        matiere = self.base.ajouter_matiere("Maths")
        self.chapitre = self.base.ajouter_chapitre(matiere, "Dérivées", texte="La dérivée mesure une pente.")
        self.vide = self.base.ajouter_chapitre(matiere, "Vide", texte="  ")
        self.service = MagicMock()
        self.service.generer.return_value = ReponseLLM("## Notions\n- dérivée", 10, 10)
        self.generateur = GenerateurContenus(self.service, self.base)

    def tearDown(self):
        self.dossier.cleanup()

    def test_fiche_generee_et_enregistree(self):
        resultat = self.generateur.generer_fiche(self.chapitre)
        self.assertIn("Notions", resultat["fiche"])
        enregistrees = self.base.lister_contenus(self.chapitre, "fiche")
        self.assertEqual(len(enregistrees), 1)
        self.assertEqual(enregistrees[0]["contenu"], resultat["fiche"])

    def test_le_cours_et_la_structure_sont_envoyes_au_modele(self):
        self.generateur.generer_fiche(self.chapitre)
        demande = self.service.generer.call_args[0][0][0]["content"]
        self.assertIn("La dérivée mesure une pente.", demande)
        self.assertIn("<cours>", demande)
        for titre in ("Notions", "Définitions", "Exemples", "Pièges", "Résumé en 3 lignes"):
            self.assertIn(titre, demande)

    def test_chapitre_inconnu_ou_vide(self):
        for chapitre_id in (999, self.vide):
            with self.subTest(chapitre_id=chapitre_id), self.assertRaises(ErreurService):
                self.generateur.generer_fiche(chapitre_id)
        self.service.generer.assert_not_called()

    def test_reponse_vide_du_modele(self):
        self.service.generer.return_value = ReponseLLM("  ", 1, 1)
        with self.assertRaises(ErreurService):
            self.generateur.generer_fiche(self.chapitre)
        self.assertEqual(self.base.lister_contenus(self.chapitre), [])

    def test_outil_declare_a_l_agent(self):
        boite = creer_outils_coach(self.base)
        noms = [s["function"]["name"] for s in boite.schemas()]
        self.assertIn("generer_fiche", noms)


JSON_OK = '[{"question": "Qu\'est-ce qu\'une dérivée ?", "reponse": "Une pente.", "notion": "Dérivée"}]'


class TestFlashcards(TestFiches):
    def test_lecture_json_valide_et_bloc_markdown(self):
        self.assertEqual(lire_flashcards(JSON_OK)[0]["reponse"], "Une pente.")
        self.assertEqual(len(lire_flashcards("```json\n" + JSON_OK + "\n```")), 1)

    def test_lecture_json_invalide(self):
        for brut in ("pas du json", "{}", "[]", '[{"question": "q"}]', '["texte"]'):
            with self.subTest(brut=brut), self.assertRaises(ValueError):
                lire_flashcards(brut)

    def test_flashcards_enregistrees_avec_notion(self):
        self.service.generer.return_value = ReponseLLM(JSON_OK, 1, 1)
        self.generateur.generer_flashcards(self.chapitre)
        cartes = self.base.lister_contenus(self.chapitre, "flashcard")
        self.assertEqual(len(cartes), 1)
        self.assertEqual(cartes[0]["reponse"], "Une pente.")
        self.assertEqual([n["nom"] for n in self.base.lister_notions(self.chapitre)], ["Dérivée"])
        self.assertIsNotNone(cartes[0]["notion_id"])

    def test_json_mal_forme_relance_une_fois(self):
        self.service.generer.side_effect = [ReponseLLM("oups", 1, 1), ReponseLLM(JSON_OK, 1, 1)]
        self.generateur.generer_flashcards(self.chapitre)
        self.assertEqual(self.service.generer.call_count, 2)
        self.assertEqual(len(self.base.lister_contenus(self.chapitre, "flashcard")), 1)

    def test_json_mal_forme_deux_fois_signale(self):
        self.service.generer.return_value = ReponseLLM("oups", 1, 1)
        with self.assertRaises(ErreurService):
            self.generateur.generer_flashcards(self.chapitre)
        self.assertEqual(self.service.generer.call_count, 2)
        self.assertEqual(self.base.lister_contenus(self.chapitre, "flashcard"), [])

    def test_regenerer_remplace(self):
        self.service.generer.return_value = ReponseLLM(JSON_OK, 1, 1)
        self.generateur.generer_flashcards(self.chapitre)
        self.generateur.generer_flashcards(self.chapitre)
        self.assertEqual(len(self.base.lister_contenus(self.chapitre, "flashcard")), 1)

    def test_outil_declare(self):
        noms = [s["function"]["name"] for s in creer_outils_coach(self.base).schemas()]
        self.assertIn("generer_flashcards", noms)


if __name__ == "__main__":
    unittest.main()
