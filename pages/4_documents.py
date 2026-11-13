import streamlit as st

from storage.database import BaseDeDonnees


@st.cache_resource
def obtenir_base() -> BaseDeDonnees:
    return BaseDeDonnees()


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
