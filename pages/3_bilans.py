import streamlit as st

from storage.database import BaseDeDonnees


@st.cache_resource
def obtenir_base() -> BaseDeDonnees:
    return BaseDeDonnees()


st.set_page_config(page_title="Bilans", page_icon="📝")
st.title("Bilans")
st.write(
    "Le résultat de tes séances terminées. "
    "Bientôt : bilans rédigés par le coach, pour la séance, la journée et la semaine."
)

base = obtenir_base()
faites = base.lister_seances("faite")

st.subheader("Séances terminées")
if not faites:
    st.info("Aucune séance terminée pour l'instant. Lance `python -m storage.seed` pour charger des données de test.")
else:
    # Le titre du chapitre est plus parlant que son id
    titres = {c["id"]: c["titre"] for c in base.lister_chapitres()}
    st.dataframe(
        [
            {"Date": s["date_prevue"], "Activité": s["activite"],
             "Chapitre": titres.get(s["chapitre_id"], "—"),
             "Score": f"{s['score']:g} / {s['score_max']:g}", "Durée (min)": s["duree_minutes"]}
            for s in faites
        ],
        hide_index=True,
    )
