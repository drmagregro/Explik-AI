import time

import streamlit as st

from coach.contenus import GenerateurContenus
from services.erreurs import ErreurService
from storage.database import BaseDeDonnees


@st.cache_resource
def obtenir_base() -> BaseDeDonnees:
    return BaseDeDonnees()


@st.cache_resource
def obtenir_generateur() -> GenerateurContenus:
    return GenerateurContenus(base=obtenir_base())


def demarrer_revision(chapitre_id: int, cartes: list[dict]) -> None:
    seance = base.ajouter_seance("flashcards", chapitre_id)
    st.session_state[f"rev_{chapitre_id}"] = {
        "seance": seance, "cartes": cartes, "i": 0, "retourne": False, "ok": 0,
        "debut": time.perf_counter(),
    }


def retourner(cle: str) -> None:
    st.session_state[cle]["retourne"] = True


def repondre(cle: str, savait: bool) -> None:
    """Enregistre la réponse (c'est ce qui alimente le suivi des notions) et passe à la carte suivante."""
    rev = st.session_state[cle]
    carte = rev["cartes"][rev["i"]]
    base.enregistrer_reponse(rev["seance"], carte["contenu"], savait, carte["notion_id"])
    rev["ok"] += savait
    rev["i"] += 1
    rev["retourne"] = False
    if rev["i"] == len(rev["cartes"]):
        minutes = max(1, round((time.perf_counter() - rev["debut"]) / 60))
        base.terminer_seance(rev["seance"], rev["ok"], len(rev["cartes"]), minutes)


def afficher_revision(chapitre_id: int, cartes: list[dict]) -> None:
    cle = f"rev_{chapitre_id}"
    rev = st.session_state.get(cle)
    if rev is None:
        st.button(f"Réviser les {len(cartes)} cartes", key=f"go_{chapitre_id}",
                  on_click=demarrer_revision, args=(chapitre_id, cartes))
        return
    total = len(rev["cartes"])
    if rev["i"] >= total:
        st.success(f"Séance terminée : {rev['ok']} / {total} cartes sues.")
        st.button("Recommencer", key=f"fin_{chapitre_id}", on_click=st.session_state.pop, args=(cle,))
        return
    carte = rev["cartes"][rev["i"]]
    st.progress(rev["i"] / total, text=f"Carte {rev['i'] + 1} sur {total}")
    st.markdown(f"**{carte['contenu']}**")
    if not rev["retourne"]:
        st.button("Retourner la carte", key=f"ret_{chapitre_id}", on_click=retourner, args=(cle,))
        return
    st.info(carte["reponse"])
    gauche, droite = st.columns(2)
    gauche.button("✅ Je savais", key=f"oui_{chapitre_id}", on_click=repondre, args=(cle, True))
    droite.button("❌ Je ne savais pas", key=f"non_{chapitre_id}", on_click=repondre, args=(cle, False))


st.set_page_config(page_title="Documents", page_icon="📚")
st.title("Documents")
st.write(
    "Tes cours classés par matière et par chapitre. "
    "Bientôt, tu pourras y importer tes PDF et photos de cours."
)

base = obtenir_base()
matieres = base.lister_matieres()

if not matieres:
    st.info("Aucune matière pour l'instant. Lance `python -m storage.seed` pour charger des données de test.")

for matiere in matieres:
    st.subheader(matiere["nom"])
    chapitres = base.lister_chapitres(matiere["id"])
    if not chapitres:
        st.caption("Aucun chapitre dans cette matière.")
        continue
    # On n'affiche pas le texte du cours : trop long pour un tableau
    st.dataframe(
        [{"Chapitre": c["titre"], "Difficulté (1 à 5)": c["difficulte"]} for c in chapitres],
        hide_index=True,
    )

    # --- Fiches de révision ---
    for chapitre in chapitres:
        fiches = base.lister_contenus(chapitre["id"], "fiche")
        with st.expander(f"Fiche : {chapitre['titre']}" + (" ✅" if fiches else "")):
            if st.button("Régénérer la fiche" if fiches else "Générer la fiche",
                         key=f"fiche_{chapitre['id']}"):
                with st.spinner("Génération en cours…"):
                    try:
                        obtenir_generateur().generer_fiche(chapitre["id"])
                        st.rerun()
                    except ErreurService as erreur:
                        st.error(str(erreur))
            if fiches:
                st.caption("Générée par une IA à partir de ton cours : relis-la avant de t'y fier.")
                st.markdown(fiches[0]["contenu"])

    # --- Flashcards ---
    for chapitre in chapitres:
        cartes = base.lister_contenus(chapitre["id"], "flashcard")
        with st.expander(f"Flashcards : {chapitre['titre']}" + (f" ({len(cartes)})" if cartes else "")):
            if st.button("Régénérer les flashcards" if cartes else "Générer les flashcards",
                         key=f"cartes_{chapitre['id']}"):
                with st.spinner("Génération en cours…"):
                    try:
                        obtenir_generateur().generer_flashcards(chapitre["id"])
                        st.session_state.pop(f"rev_{chapitre['id']}", None)
                        st.rerun()
                    except ErreurService as erreur:
                        st.error(str(erreur))
            if cartes:
                st.caption("Générées par une IA à partir de ton cours : relis-les avant de t'y fier.")
                afficher_revision(chapitre["id"], cartes)
