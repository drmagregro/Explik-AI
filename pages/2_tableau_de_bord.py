import streamlit as st

from storage.database import BaseDeDonnees


@st.cache_resource
def obtenir_base() -> BaseDeDonnees:
    return BaseDeDonnees()


st.set_page_config(page_title="Tableau de bord", page_icon="📊")
st.title("Tableau de bord")
st.write(
    "Ta préparation en un coup d'œil. "
    "Bientôt : progression par chapitre, planning du jour et prochaines répétitions."
)

base = obtenir_base()
chapitres = base.lister_chapitres()
faites = base.lister_seances("faite")
prevues = base.lister_seances("prevue")

col1, col2, col3 = st.columns(3)
col1.metric("Chapitres", len(chapitres))
col2.metric("Séances faites", len(faites))
col3.metric("Séances à venir", len(prevues))

st.subheader("Prochaines séances")
if not prevues:
    st.info("Aucune séance prévue pour l'instant. Lance `python -m storage.seed` pour charger des données de test.")
else:
    # Le titre du chapitre est plus parlant que son id
    titres = {c["id"]: c["titre"] for c in chapitres}
    st.dataframe(
        [
            {"Date": s["date_prevue"], "Activité": s["activite"],
             "Chapitre": titres.get(s["chapitre_id"], "—")}
            for s in prevues
        ],
        hide_index=True,
    )
