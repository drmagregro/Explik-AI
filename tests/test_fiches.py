"""Tests de la génération de fiches. Lancer : python -m unittest tests.test_fiches -v"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("GROQ_API_KEY", "gsk_cle_de_test")

from coach.contenus import GenerateurContenus
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


if __name__ == "__main__":
    unittest.main()
