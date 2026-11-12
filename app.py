import streamlit as st

from services.images import ImageInvalide, ServiceImage
from services.llm import ServiceLLM


@st.cache_resource
def obtenir_service_llm() -> ServiceLLM:
    return ServiceLLM()


@st.cache_resource
def obtenir_service_vision() -> ServiceLLM:
    return ServiceLLM.vision()


class InterfaceChat:

    CLE_HISTORIQUE = "messages"

    def __init__(self, service_texte: ServiceLLM, service_vision: ServiceLLM,
                 service_image: ServiceImage):
        self.service_texte = service_texte
        self.service_vision = service_vision
        self.service_image = service_image
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
                if message.get("image"):
                    st.image(message["image"], width=300)
                st.markdown(message["content"])

    def _contient_image(self) -> bool:
        return any(message.get("image") for message in self.historique)

    def _messages_pour_api(self) -> list[dict]:
        """Traduit l'historique au format de l'API, en n'envoyant que la dernière image."""
        indices_images = [i for i, m in enumerate(self.historique) if m.get("image")]
        derniere_image = indices_images[-1] if indices_images else None

        messages = []
        for i, message in enumerate(self.historique):
            if i == derniere_image:
                contenu = [
                    {"type": "text", "text": message["content"]},
                    {"type": "image_url",
                     "image_url": {"url": ServiceImage.vers_data_url(message["image"])}},
                ]
            elif message.get("image"):
                contenu = message["content"] + "\n[Une image avait été jointe à ce message.]"
            else:
                contenu = message["content"]
            messages.append({"role": message["role"], "content": contenu})
        return messages

    def traiter_saisie(self) -> None:
        saisie = st.chat_input(
            "Pose ta question ou joins une photo…",
            accept_file=True,
            file_type=ServiceImage.FORMATS_ACCEPTES,
        )
        if not saisie:
            return

        question = saisie.text or "Décris cette image."
        image = None
        if saisie.files:
            try:
                image = self.service_image.preparer(saisie.files[0].getvalue())
            except ImageInvalide as erreur:
                st.error(str(erreur))
                return

        message = {"role": "user", "content": question}
        if image:
            message["image"] = image
        self.historique.append(message)

        with st.chat_message("user"):
            if image:
                st.image(image, width=300)
            st.markdown(question)

        service = self.service_vision if self._contient_image() else self.service_texte
        with st.chat_message("assistant"):
            # write_stream affiche les morceaux au fil de l'eau et renvoie le texte complet
            texte = st.write_stream(service.generer_stream(self._messages_pour_api()))

        self.historique.append({"role": "assistant", "content": texte})

    def lancer(self) -> None:
        self.afficher_barre_laterale()
        self.afficher_historique()
        self.traiter_saisie()


st.set_page_config(page_title="Coach de révision", page_icon="🎓")
InterfaceChat(obtenir_service_llm(), obtenir_service_vision(), ServiceImage()).lancer()