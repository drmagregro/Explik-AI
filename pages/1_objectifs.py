import streamlit as st

from storage.database import BaseDeDonnees


@st.cache_resource
def obtenir_base() -> BaseDeDonnees:
    return BaseDeDonnees()


# Libellés lisibles pour les valeurs stockées en base
STATUTS = {
    "a_commencer": "À commencer",
    "en_cours": "En cours",
    "maitrise": "Maîtrisé",
    "a_revoir": "À revoir",
}


st.set_page_config(page_title="Objectifs", page_icon="🎯")
st.title("Objectifs")
st.write(
    "Ton profil et tes objectifs de révision. "
    "Bientôt, tu pourras y ajouter tes propres objectifs et suivre ta progression."
)

base = obtenir_base()

st.header("Mon profil")
profil = base.obtenir_profil()

if profil is None:
    st.info("Aucun profil pour l'instant. Lance `python -m storage.seed` pour charger des données de test.")
else:
    st.write(f"**{profil['prenom']}** · {profil['objectif']} · échéance le {profil['echeance']}")
    st.write(
        f"Niveau actuel : {profil['niveau_actuel']} → niveau visé : {profil['niveau_vise']} · "
        f"{profil['minutes_par_jour']} min par jour"
    )

st.header("Mes objectifs")
objectifs = base.lister_objectifs()

if not objectifs:
    st.info("Aucun objectif pour l'instant. Lance `python -m storage.seed` pour charger des données de test.")

for objectif in objectifs:
    st.subheader(objectif["intitule"])
    st.write(
        f"Priorité {objectif['priorite']} · "
        f"avant le {objectif['date_limite'] or 'date non fixée'} · "
        f"{STATUTS[objectif['statut']]}"
    )
    if objectif["indicateur"]:
        st.caption(f"Réussi si : {objectif['indicateur']}")
