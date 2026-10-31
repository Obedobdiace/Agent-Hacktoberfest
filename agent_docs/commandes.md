# Commandes du Projet

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env pour ajouter votre clé API Google
# GOOGLE_API_KEY=votre_clé_ici
```

## Lancement de l'Agent

```bash
# Lancer l'agent en mode normal
python -m agent.core.orchestrator

# Lancer en mode lecture seule (aucune action exécutée)
python -m agent.core.orchestrator --readonly
```

## Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Lancer un fichier de test spécifique
pytest tests/test_security.py -v

# Lancer les tests avec couverture
pytest tests/ --cov=agent --cov-report=html
```

## Vérification du Code

```bash
# Vérification des types avec mypy
mypy agent/ --strict

# Linting avec ruff
ruff check agent/

# Formatage automatique avec ruff
ruff format agent/
```

## Base de Données

```bash
# La base de données est créée automatiquement au premier lancement
# Fichier par défaut: ./agent.db

# Pour spécifier un autre chemin, modifier DB_PATH dans .env
```

## Obsidian

```bash
# Configurer le chemin vers votre vault Obsidian dans .env
# OBSIDIAN_VAULT_PATH=C:/Users/YourName/Obsidian/Vault

# Les notes seront créées automatiquement dans:
# vault/Sessions/
# vault/Tâches/
# vault/Erreurs/
# vault/KB/
# vault/Recherches/
```

## Dépannage

```bash
# Vérifier que les dépendances sont installées
pip list | grep -E "google|pyautogui|easyocr|mss"

# Tester l'API Gemini
python test_gemini.py

# Vérifier la configuration
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('API Key:', os.getenv('GOOGLE_API_KEY')[:20] + '...' if os.getenv('GOOGLE_API_KEY') else 'Non trouvée')"
```

## Nettoyage

```bash
# Supprimer la base de données
rm agent.db

# Supprimer les captures d'écran
rm -rf captures/

# Réinitialiser le projet (attention: supprime tout)
rm -rf agent.db captures/ __pycache__/
```

## Logs

```bash
# Les logs sont affichés dans la console
# Pour changer le niveau de logging, modifier LOG_LEVEL dans .env
# Options: DEBUG, INFO, WARNING, ERROR
```

# 1. Activer l'environnement virtuel (selon celui que vous utilisez)
.\venv\Scripts\activate
# OU .\venv\Scripts\activate si le premier ne marche pas

# 2. Lancer le serveur API
python -m agent.api.server

# 1. Se déplacer dans le dossier frontend
cd frontend

# 2. Installer les dépendances (si ce n'est pas déjà fait)
npm install

# 3. Lancer l'interface (Vite + Electron)
npm run dev:electron
