import streamlit as st

from services.llm import ServiceLLM


@st.cache_resource
def obtenir_service_llm() -> ServiceLLM:
    return ServiceLLM()


class InterfaceChat:

    CLE_HISTORIQUE = "messages"

    def __init__(self, service: ServiceLLM):
        self.service = service
        # Crée l'historique au tout premier chargement uniquement
        if self.CLE_HISTORIQUE not in st.session_state:
            st.session_state[self.CLE_HISTORIQUE] = []

    @property
    def historique(self) -> list[dict]:
        """La conversation en cours, stockée dans la mémoire de Streamlit."""
        return st.session_state[self.CLE_HISTORIQUE]

    def afficher_barre_laterale(self) -> None:
        with st.sidebar:
            st.title("Coach de révision")
            if st.button("Nouvelle conversation", width="stretch"):
                st.session_state[self.CLE_HISTORIQUE] = []
                st.rerun()

    def afficher_historique(self) -> None:
        for message in self.historique:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    def traiter_saisie(self) -> None:
        question = st.chat_input("Pose ta question…")
        if not question:
            return

        self.historique.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            # write_stream affiche les morceaux au fil de l'eau et renvoie le texte complet
            texte = st.write_stream(self.service.generer_stream(self.historique))

        self.historique.append({"role": "assistant", "content": texte})

    def lancer(self) -> None:
        self.afficher_barre_laterale()
        self.afficher_historique()
        self.traiter_saisie()


st.set_page_config(page_title="Coach de révision", page_icon="🎓")
InterfaceChat(obtenir_service_llm()).lancer()