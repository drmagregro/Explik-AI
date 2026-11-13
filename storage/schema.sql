CREATE TABLE IF NOT EXISTS profil (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    prenom          TEXT,
    objectif        TEXT,              
    niveau_actuel   TEXT,
    niveau_vise     TEXT,
    echeance        TEXT,              
    minutes_par_jour INTEGER,
    difficultes     TEXT,
    rgpd_accepte    INTEGER NOT NULL DEFAULT 0,   -- 0 = non, 1 = oui
    cree_le         TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS matieres (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nom  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS chapitres (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    matiere_id  INTEGER NOT NULL REFERENCES matieres(id) ON DELETE CASCADE,
    titre       TEXT NOT NULL,
    ordre       INTEGER NOT NULL DEFAULT 0,
    difficulte  INTEGER NOT NULL DEFAULT 3 CHECK (difficulte BETWEEN 1 AND 5),
    texte       TEXT NOT NULL DEFAULT ''     
);


CREATE TABLE IF NOT EXISTS notions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chapitre_id INTEGER NOT NULL REFERENCES chapitres(id) ON DELETE CASCADE,
    nom         TEXT NOT NULL,
    UNIQUE (chapitre_id, nom)
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    chapitre_id   INTEGER REFERENCES chapitres(id) ON DELETE SET NULL,
    nom_fichier   TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('cours', 'photo', 'notes', 'annale')),
    texte_extrait TEXT NOT NULL DEFAULT '',
    importe_le    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS objectifs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    intitule           TEXT NOT NULL,
    matiere_id         INTEGER REFERENCES matieres(id) ON DELETE SET NULL,
    chapitre_id        INTEGER REFERENCES chapitres(id) ON DELETE SET NULL,
    priorite           TEXT NOT NULL DEFAULT 'moyenne' CHECK (priorite IN ('haute', 'moyenne', 'basse')),
    date_limite        TEXT,
    indicateur         TEXT,                  -- « 80 % au quiz du chapitre 4 »
    seuil_reussite     REAL,                  -- 0.8 pour 80 %
    difficulte         INTEGER CHECK (difficulte BETWEEN 1 AND 5),
    statut             TEXT NOT NULL DEFAULT 'a_commencer'
                       CHECK (statut IN ('a_commencer', 'en_cours', 'maitrise', 'a_revoir')),
    prochaines_actions TEXT,
    cree_le            TEXT NOT NULL DEFAULT (date('now'))
);

-- Fiches et flashcards générées
CREATE TABLE IF NOT EXISTS contenus (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chapitre_id INTEGER NOT NULL REFERENCES chapitres(id) ON DELETE CASCADE,
    notion_id   INTEGER REFERENCES notions(id) ON DELETE SET NULL,
    type        TEXT NOT NULL CHECK (type IN ('fiche', 'flashcard')),
    titre       TEXT,
    contenu     TEXT NOT NULL,     -- texte de la fiche, ou question de la flashcard
    reponse     TEXT,              -- réponse de la flashcard (vide pour une fiche)
    cree_le     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Une séance = un moment de révision, prévu ou réalisé
CREATE TABLE IF NOT EXISTS seances (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    chapitre_id    INTEGER REFERENCES chapitres(id) ON DELETE SET NULL,
    activite       TEXT NOT NULL CHECK (activite IN ('quiz', 'quiz_oral', 'flashcards', 'fiche', 'examen', 'lecture')),
    date_prevue    TEXT,
    statut         TEXT NOT NULL DEFAULT 'prevue' CHECK (statut IN ('prevue', 'faite', 'manquee')),
    duree_minutes  INTEGER,
    score          REAL,         
    score_max      REAL,          
    methode        TEXT,          -- Feynman, récupération active… (tâches 54-55)
    terminee_le    TEXT
);

-- Le détail question par question : c'est ce qui permet de suivre les notions ratées
CREATE TABLE IF NOT EXISTS reponses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    seance_id  INTEGER NOT NULL REFERENCES seances(id) ON DELETE CASCADE,
    notion_id  INTEGER REFERENCES notions(id) ON DELETE SET NULL,
    question   TEXT NOT NULL,
    correcte   INTEGER NOT NULL CHECK (correcte IN (0, 1)),
    repondu_le TEXT NOT NULL DEFAULT (datetime('now'))
);

-- État de la répétition espacée de chaque notion (rempli par la tâche 29)
CREATE TABLE IF NOT EXISTS repetitions (
    notion_id        INTEGER PRIMARY KEY REFERENCES notions(id) ON DELETE CASCADE,
    intervalle_jours INTEGER NOT NULL DEFAULT 1,
    facilite         REAL NOT NULL DEFAULT 2.5,
    prochaine_date   TEXT NOT NULL DEFAULT (date('now')),
    nb_reussites     INTEGER NOT NULL DEFAULT 0
);