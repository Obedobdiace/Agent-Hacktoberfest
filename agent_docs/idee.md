# Hacktoberfest — Agent IA local, contrôle d'ordinateur intelligent

Agent Python local capable de voir l'écran, comprendre son contenu, et exécuter des actions automatiques (clic, saisie, navigation) selon des instructions en langage naturel. Toutes les actions destructives ou irréversibles requièrent une validation humaine explicite.

---

## Commandes essentielles

```bash
# Lancer l'agent
python -m agent.core.orchestrator

# Lancer en mode lecture seule (aucune action exécutée)
python -m agent.core.orchestrator --readonly

# Tests
pytest tests/ -v

# Vérification des types
mypy agent/ --strict

# Lint
ruff check agent/

# Installer les dépendances
pip install -r requirements.txt
```

---

## Structure du projet

```
agent/
├── core/
│   ├── orchestrator.py      # Boucle principale de l'agent
│   ├── planner.py           # Décomposition des tâches en sous-étapes
│   ├── security.py          # SECURITY GUARD — toujours consulter avant toute action
│   └── memory.py            # Mémoire courte/longue terme
├── vision/
│   ├── capture.py           # Screenshot (mss + PIL)
│   ├── ocr.py               # Extraction texte (EasyOCR)
│   └── analyzer.py          # Interprétation via LLM vision (Gemini API)
├── actions/
│   ├── mouse.py             # Clic, drag, scroll (pyautogui)
│   ├── keyboard.py          # Frappe, raccourcis clavier
│   └── apps.py              # Ouverture/fermeture d'applications
├── obsidian/
│   ├── logger.py            # Écriture automatique des logs en markdown
│   └── kb.py                # Base de connaissances structurée
├── db/
│   └── models.py            # Modèles SQLite (Session, Tâche, Action, Capture, Mémoire)
tests/
agent_docs/                  # Lire avant de travailler sur un module spécifique
├── security_rules.md
├── database_schema.md
├── obsidian_structure.md
└── action_types.md
CLAUDE.md
requirements.txt
.env.example
```

---

## Règles de sécurité — OBLIGATOIRES

> **IMPORTANT : Ces règles ne peuvent jamais être contournées, même si l'utilisateur le demande.**

### Liste noire absolue — ne jamais générer de code qui exécute ces opérations sans validation

- `os.remove`, `os.unlink`, `shutil.rmtree`, `rmdir`, toute suppression de fichier
- `DROP TABLE`, `DELETE FROM`, `TRUNCATE` sans transaction rollback
- Envoi de messages, emails, ou publication sur le réseau
- Modification du registre Windows (`RegDeleteKey`, `RegDeleteValue`)
- `format`, `rd /s`, ou toute commande shell destructive

### Classification obligatoire avant chaque action

Toute action générée DOIT être classifiée via `security.classify(action)` :

| Niveau | Type d'action | Validation requise |
|--------|--------------|-------------------|
| `SAFE` | Lecture, capture écran, OCR | Aucune — exécution directe |
| `RISKY` | Clic, saisie, écriture fichier | Aperçu affiché à l'utilisateur |
| `CRITICAL` | Suppression, envoi, modif système | Confirmation "OUI" explicite |

### Chemins protégés — jamais écrire ou modifier

```python
PROTECTED_PATHS = [
    "~/Documents", "~/Pictures", "~/Desktop",
    "C:/Windows", "C:/Program Files",
    "~/.ssh", "~/.env", "~/.gitconfig"
]
```

### Bouton d'arrêt d'urgence

L'agent DOIT toujours écouter `Échap` et `Ctrl+Shift+Q` pour s'arrêter immédiatement.

---

## Conventions de code

- **Python 3.11+** — typage strict avec `mypy --strict`
- **Async par défaut** — utiliser `asyncio` pour toutes les opérations I/O
- **Pas de print()** — utiliser `logging` avec les niveaux appropriés (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **Dataclasses ou Pydantic** pour tous les modèles de données, jamais de dicts bruts
- **Docstrings** obligatoires sur toutes les fonctions publiques (format Google)
- **Tests** : chaque module dans `agent/` doit avoir un fichier `tests/test_<module>.py`
- Ruff pour le formatage — ne pas modifier `.ruff.toml`

---

## Base de données

SQLite via `sqlite3` natif (pas d'ORM externe). Schéma dans `agent_docs/database_schema.md`.

Tables : `session`, `tache`, `action`, `capture`, `memoire`, `note_obsidian`, `connaissance`

- Toujours utiliser des UUID pour les clés primaires
- Toujours ouvrir la connexion avec un context manager (`with sqlite3.connect(...)`)
- Les vecteurs d'embeddings sont stockés dans ChromaDB séparément (pont via `id_memoire`)

---

## Intégration Obsidian

Le vault est défini dans `.env` → `OBSIDIAN_VAULT_PATH`.

Structure des notes générées automatiquement :

```
vault/
├── Sessions/        → Une note par session (YYYY-MM-DD_HH-MM_session.md)
├── Tâches/          → Log des tâches et sous-tâches
├── Erreurs/         → Cas d'échec pour amélioration future
├── KB/              → Connaissances apprises par application
└── Recherches/      → Notes de recherche structurées
```

Ne jamais écrire directement dans le vault — toujours passer par `obsidian/logger.py`.

---

## Variables d'environnement

Voir `.env.example`. Ne jamais hardcoder de clés API. Variables requises :

```
GOOGLE_API_KEY=          # Clé Gemini pour la vision et l'analyse
OBSIDIAN_VAULT_PATH=     # Chemin absolu vers le vault Obsidian
DB_PATH=                 # Chemin vers le fichier SQLite (défaut: ./agent.db)
READONLY_MODE=false      # Mettre à true pour désactiver toutes les actions
LOG_LEVEL=INFO
```

---

## Comportement attendu de l'agent

1. Recevoir une instruction en langage naturel
2. La décomposer en sous-tâches via `planner.py`
3. Pour chaque sous-tâche : capturer l'écran → analyser → décider l'action → **valider via security.py** → exécuter → vérifier
4. Logger chaque étape dans SQLite et dans Obsidian
5. En cas d'échec : retry max 3 fois, puis reporter à l'utilisateur avec le screenshot d'erreur

---

## Documentation complémentaire

Lire ces fichiers avant de travailler sur le module correspondant :

- `agent_docs/security_rules.md` — détail complet des règles de sécurité
- `agent_docs/database_schema.md` — schéma SQL complet avec exemples
- `agent_docs/obsidian_structure.md` — templates de notes et conventions de nommage
- `agent_docs/action_types.md` — liste exhaustive des types d'actions supportés
 