# Hacktoberfest

## 📌 Vue d'ensemble du Projet
Hacktoberfest est un agent d'assistance de bureau autonome et intelligent. Il est conçu pour interagir avec le système d'exploitation (Windows) à l'aide d'instructions en langage naturel, en orchestrant la vision par ordinateur, la compréhension LLM (Gemini) et les actions directes du système (souris, clavier, fichiers, terminaux).

---

## 🏗️ Architecture Actuelle

Le projet est divisé en deux parties principales : un backend en Python et un frontend sous React/Electron.

### 1. Backend (Python)
Gère l'intelligence, la communication avec le système, et le traitement des requêtes.
*   **`agent/api/`** : Serveur FastAPI (`server.py`) exposant des WebSockets pour une communication temps réel avec le frontend.
*   **`agent/core/`** : Le cerveau de l'agent.
    *   `orchestrator.py` : Coordonne la boucle de raisonnement et d'action (ReAct).
    *   `fast_parser.py` : Analyseur rapide pour extraire les intentions et applications (évite des appels LLM inutiles).
    *   `planner.py` : Planifie les séquences d'actions complexes.
    *   `memory.py` : Gestion de la mémoire à l'aide de ChromaDB (base de données vectorielle).
    *   `security.py` : Système de "Human-in-the-loop" pour demander confirmation à l'utilisateur avant d'exécuter des actions critiques.
*   **`agent/actions/`** : Outils d'interaction concrets.
    *   `apps.py`, `filesystem.py`, `keyboard.py`, `mouse.py`, `search.py` : Exécutent les clics, les frappes, gèrent les fenêtres et manipulent les fichiers (PowerShell / PyAutoGUI).
*   **`agent/vision/`** : Traitement visuel de l'écran à l'aide de `mss` (capture) et `easyocr` (reconnaissance de texte) / Pillow.
*   **`agent/obsidian/`** : Module spécifique pour interagir avec l'application de prise de notes Obsidian.

### 2. Frontend (React + Electron)
Interface utilisateur (Overlay) de type "gliding desktop".
*   **`frontend/`** : Projet Vite avec React et Electron.
*   **`src/`** : Composants React pour l'interface de Hacktoberfest, conçue pour être minimaliste et fluide.
*   Permet d'afficher l'état de l'agent, le retour visuel des tâches en cours, et l'interface de chat.

---

## 🚀 Ce qu'il y a déjà (Fonctionnalités clés)
1.  **Exécution d'Actions Autonomes** : Déplacement de la souris, frappe au clavier, et navigation dans le système de fichiers.
2.  **Fast-Track & Parsing** : Compréhension rapide des commandes simples ("ouvre spotify", "écris dans Obsidian") via le `fast_parser.py`.
3.  **Vision par Ordinateur** : Capacité à "voir" l'écran pour cliquer sur les bons éléments.
4.  **Interface Native (Electron)** : Un overlay élégant qui communique de manière fluide avec le backend via WebSockets.
5.  **Sécurité Intégrée** : L'agent demande une autorisation avant les commandes potentiellement dangereuses.
6.  **Mémoire (RAG)** : Utilisation de ChromaDB pour se souvenir des contextes passés et de la configuration du système.

---

## 🛠️ Pistes d'Amélioration (Ce que tu peux améliorer)

Voici les axes principaux d'amélioration pour rendre l'agent encore plus performant et stable :

### 1. Gestion des Quotas et Fallback LLM (Priorité Haute)
*   **Problème observé** : Les logs récents montrent une erreur `429 RESOURCE_EXHAUSTED` (Quota Gemini dépassé). Le système bascule sur un fallback local qui plante avec un problème de parsing JSON.
*   **Amélioration** : 
    *   Améliorer le mécanisme de **fallback vers un LLM local** (ex: Ollama, Llama.cpp) pour qu'il soit 100% fonctionnel et gère exactement les mêmes formats JSON de réponse que Gemini.
    *   Mettre en place un système de cache ou de limitation de requêtes pour économiser le quota de l'API.

### 2. Robustesse de la Vision et de l'OCR
*   **Amélioration** : Actuellement, `easyocr` peut être lent ou imprécis selon la résolution. Tu pourrais intégrer la vision de Gemini 2.0 (si les quotas le permettent) pour détecter directement les coordonnées des boutons, ou utiliser un modèle plus léger comme YOLOv8 entraîné pour les UI (User Interfaces).

### 3. Tests Automatisés (Dossier `tests/`)
*   **Amélioration** : Le dossier `tests/` existe. Il serait judicieux de créer des tests unitaires robustes pour `fast_parser.py` et `orchestrator.py` afin de s'assurer que les modifications futures ne cassent pas le parsing des commandes.

### 4. Extensions d'Applications (Plugins)
*   **Amélioration** : Tu as déjà un module `agent/obsidian/`. Tu pourrais standardiser une architecture de "Plugins" pour d'autres applications courantes (ex: VSCode, Spotify, Chrome). Cela permettrait au `fast_parser` de rediriger directement vers la bonne logique d'application sans réfléchir.

### 5. Compatibilité Multi-OS / Gestion des erreurs PowerShell
*   **Amélioration** : Les logs indiquent une erreur PowerShell (`Start-Process 'spotify'`). Il faudrait améliorer la détection des chemins d'applications sous Windows (ex: lire le registre Windows ou utiliser des alias globaux) pour que l'ouverture d'apps ne plante pas.

### 6. Frontend : Optimisation Electron
*   **Amélioration** : S'assurer que le mode "Overlay" (fond transparent, click-through) fonctionne parfaitement sous Windows sans bloquer les interactions de l'utilisateur avec ses autres applications.

---

## 📝 Comment utiliser ce fichier ?
Ce fichier est ton plan de route. Tu peux cocher les cases au fur et à mesure que tu améliores Hacktoberfest ! N'hésite pas à me demander de t'aider sur un de ces points (par exemple : "Aide-moi à corriger l'erreur de Fallback Local" ou "Ajoute un plugin pour Spotify").
