# Schéma de la Base de Données

## Vue d'ensemble

Base de données SQLite avec les tables suivantes :
- `session` — Sessions de l'agent
- `tache` — Tâches et sous-tâches
- `action` — Actions exécutées
- `capture` — Captures d'écran
- `memoire` — Mémoires courte et longue terme
- `note_obsidian` — Notes générées dans Obsidian
- `connaissance` — Connaissances structurées

## Tables

### session

```sql
CREATE TABLE session (
    id TEXT PRIMARY KEY,  -- UUID
    debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fin TIMESTAMP,
    instruction_initiale TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_cours',  -- en_cours, terminee, annulee, erreur
    readonly_mode BOOLEAN DEFAULT 0
);
```

### tache

```sql
CREATE TABLE tache (
    id TEXT PRIMARY KEY,  -- UUID
    id_session TEXT NOT NULL,
    id_parent TEXT,  -- NULL pour tâche principale, UUID pour sous-tâche
    description TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed, failed
    ordre INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (id_session) REFERENCES session(id),
    FOREIGN KEY (id_parent) REFERENCES tache(id)
);
```

### action

```sql
CREATE TABLE action (
    id TEXT PRIMARY KEY,  -- UUID
    id_tache TEXT NOT NULL,
    type_action TEXT NOT NULL,  -- mouse_click, keyboard_type, app_open, etc.
    parametres TEXT NOT NULL,  -- JSON
    security_level TEXT NOT NULL,  -- SAFE, RISKY, CRITICAL
    user_approved BOOLEAN,
    blocked_reason TEXT,
    resultat TEXT,  -- success, failed, blocked
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_tache) REFERENCES tache(id)
);
```

### capture

```sql
CREATE TABLE capture (
    id TEXT PRIMARY KEY,  -- UUID
    id_action TEXT,  -- NULL si capture autonome
    chemin_fichier TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ocr_resultat TEXT,  -- Texte extrait
    FOREIGN KEY (id_action) REFERENCES action(id)
);
```

### memoire

```sql
CREATE TABLE memoire (
    id TEXT PRIMARY KEY,  -- UUID
    id_session TEXT NOT NULL,
    type TEXT NOT NULL,  -- short_term, long_term
    contenu TEXT NOT NULL,
    tags TEXT,  -- JSON array de tags
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    FOREIGN KEY (id_session) REFERENCES session(id)
);
```

### note_obsidian

```sql
CREATE TABLE note_obsidian (
    id TEXT PRIMARY KEY,  -- UUID
    id_session TEXT NOT NULL,
    chemin_fichier TEXT NOT NULL,
    type_note TEXT NOT NULL,  -- session, tache, erreur, recherche
    titre TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_session) REFERENCES session(id)
);
```

### connaissance

```sql
CREATE TABLE connaissance (
    id TEXT PRIMARY KEY,  -- UUID
    application TEXT NOT NULL,  -- ex: "Chrome", "Excel"
    categorie TEXT NOT NULL,  -- ex: "raccourcis", "workflows"
    titre TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    embedding_id TEXT  -- Référence vers ChromaDB
);
```

## Index

```sql
CREATE INDEX idx_tache_session ON tache(id_session);
CREATE INDEX idx_tache_parent ON tache(id_parent);
CREATE INDEX idx_action_tache ON action(id_tache);
CREATE INDEX idx_capture_action ON capture(id_action);
CREATE INDEX idx_memoire_session ON memoire(id_session);
CREATE INDEX idx_note_session ON note_obsidian(id_session);
CREATE INDEX idx_connaissance_app ON connaissance(application);
```

## Exemples d'Utilisation

### Créer une session

```python
import sqlite3
import uuid

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO session (id, instruction_initiale) VALUES (?, ?)",
        (session_id, "Ouvrir Chrome et aller sur google.com")
    )
    conn.commit()
```

### Logger une action

```python
import json

action_id = str(uuid.uuid4())
cursor.execute(
    """INSERT INTO action 
       (id, id_tache, type_action, parametres, security_level, user_approved, resultat)
       VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (
        action_id,
        task_id,
        "mouse_click",
        json.dumps({"x": 500, "y": 300, "button": "left"}),
        "RISKY",
        True,
        "success"
    )
)
```

### Récupérer les tâches d'une session

```python
cursor.execute(
    "SELECT * FROM tache WHERE id_session = ? ORDER BY ordre",
    (session_id,)
)
tasks = cursor.fetchall()
```
