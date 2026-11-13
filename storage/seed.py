"""Remplit la base avec de fausses données pour tester sans attendre les autres tâches.

Lancement : python -m storage.seed
Attention : supprime la base existante et repart de zéro.
"""
from datetime import date, timedelta

import config
from storage.database import BaseDeDonnees


def dans(jours: int) -> str:
    """Date ISO à J+jours (négatif pour le passé)."""
    return (date.today() + timedelta(days=jours)).isoformat()


def remplir(base: BaseDeDonnees) -> None:
    base.enregistrer_profil(
        prenom="Léa", objectif="Partiels de janvier", niveau_actuel="moyen",
        niveau_vise="bon", echeance=dans(45), minutes_par_jour=60,
        difficultes="Les dérivées et la mémorisation des définitions",
    )

    maths = base.ajouter_matiere("Mathématiques")
    bio = base.ajouter_matiere("Biologie")

    derivees = base.ajouter_chapitre(
        maths, "Dérivées", ordre=1, difficulte=4,
        texte=("La dérivée de f en a est la limite du taux d'accroissement "
               "(f(a+h) - f(a)) / h quand h tend vers 0. "
               "Règles : (u + v)' = u' + v' ; (uv)' = u'v + uv' ; (u/v)' = (u'v - uv') / v². "
               "Dérivées usuelles : (x^n)' = n·x^(n-1) ; (e^x)' = e^x ; (ln x)' = 1/x."),
    )
    base.ajouter_chapitre(
        maths, "Intégrales", ordre=2, difficulte=5,
        texte="Une primitive F de f vérifie F' = f. L'intégrale de a à b de f vaut F(b) - F(a).",
    )
    cellule = base.ajouter_chapitre(
        bio, "La cellule", ordre=1, difficulte=2,
        texte=("La cellule est l'unité de base du vivant. Elle est délimitée par une membrane "
               "plasmique. Les cellules eucaryotes ont un noyau ; les procaryotes n'en ont pas. "
               "La mitochondrie produit l'énergie (ATP) de la cellule."),
    )
    base.ajouter_chapitre(
        bio, "L'ADN", ordre=2, difficulte=3,
        texte="L'ADN est une double hélice formée de nucléotides A, T, C, G. A s'apparie avec T, C avec G.",
    )
    base.ajouter_chapitre(
        bio, "La mitose", ordre=3, difficulte=3,
        texte="La mitose comprend quatre phases : prophase, métaphase, anaphase, télophase.",
    )

    produit = base.ajouter_notion(derivees, "Dérivée d'un produit")
    quotient = base.ajouter_notion(derivees, "Dérivée d'un quotient")
    usuelles = base.ajouter_notion(derivees, "Dérivées usuelles")
    noyau = base.ajouter_notion(cellule, "Eucaryote / procaryote")
    mitochondrie = base.ajouter_notion(cellule, "Rôle de la mitochondrie")

    base.ajouter_objectif(
        "Maîtriser les dérivées", date_limite=dans(20), priorite="haute",
        indicateur="80 % au quiz du chapitre Dérivées", seuil_reussite=0.8,
        chapitre_id=derivees, matiere_id=maths, difficulte=4,
    )
    base.ajouter_objectif(
        "Connaître la structure de la cellule", date_limite=dans(30),
        indicateur="70 % au quiz du chapitre La cellule", seuil_reussite=0.7,
        chapitre_id=cellule, matiere_id=bio, difficulte=2,
    )

    # Deux quiz déjà faits, avec le détail des réponses
    quiz1 = base.ajouter_seance("quiz", derivees, date_prevue=dans(-3))
    for question, notion, juste in [
        ("Dérivée de x³ ?", usuelles, True),
        ("Dérivée de x·e^x ?", produit, False),
        ("Dérivée de 1/x ?", quotient, False),
        ("Dérivée de ln x ?", usuelles, True),
    ]:
        base.enregistrer_reponse(quiz1, question, juste, notion)
    base.terminer_seance(quiz1, score=2, score_max=4, duree_minutes=15)

    quiz2 = base.ajouter_seance("quiz", cellule, date_prevue=dans(-1))
    for question, notion, juste in [
        ("Une bactérie a-t-elle un noyau ?", noyau, True),
        ("Que produit la mitochondrie ?", mitochondrie, True),
        ("Qu'est-ce qu'une cellule eucaryote ?", noyau, False),
    ]:
        base.enregistrer_reponse(quiz2, question, juste, notion)
    base.terminer_seance(quiz2, score=2, score_max=3, duree_minutes=10)

    # Deux séances à venir
    base.ajouter_seance("flashcards", derivees, date_prevue=dans(1))
    base.ajouter_seance("quiz", cellule, date_prevue=dans(2))


if __name__ == "__main__":
    config.DB_PATH.unlink(missing_ok=True)  # repart d'une base vide
    base = BaseDeDonnees()
    remplir(base)
    print(f"Base remplie : {base.chemin}")
    print(f"- {len(base.lister_matieres())} matières, {len(base.lister_chapitres())} chapitres")
    print(f"- {len(base.lister_objectifs())} objectifs, {len(base.lister_seances())} séances")