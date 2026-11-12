import streamlit as st

import config

from services.images import ImageInvalide, ServiceImage
from services.llm import ServiceLLM
from services.stt import ErreurTranscription, ServiceSTT


@st.cache_resource
def obtenir_service_llm() -> ServiceLLM:
    return ServiceLLM()


@st.cache_resource
def obtenir_service_vision() -> ServiceLLM:
    return ServiceLLM.vision()


@st.cache_resource
def obtenir_service_stt() -> ServiceSTT:
    return ServiceSTT()


class InterfaceChat:

    CLE_HISTORIQUE = "messages"

    def __init__(self, service_texte: ServiceLLM, service_vision: ServiceLLM,
                 service_image: ServiceImage, service_stt: ServiceSTT):
        self.service_stt = service_stt
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
                self._afficher_texte(message)

    @staticmethod
    def _afficher_texte(message: dict) -> None:
        """Signale un message dicté pour que l'utilisateur voie ce qui a été compris."""
        if message.get("vocal"):
            st.caption("🎤 Message dicté, transcription automatique :")
        st.markdown(message["content"])

    def _transcrire(self, audio) -> str | None:
        """Transcrit l'audio du micro. Renvoie None (et affiche l'erreur) en cas d'échec."""
        with st.spinner("Transcription en cours…"):
            try:
                return self.service_stt.transcrire(audio.getvalue(), nom_fichier=audio.name).texte
            except ErreurTranscription as erreur:
                st.error(str(erreur))
                return None

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
            "Pose ta question, joins une photo ou dicte avec le micro…",
            accept_file=True,
            file_type=ServiceImage.FORMATS_ACCEPTES,
            accept_audio=True,
            audio_sample_rate=config.AUDIO_FREQUENCE_HZ,
        )
        if not saisie:
            return

        # Message vocal : on le transcrit, puis il est traité comme un message écrit
        vocal = saisie.audio is not None
        if vocal:
            question = self._transcrire(saisie.audio)
            if question is None:
                return
            if saisie.text:
                question = f"{saisie.text}\n\n{question}"
        else:
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
        if vocal:
            message["vocal"] = True
        self.historique.append(message)

        with st.chat_message("user"):
            if image:
                st.image(image, width=300)
            self._afficher_texte(message)

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
InterfaceChat(obtenir_service_llm(), obtenir_service_vision(), ServiceImage(),
              obtenir_service_stt()).lancer()