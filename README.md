# Explik-AI

## Base de données

Le coach garde en mémoire tout ce qui doit survivre à la fermeture de l'application
(profil de l'élève, matières, chapitres, notions, objectifs, séances de révision et
réponses aux quiz) dans une base **SQLite** : un simple fichier, `data/coach.db`,
sans serveur à installer, grâce au module `sqlite3` inclus dans Python.

- **Création automatique** : la base et ses tables sont créées au premier lancement,
  à partir du plan décrit dans `storage/schema.sql`. Rien à faire à la main.
- **Un seul point d'accès** : toutes les lectures et écritures passent par la classe
  `BaseDeDonnees` (`storage/database.py`). C'est le seul fichier qui contient du SQL,
  toujours avec des requêtes paramétrées pour se protéger des injections SQL.
- **Suivi des notions ratées** : chaque réponse à chaque question est enregistrée avec
  sa notion. C'est ce qui permet au coach de savoir ce que l'élève maîtrise ou non,
  et de planifier les révisions en conséquence.
- **Données de test** : `python -m storage.seed` remplit la base avec une élève fictive
  et un historique de révisions, pour tester l'application sans tout saisir à la main.
  Attention, cette commande efface la base existante.
- **Confidentialité** : le dossier `data/` est exclu de Git (`.gitignore`). Les données
  de l'élève restent sur son ordinateur. Ni la voix ni les photos ne sont stockées :
  seul le texte utile au suivi est conservé.

## Mémoire de la conversation

Le modèle n'a aucune mémoire : à chaque appel, on lui renvoie le prompt système (lu depuis `prompts/system.md`) suivi de l'historique. C'est ce qui lui permet de se souvenir, par exemple, d'un prénom donné plus tôt.

**Stratégie retenue : garder les N derniers échanges** (`MAX_ECHANGES_HISTORIQUE = 10` dans `config.py`, soit 20 messages). L'historique complet reste affiché dans l'interface, mais seule cette fenêtre est envoyée au modèle (`ServiceLLM.preparer_messages`).

Pourquoi :
- **Coût et quota** : chaque token envoyé est facturé et compte dans les limites du palier gratuit de Groq. Sans plafond, chaque message coûterait plus cher que le précédent.
- **Simplicité et fiabilité** : une fenêtre glissante est prévisible et sans appel supplémentaire. Résumer les anciens échanges demanderait un second appel au modèle et risquerait de perdre ou déformer des détails.
- **Suffisant pour une séance de révision** : 10 échanges couvrent le contexte utile d'une discussion.

Limite : au-delà de 10 échanges, les plus anciens sont oubliés (un prénom donné au tout début peut disparaître). Pour une mémoire plus longue, on pourrait résumer les anciens échanges dans un message.

**Si l'historique dépassait la fenêtre de contexte du modèle**, l'API renverrait une erreur (contexte trop long) ou tronquerait l'entrée, et le modèle perdrait le début de la conversation sans prévenir. La fenêtre glissante évite ce cas, et `MAX_TOKENS` plafonne aussi la longueur des réponses.
# Explik-AI — Coach de révision

Explik-AI est un assistant de révision qui s'utilise comme ChatGPT : on lui écrit, il répond en gardant le fil de la conversation. À terme, il pourra aussi écouter, parler, lire une photo de cours et agir grâce à plusieurs agents spécialisés (lecture de cours, quiz, suivi du planning).

Projet étudiant réalisé à 4 dans le cadre du cours DIA3, en deux parties :

1. **Assistant multimodal** : texte, voix (dictée et lecture à voix haute) et images.
2. **Multi-agent** : un orchestrateur qui délègue à des agents Lecture, Quiz et Suivi, avec validation humaine des actions sensibles et export vers Anki.

## Ce qui fonctionne aujourd'hui

| Fonctionnalité | État |
|---|---|
| Chat texte avec historique de conversation | ✅ |
| Réponses affichées au fil de l'eau (streaming) | ✅ |
| Bouton « Nouvelle conversation » | ✅ |
| Prompt système et gestion des longues conversations | 🔜 |
| Image (vision), dictée (STT), réponse vocale (TTS) | 🔜 |
| Agents Lecture, Quiz, Suivi et orchestrateur | 🔜 |

---

## Installation

### Prérequis

- **Python 3.11 ou plus récent** (vérifier avec `python3 --version`)
- **Une clé API Groq**, gratuite : [console.groq.com/keys](https://console.groq.com/keys)
  > Attention : **Groq**, pas Grok (xAI).

### 1. Récupérer le projet

```bash
git clone https://github.com/drmagregro/Explik-AI.git
cd Explik-AI
```

### 2. Créer l'environnement virtuel et installer les dépendances

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurer la clé API

```bash
cp .env.example .env
```

Ouvre `.env` et colle ta clé après `GROQ_API_KEY=`.

Le fichier `.env` est ignoré par Git : ta clé ne part jamais sur GitHub. Si une clé est poussée par erreur, **révoque-la** sur la console Groq. La supprimer du dépôt ne suffit pas, elle reste dans l'historique.

Si la clé manque, l'application s'arrête au lancement avec un message qui explique quoi faire.

### 4. Lancer l'application

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur, sur `http://localhost:8501`.

---

## Utilisation

1. Écris ta question dans le champ en bas de la page, puis appuie sur Entrée.
2. La réponse s'écrit au fur et à mesure.
3. Tu peux enchaîner les questions : le coach garde le fil de la conversation.
4. Pour repartir de zéro, clique sur **Nouvelle conversation** dans la barre latérale.

Pour tester le service LLM seul, sans interface :

```bash
python -m services.llm
```

### ⚠️ Données et confidentialité

Tes messages sont envoyés à **Groq** pour générer les réponses. N'y mets pas d'informations personnelles sensibles. L'application ne stocke pas tes conversations : l'historique est effacé quand tu fermes l'onglet ou cliques sur « Nouvelle conversation ».

---

## Architecture

Règle centrale : **l'interface ne parle jamais directement aux API**. Seuls les fichiers de `services/` appellent les providers. Changer de provider ou de modèle ne touche donc que `services/` et `config.py`.

```
Explik-AI/
├── app.py              Interface Streamlit (chat), aucun appel API direct
├── config.py           Modèle, paramètres, lecture des clés depuis .env
├── services/
│   └── llm.py          Seul point d'accès au modèle de texte (Groq)
├── requirements.txt
└── .env.example        Modèle du fichier .env (sans valeurs)
```

Dossiers prévus pour la suite : `pages/`, `agents/`, `tools/`, `coach/`, `storage/`, `prompts/`, `docs/`.

## Choix techniques

| Choix | Raison |
|---|---|
| **Groq** comme provider | Très rapide, palier gratuit, API compatible OpenAI |
| **Modèle `openai/gpt-oss-120b`** | Bonne qualité en français ; `reasoning_effort="low"` pour limiter la latence |
| **`temperature = 0`** | Réponses stables et reproductibles, adaptées à un coach qui explique des notions |
| **`max_completion_tokens = 1024`** | Plafonne la longueur des réponses et la consommation du palier gratuit |
| **Service sans état** | `ServiceLLM` reçoit toute la conversation à chaque appel : le modèle n'a pas de mémoire propre |
| **Streaming** | `generer_stream()` renvoie la réponse morceau par morceau ; `st.write_stream` l'affiche et renvoie le texte complet, qui seul est ajouté à l'historique |
| **Historique dans `st.session_state`** | Streamlit ré-exécute tout le script à chaque interaction ; `session_state` est ce qui survit entre deux exécutions |

---

## Contribuer (équipe)

### Règles du projet

- `app.py` et `pages/` n'importent jamais `groq`, `openai` ou `together`. Ils passent uniquement par `services/`, `agents/` ou `coach/`.
- Noms de modèles et clés : **uniquement** dans `config.py` et `.env`.
- Les prompts vivent dans `prompts/*.md`, jamais dans une chaîne Python.
- `data/` (cours, voix, photos) ne doit jamais être commité.

### Workflow Git

```
main                 version stable, démontrable
dev                  intégration, doit toujours tourner
feature/<nom>        une branche par fonctionnalité, créée depuis dev
```

1. Créer sa branche depuis `dev` à jour :
   ```bash
   git checkout dev && git pull && git checkout -b feature/<nom>
   ```
2. Faire des petits commits, avec le format `feature: …` ou `fix: …`.
3. Récupérer `dev` chaque jour (`git pull origin dev`) pour voir les conflits tôt.
4. Quand la validation de l'étape passe, ouvrir une Pull Request vers `dev`, relue par un autre membre.
5. Merger le jour même : une branche qui vit plus de 3 jours devient une source de conflits.

## Licence

Voir [LICENSE](LICENSE).
