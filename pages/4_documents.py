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
