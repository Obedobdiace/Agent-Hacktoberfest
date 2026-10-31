# Hacktoberfest

Agent de bureau pour Windows. On lui parle en français, à l’écrit ou au micro, et il agit sur l’ordinateur : ouvrir une application, régler le volume, verrouiller la session, prendre une capture, écrire une note. Les actions sensibles attendent une confirmation.

L’interface est une fenêtre Electron. Le serveur Python tourne en local (`127.0.0.1`) et ne sort du poste que pour appeler le modèle.

## Fonctionnalités

- **Applications installées.** L’agent lit le menu Démarrer, le registre et les chemins d’applications, puis ouvre ou ferme le programme demandé. Ce n’est pas une liste figée.
- **Commandes directes.** Luminosité, volume, lecture multimédia, verrouillage, corbeille et capture d’écran sont traités sans appel au modèle.
- **Voix.** La dictée utilise le reconnaisseur Windows en français. Les réponses sont lues par la synthèse vocale du navigateur. Une barre indique si le micro reçoit du son.
- **Modèle.** Le cerveau par défaut est Gemma (`gemma-4-26b-a4b-it`) via l’API Google. Une clé Gemini reste utilisable pour la vision.
- **Confirmation.** Suppression, commandes système et chemins protégés (`C:\Windows`, clés SSH, etc.) ne partent pas sans accord.
- **Notes Obsidian.** Les sessions, tâches et recherches peuvent être écrites dans un coffre configuré.

## Prérequis

- Windows 10 ou 11
- Python 3.11
- Node.js 20 ou plus récent
- Un micro, si vous utilisez la voix (le micro intégré du PC, pas un casque débranché)
- Une clé API Google pour Gemma

## Installation

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
```

## Configuration

```bash
copy .env.example .env
```

Renseignez `.env` :

| Variable | Rôle |
| --- | --- |
| `LLM_PROVIDER` | `gemma` (défaut) ou `gemini` |
| `GEMMA_API_KEY` | Clé de l’API Gemma |
| `GEMMA_MODEL` | `gemma-4-26b-a4b-it` |
| `GOOGLE_API_KEY` | Clé Gemini, utilisée pour la vision si elle est présente |
| `OBSIDIAN_VAULT_PATH` | Chemin du coffre Obsidian |
| `READONLY_MODE` | `true` pour refuser toute action |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` ou `ERROR` |

`.env` ne doit pas être commité.

## Lancer

Deux terminaux, depuis la racine du projet.

```bash
venv\Scripts\activate
python -m agent.api.server
```

```bash
cd frontend
npm run dev:electron
```

Le serveur écoute `http://127.0.0.1:8000`. L’interface se connecte en WebSocket. Le bouton micro démarre une écoute ; le texte reconnu apparaît sous « vous dites », puis part comme un message.

## Exemples

- « Ouvre Spotify »
- « Ferme le bloc-notes »
- « Baisse le volume »
- « Verrouille la session »
- « Prends une capture d’écran »

Une demande d’ouverture ou de fermeture d’application est exécutée tout de suite. Le modèle n’intervient que lorsque la phrase n’est pas une commande reconnue.

## Architecture

```
agent/
  api/            serveur FastAPI et WebSocket
  core/           orchestration, commandes rapides, sécurité, mémoire
  actions/        applications, souris, clavier, fichiers
  voice/          reconnaissance Windows (français)
  vision/         capture d’écran et analyse
  obsidian/       notes dans le coffre
frontend/         interface React + Electron
```

Les commandes simples passent par `fast_parser`. Le catalogue d’applications résout le nom, puis lance le raccourci ou l’exécutable. Le reste est envoyé à Gemma, qui renvoie une action au format JSON.

## Sécurité

L’agent contrôle la souris, le clavier et les applications du poste. Gardez `READONLY_MODE=true` tant que vous explorez le code. Les opérations critiques demandent une validation dans l’interface. Les chemins système et les secrets (`.env`, `.ssh`) sont protégés.

## Tests

```bash
pytest tests/ -v
ruff check agent/actions/app_catalog.py agent/core/llm.py agent/voice/listener.py
```

## Licence

[MIT](LICENSE) — Copyright 2026 Obedobdiace
