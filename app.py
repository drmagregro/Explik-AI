import streamlit as st

import config

from agents.orchestrateur import Orchestrateur
from services.erreurs import ErreurService
from services.images import ServiceImage
from services.llm import ServiceLLM
from services.stt import ServiceSTT


@st.cache_resource
def obtenir_service_llm() -> ServiceLLM:
    return ServiceLLM()


@st.cache_resource
def obtenir_service_vision() -> ServiceLLM:
    return ServiceLLM.vision()


@st.cache_resource
def obtenir_service_stt() -> ServiceSTT:
    return ServiceSTT()


@st.cache_resource
def obtenir_orchestrateur() -> Orchestrateur:
    return Orchestrateur(obtenir_service_llm())


class InterfaceChat:

    CLE_HISTORIQUE = "messages"

    def __init__(self, orchestrateur: Orchestrateur, service_vision: ServiceLLM,
                 service_image: ServiceImage, service_stt: ServiceSTT):
        self.service_stt = service_stt
        self.orchestrateur = orchestrateur
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
        if message.get("agents"):
            st.caption("🤖 " + ", ".join(message["agents"]))
        st.markdown(message["content"])

    def _transcrire(self, audio) -> str | None:
        """Transcrit l'audio du micro. Renvoie None (et affiche l'erreur) en cas d'échec."""
        with st.spinner("Transcription en cours…"):
            try:
                return self.service_stt.transcrire(audio.getvalue(), nom_fichier=audio.name).texte
            except ErreurService as erreur:
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
            except ErreurService as erreur:
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

        with st.chat_message("assistant"):
            try:
                reponse = self._repondre()
            except ErreurService as erreur:
                st.error(str(erreur))
                # on retire la question restée sans réponse : l'utilisateur peut la renvoyer
                self.historique.pop()
                return

        self.historique.append(reponse)

    def _repondre(self) -> dict:
        """Affiche la réponse du coach et la renvoie, prête à entrer dans l'historique.

        Avec une image : le modèle vision, en streaming (l'agent Lecture ne lit pas encore les photos).
        Sinon : l'orchestrateur, qui répond lui-même ou délègue à un agent. Sa réponse arrive
        d'un bloc, après la boucle des agents, donc sans streaming.
        """
        if self._contient_image():
            # write_stream affiche les morceaux au fil de l'eau et renvoie le texte complet
            texte = st.write_stream(self.service_vision.generer_stream(self._messages_pour_api()))
            return {"role": "assistant", "content": texte}

        with st.spinner("Le coach réfléchit…"):
            resultat = self.orchestrateur.run(self._messages_pour_api())
        # demander_agent_quiz -> Quiz : on garde seulement les agents, pas leurs outils internes
        agents = [appel.nom.removeprefix("demander_agent_").capitalize() for appel in resultat.appels]
        reponse = {"role": "assistant", "content": resultat.texte, "agents": agents}
        self._afficher_texte(reponse)
        return reponse

    def lancer(self) -> None:
        self.afficher_barre_laterale()
        self.afficher_historique()
        self.traiter_saisie()


st.set_page_config(page_title="Coach de révision", page_icon="🎓")
InterfaceChat(obtenir_orchestrateur(), obtenir_service_vision(), ServiceImage(),
              obtenir_service_stt()).lancer()