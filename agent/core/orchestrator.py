"""Orchestrateur principal - boucle principale de l'agent."""

import argparse
import asyncio
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from agent.actions.apps import AppController
from agent.actions.keyboard import KeyboardController
from agent.actions.mouse import MouseController
from agent.actions.search import SearchController
from agent.actions.filesystem import FileSystemController
from agent.core.memory import MemoryManager, MemoryEntry, MemoryType
from agent.core.planner import TaskPlanner, TaskStatus
from agent.core.security import Action, SecurityGuard, SecurityLevel
from agent.obsidian.logger import ObsidianLogger
from agent.core.llm import GemmaModel, use_gemma
from agent.vision.analyzer import VisionAnalyzer
from agent.vision.capture import ScreenCapture
from agent.core.fast_parser import FastParser


logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrateur principal de l'agent."""

    def __init__(
        self,
        db_path: str,
        readonly_mode: bool = False,
    ) -> None:
        """Initialise l'orchestrateur.

        Args:
            db_path: Chemin vers la base de données SQLite.
            readonly_mode: Si True, désactive toutes les actions.
        """
        self.db_path = db_path
        self.security = SecurityGuard(readonly_mode=readonly_mode)
        self.memory = MemoryManager(db_path)
        self.planner = TaskPlanner(db_path)
        self.running = False
        self.callbacks = None

        # Initialiser les contrôleurs
        self.screen_capture = ScreenCapture()
        self.mouse_controller = MouseController()
        self.keyboard_controller = KeyboardController()
        self.app_controller = AppController()
        self.search_controller = SearchController()
        self.filesystem_controller = FileSystemController()
        self.fast_parser = FastParser()

        # Gemma via l'API Google. Gemini reste disponible si LLM_PROVIDER=gemini.
        if use_gemma():
            self.vision_analyzer = GemmaModel()
            logger.info("Cerveau Gemma: %s", self.vision_analyzer.model)
        else:
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.vision_analyzer = VisionAnalyzer(api_key)
            else:
                self.vision_analyzer = None
                logger.warning("GOOGLE_API_KEY non trouvée, l'analyse vision sera désactivée")

        # Initialiser le logger Obsidian si le chemin est disponible
        vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        if vault_path:
            try:
                self.obsidian_logger = ObsidianLogger(vault_path)
                logger.info(f"Logger Obsidian initialisé: {vault_path}")
            except Exception as e:
                self.obsidian_logger = None
                logger.warning(f"Erreur lors de l'initialisation d'Obsidian: {e}")
        else:
            self.obsidian_logger = None
            logger.warning("OBSIDIAN_VAULT_PATH non trouvée, le logging Obsidian sera désactivé")

        self._init_db()

    def _init_db(self) -> None:
        """Initialise la table session si elle n'existe pas."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session (
                    id TEXT PRIMARY KEY,
                    debut TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fin TIMESTAMP,
                    instruction_initiale TEXT NOT NULL,
                    statut TEXT NOT NULL DEFAULT 'en_cours',
                    readonly_mode BOOLEAN DEFAULT 0
                )
                """
            )
            conn.commit()

    async def run(self, instruction: str) -> str:
        """Exécute une instruction.

        Args:
            instruction: Instruction en langage naturel.

        Returns:
            ID de la session créée.
        """
        session_id = str(uuid.uuid4())

        # Créer la session
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session (id, instruction_initiale, readonly_mode)
                VALUES (?, ?, ?)
                """,
                (session_id, instruction, self.security.readonly_mode),
            )
            conn.commit()

        logger.info(f"Session créée: {session_id}")
        logger.info(f"Instruction: {instruction}")

        # Planifier la tâche principale
        tasks = self.planner.plan_task(session_id, instruction, getattr(self, 'vision_analyzer', None))

        if not tasks:
            logger.error("Échec de la planification de la tâche")
            self._end_session(session_id, "erreur")
            return session_id

        # Exécuter les tâches
        self.running = True
        try:
            await self._execute_tasks(session_id)
        except KeyboardInterrupt:
            logger.info("Interruption par l'utilisateur")
            self._end_session(session_id, "annulee")
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution: {e}")
            self._end_session(session_id, "erreur")
        finally:
            self.running = False

        return session_id

    async def _execute_tasks(self, session_id: str) -> None:
        """Exécute toutes les tâches d'une session.

        Args:
            session_id: ID de la session.
        """
        while self.running:
            # Récupérer la prochaine tâche en attente
            task = self.planner.get_next_pending_task(session_id)

            if task is None:
                logger.info("Plus de tâches en attente")
                self._end_session(session_id, "terminee")
                break

            logger.info(f"Exécution de la tâche: {task.description}")

            # Marquer comme en cours
            self.planner.update_task_status(task.id, TaskStatus.IN_PROGRESS)

            # Exécuter la tâche
            try:
                await self._execute_task(session_id, task)
                self.planner.update_task_status(task.id, TaskStatus.COMPLETED)
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de la tâche: {e}")
                self.planner.update_task_status(task.id, TaskStatus.FAILED)

                # Stocker l'erreur en mémoire
                self.memory.add_memory(
                    session_id,
                    MemoryEntry(
                        content=f"Erreur: {e}",
                        tags=["erreur"],
                        memory_type=MemoryType.SHORT_TERM,
                    ),
                )

    async def _execute_task(self, session_id: str, task) -> None:
        """Exécute une tâche spécifique de manière itérative (ReAct)."""
        logger.info(f"Exécution de: {task.description}")

        async def say(text: str):
            """Envoie un message naturel à l'utilisateur via l'UI."""
            if self.callbacks:
                await self.callbacks.log_message("INFO", text)

        # --- FAST-TRACK: commandes système, puis ouverture locale d'applications ---
        fast_cmd = self.fast_parser.parse(task.description)
        if fast_cmd:
            await say("Je m'en occupe tout de suite.")
            await self._execute_action("system_command", {"command": fast_cmd})
            await say("C'est fait !")
            return

        app_action = self.fast_parser.parse_app_action(task.description)
        if app_action:
            kind, app_query = app_action
            if kind == "open_maybe" and not self.app_controller.can_open(app_query):
                app_action = None
            else:
                if kind == "open_maybe":
                    kind = "open"
                await say("Je m'en occupe tout de suite.")
                label = self.app_controller.resolve_name(app_query) or app_query
                if kind == "open":
                    opened = self.app_controller.open(app_query)
                    await say(
                        f"{label} est ouvert."
                        if opened
                        else f"Je ne trouve pas « {app_query} » parmi les applications installées."
                    )
                else:
                    closed = self.app_controller.close(app_query)
                    await say(
                        f"{label} est fermé."
                        if closed
                        else f"Je n'ai pas pu fermer « {app_query} »."
                    )
                return
        # --- FIN FAST-TRACK ---

        max_iterations = 20
        iteration = 0
        action_history = []
        task_completed = False

        # Messages d'observation humains pour éviter la répétition
        observation_msgs = [
            "Je regarde l'écran pour savoir quoi faire...",
            "J'observe la situation avant d'agir...",
            "J'analyse ce qui est affiché...",
            "Je scanne l'écran pour continuer...",
        ]

        # Mapping action → description naturelle AVANT exécution
        def describe_action_before(action_type: str, params: dict) -> str:
            p = params
            m = {
                "app_open":          f"J'ouvre {p.get('app_name', 'l\'application')}...",
                "app_open_and_type": f"J'ouvre {p.get('app_name', 'l\'application')} et je tape le texte...",
                "app_close":         f"Je ferme {p.get('app_name', 'l\'application')}...",
                "app_focus":         f"Je mets le focus sur {p.get('app_name', 'l\'application')}...",
                "keyboard_type":     f"Je tape : « {p.get('text', '')[:60]} »...",
                "type_text":         f"Je tape : « {p.get('text', '')[:60]} »...",
                "keyboard_press":    f"J'appuie sur la touche {p.get('key', '')}...",
                "keyboard_hotkey":   f"J'utilise le raccourci {' + '.join(p.get('keys', []))}...",
                "mouse_click":       f"Je clique à la position ({p.get('x')}, {p.get('y')})...",
                "mouse_move":        f"Je déplace la souris...",
                "mouse_scroll":      f"Je fais défiler...",
                "mouse_drag":        f"Je glisse un élément...",
                "web_search":        f"Je recherche « {p.get('query', '')} » sur le web...",
                "create_directory":  f"Je crée le dossier « {p.get('path', '')} »...",
                "move_file":         f"Je déplace le fichier vers {p.get('dst', '')}...",
                "copy_file":         f"Je copie le fichier vers {p.get('dst', '')}...",
                "list_directory":    f"Je lis le contenu du dossier {p.get('path', '')}...",
                "file_read":         f"Je lis le fichier {p.get('path', '')}...",
                "file_write":        f"J'écris dans le fichier {p.get('path', '')}...",
                "file_delete":       f"Je supprime le fichier {p.get('path', '')}...",
                "system_command":    f"J'exécute une commande système...",
            }
            return m.get(action_type, f"Je fais l'action : {action_type}...")

        # Mapping action → confirmation naturelle APRÈS exécution
        def describe_action_after(action_type: str, params: dict, result) -> str:
            p = params
            m = {
                "app_open":          f"L'application {p.get('app_name', '')} est ouverte.",
                "app_open_and_type": f"J'ai ouvert {p.get('app_name', '')} et saisi le texte.",
                "app_close":         f"{p.get('app_name', 'L\'application')} est fermée.",
                "keyboard_type":     "Le texte a été saisi.",
                "type_text":         "Le texte a été saisi.",
                "keyboard_press":    f"Touche {p.get('key', '')} pressée.",
                "keyboard_hotkey":   "Raccourci exécuté.",
                "mouse_click":       "Clic effectué.",
                "mouse_scroll":      "Défilement effectué.",
                "web_search":        "Recherche effectuée.",
                "create_directory":  f"Dossier « {p.get('path', '')} » créé.",
                "move_file":         "Fichier déplacé.",
                "copy_file":         "Fichier copié.",
                "system_command":    f"Commande exécutée.{(' Résultat : ' + str(result)[:120]) if result and 'Succès' in str(result) else ''}",
            }
            return m.get(action_type, "Action effectuée.")

        while self.running and iteration < max_iterations and not task_completed:
            iteration += 1

            # Message d'observation (rotation pour éviter la répétition)
            await say(observation_msgs[(iteration - 1) % len(observation_msgs)])

            # Capturer l'écran
            screenshot_path = self.screen_capture.capture_full_screen()

            action_to_execute = None

            if self.vision_analyzer:
                import json
                import os

                history_str = "Aucune action précédente."
                if action_history:
                    history_str = "\n".join([
                        f"- {a['action']} (Params: {a.get('params', {})}) -> {a.get('result', 'OK')}"
                        for a in action_history[-5:]
                    ])

                manifest_path = os.path.join(os.path.dirname(__file__), "tools_manifest.json")
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        tools_manifest = f.read()
                except Exception as e:
                    logger.error(f"Erreur de lecture du tools_manifest: {e}")
                    tools_manifest = "Impossible de charger le manifeste."

                prompt = f"""Tu es le cerveau d'un agent de contrôle d'ordinateur sous Windows.
Ta tâche globale est : "{task.description}"

Historique récent de tes actions :
{history_str}

Voici le manifeste des actions supportées :
{tools_manifest}

En observant la capture d'écran actuelle et l'historique, détermine la SEULE prochaine action à effectuer pour avancer vers ton objectif.
Si la tâche est complètement terminée avec succès, utilise l'action 'task_complete'.
Si tu as besoin d'une confirmation de l'utilisateur ou d'une information pour lever une ambiguïté, utilise 'ask_human'.

Format de réponse attendu (UNIQUEMENT un objet JSON pur, aucun autre texte) :
{{"action_type": "nom_action", "params": {{"cle": "valeur"}}}}
"""
                try:
                    response = self.vision_analyzer.analyze_screen(
                        screenshot_path,
                        prompt,
                        context="Tu dois choisir UNE SEULE action suivante pour accomplir la tâche."
                    )
                    json_str = response.strip()
                    if json_str.startswith("```json"):
                        json_str = json_str[7:-3].strip()
                    elif json_str.startswith("```"):
                        json_str = json_str[3:-3].strip()

                    action_data = json.loads(json_str)

                    if isinstance(action_data, list) and len(action_data) > 0:
                        action_data = action_data[0]

                    if isinstance(action_data, dict) and "action_type" in action_data:
                        if action_data["action_type"] == "web_search":
                            if "params" not in action_data:
                                action_data["params"] = {}
                            action_data["params"]["session_id"] = session_id
                            action_data["params"]["instruction"] = task.description
                        action_to_execute = action_data
                except Exception as e:
                    logger.error(f"Erreur lors du parsing LLM de l'action: {e}")

            # Fallback statique si l'IA échoue ou n'est pas disponible (première itération uniquement)
            if not action_to_execute and iteration == 1:
                instruction_lower = task.description.lower()
                action_type = None
                action_params = {}

                app_name = self._extract_app_name(task.description)
                text_to_type = self._extract_text_to_type(task.description)

                if app_name and text_to_type:
                    action_type = "app_open_and_type"
                    action_params = {"app_name": app_name, "text": text_to_type}
                elif app_name and ("ouvr" in instruction_lower or "open" in instruction_lower or "lanc" in instruction_lower):
                    action_type = "app_open"
                    action_params = {"app_name": app_name}
                elif text_to_type:
                    action_type = "type_text"
                    action_params = {"text": text_to_type}
                elif "recherche" in instruction_lower:
                    import re
                    match = re.search(r'recherche\s+(?:sur\s+)?(.+)', instruction_lower)
                    query = match.group(1).strip() if match else instruction_lower.replace("recherche", "").strip()
                    query = re.sub(r'\s+et\s+crée.*$', '', query, flags=re.IGNORECASE)
                    action_type = "web_search"
                    action_params = {"query": query, "session_id": session_id, "instruction": task.description}
                elif "dossier" in instruction_lower and "crée" in instruction_lower:
                    import re
                    match = re.search(r'crée\s+(?:un\s+)?dossier\s+(?:nommé\s+)?["\']?([^"\']+)["\']?', instruction_lower)
                    path = match.group(1).strip() if match else "Nouveau dossier"
                    action_type = "create_directory"
                    action_params = {"path": path}
                elif "déplacer" in instruction_lower or "deplacer" in instruction_lower or "déplace" in instruction_lower or "mets les fichiers" in instruction_lower:
                    import re
                    match_ext = re.search(r"'(?:\.)?([^']+)'", instruction_lower)
                    match_dest = re.search(r"vers (?:le dossier )?'([^']+)'", instruction_lower)
                    if match_ext and match_dest:
                        ext = match_ext.group(1).replace('.', '')
                        dest = match_dest.group(1)
                        cmd = f"Move-Item -Path '*.*{ext}' -Destination '{dest}' -ErrorAction SilentlyContinue"
                        action_type = "system_command"
                        action_params = {"command": cmd}

                if action_type:
                    action_to_execute = {"action_type": action_type, "params": action_params}

            if not action_to_execute:
                await say("Je n'arrive pas à déterminer comment procéder. Peux-tu reformuler ta demande ?")
                break

            action_type = action_to_execute["action_type"]
            action_params = action_to_execute.get("params", {})

            if action_type == "task_complete":
                msg = action_params.get("message", "C'est fait !")
                await say(msg)
                task_completed = True
                break

            if action_type == "ask_human":
                question = action_params.get("question", "J'ai besoin de ton aide, peux-tu m'aiguiller ?")
                await say(question)
                action_history.append({
                    "action": action_type,
                    "params": action_params,
                    "result": "En attente de réponse utilisateur"
                })
                continue

            # Message AVANT exécution
            await say(describe_action_before(action_type, action_params))

            # Classifier l'action pour la sécurité
            security_level = self.classify_action(action_type, action_params)

            if self.security.readonly_mode:
                await say("Je suis en mode lecture seule, je ne peux pas effectuer cette action.")
                action_history.append({"action": action_type, "params": action_params, "result": "bloqué (readonly)"})
                break

            if security_level.value == "CRITICAL":
                if self.callbacks:
                    approved = await self.callbacks.request_confirmation(action_type, action_params)
                    if not approved:
                        await say("D'accord, j'annule cette action.")
                        action_history.append({"action": action_type, "params": action_params, "result": "annulée par l'utilisateur"})
                        continue
                else:
                    print(f"\n[SECURITE] L'agent souhaite exécuter une action CRITIQUE : {action_type}")
                    print(f"Paramètres : {action_params}")
                    rep = input("Confirmez-vous l'exécution de cette commande ? [o/N] : ")
                    if rep.lower() not in ['o', 'y', 'oui', 'yes']:
                        action_history.append({"action": action_type, "params": action_params, "result": "annulée par l'utilisateur"})
                        continue

            # Exécuter l'action
            action_result = await self._execute_action(action_type, action_params)

            # Message APRÈS exécution
            await say(describe_action_after(action_type, action_params, action_result))

            action_history.append({
                "action": action_type,
                "params": action_params,
                "result": action_result if action_result is not None else "Exécutée avec succès"
            })

            await asyncio.sleep(0.3)  # Réduit de 1.0 → 0.3 pour plus de réactivité

        if not task_completed and iteration >= max_iterations:
            await say("J'ai atteint le nombre maximum d'étapes sans terminer. Veux-tu que je réessaie ?")

    def _extract_text_to_type(self, instruction: str) -> Optional[str]:
        """Extrait le texte à taper de l'instruction."""
        import re
        
        # 1. Chercher entre guillemets simples ou doubles
        match = re.search(r'["\']([^"\']+)["\']', instruction)
        if match:
            return match.group(1)
            
        # 2. Chercher après certains mots clés : écrit, tape, note, texte
        match = re.search(r'(?:écri|tape|note|texte)(?:\s+le texte)?\s*(?::|que|)\s+(.+)', instruction, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            # Nettoyer les mentions de l'application à la fin
            text = re.sub(r'\s+(?:dans|sur)\s+(?:le\s+)?(?:bloc-?notes|obsidian|chrome|word|excel).*$', '', text, flags=re.IGNORECASE)
            return text
            
        return None

    def _extract_app_name(self, instruction: str) -> Optional[str]:
        """Extrait le nom de l'application de l'instruction.

        Args:
            instruction: Instruction en langage naturel.

        Returns:
            Nom de l'application ou None.
        """
        instruction_lower = instruction.lower()

        # Mapping simple d'applications
        app_mapping = {
            "bloc-notes": "notepad",
            "notepad": "notepad",
            "chrome": "chrome",
            "navigateur": "chrome",
            "excel": "excel",
            "word": "word",
            "calculatrice": "calc",
            "calc": "calc",
            "obsidian": "obsidian",
        }

        for key, app in app_mapping.items():
            if key in instruction_lower:
                return app

        return None

    async def _execute_action(self, action_type: str, params: dict) -> Optional[str]:
        """Exécute une action.

        Args:
            action_type: Type de l'action.
            params: Paramètres de l'action.
        """
        logger.info(f"Exécution de l'action: {action_type} avec params: {params}")

        # --- Souris ---
        if action_type == "mouse_click":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            clicks = params.get("clicks", 1)
            if x is not None and y is not None:
                self.mouse_controller.click(int(x), int(y), button, int(clicks))
                
        elif action_type == "mouse_move":
            x = params.get("x")
            y = params.get("y")
            duration = params.get("duration", 0.2)
            if x is not None and y is not None:
                self.mouse_controller.move(int(x), int(y), float(duration))
                
        elif action_type == "mouse_drag":
            start_x = params.get("start_x")
            start_y = params.get("start_y")
            end_x = params.get("end_x")
            end_y = params.get("end_y")
            duration = params.get("duration", 0.5)
            button = params.get("button", "left")
            if all(v is not None for v in [start_x, start_y, end_x, end_y]):
                self.mouse_controller.drag(int(start_x), int(start_y), int(end_x), int(end_y), float(duration), button)
                
        elif action_type == "mouse_scroll":
            x = params.get("x")
            y = params.get("y")
            clicks = params.get("clicks", 5)
            direction = params.get("direction", "down")
            if x is not None and y is not None:
                self.mouse_controller.scroll(int(x), int(y), int(clicks), direction)
        
        # --- Clavier ---
        elif action_type in ("keyboard_type", "type_text"):
            text = params.get("text")
            interval = params.get("interval", 0.01)
            if text:
                self.keyboard_controller.type(text, float(interval))
                
        elif action_type == "keyboard_press":
            key = params.get("key")
            if key:
                self.keyboard_controller.press(key)
                
        elif action_type == "keyboard_hotkey":
            keys = params.get("keys", [])
            if keys and isinstance(keys, list):
                self.keyboard_controller.hotkey(*keys)

        # --- Applications ---
        elif action_type == "app_open":
            app_name = params.get("app_name")
            if app_name:
                success = self.app_controller.open(app_name)
                if success:
                    logger.info(f"Application {app_name} ouverte avec succès")
                else:
                    logger.error(f"Échec de l'ouverture de {app_name}")
                    
        elif action_type == "app_close":
            app_name = params.get("app_name")
            force = params.get("force", False)
            if app_name:
                self.app_controller.close(app_name, force)
                
        elif action_type == "app_focus":
            app_name = params.get("app_name")
            if app_name:
                self.app_controller.focus(app_name)
                
        elif action_type == "app_open_and_type":
            app_name = params.get("app_name")
            text = params.get("text")
            if app_name and text:
                success = self.app_controller.open(app_name)
                if success:
                    logger.info(f"Application {app_name} ouverte. Attente de 2 secondes avant la frappe...")
                    import asyncio
                    await asyncio.sleep(2.0)
                    self.app_controller.focus(app_name)
                    self.keyboard_controller.type(text)
                    self.keyboard_controller.press("enter")
                    logger.info("Texte tapé avec succès")
                else:
                    logger.error(f"Échec de l'ouverture de {app_name}")
                    
        # --- Web & Fichiers ---
        elif action_type == "web_search":
            query = params.get("query")
            session_id = params.get("session_id", "unknown")
            if query:
                results = self.search_controller.search_web(query)
                formatted_content = self.search_controller.format_results(results)
                
                if self.vision_analyzer:
                    instruction = params.get("instruction", query)
                    if results:
                        prompt = f"Tu es un assistant IA. L'utilisateur a demandé : '{instruction}'.\n\nVoici les résultats d'une recherche web :\n{formatted_content}\n\nRédige une réponse ou un résumé utile basé sur ces résultats."
                    else:
                        prompt = f"Tu es un assistant IA. L'utilisateur a demandé : '{instruction}'.\n\nRédige une réponse utile, sans résultats."
                        
                    summary = self.vision_analyzer.generate_text(prompt)
                    formatted_content = f"## Résumé IA\n\n{summary}\n\n## Sources brutes\n\n{formatted_content}"

                references = [{"title": r.get("title", "Lien"), "href": r.get("href", "")} for r in results]
                
                if getattr(self, "obsidian_logger", None):
                    self.obsidian_logger.create_research_note(
                        session_id=session_id,
                        query=query,
                        content=formatted_content,
                        references=references
                    )
                    logger.info("Recherche effectuée et enregistrée dans Obsidian.")
                else:
                    logger.info("Recherche effectuée (pas d'enregistrement Obsidian).")
                    
        elif action_type == "create_directory":
            path = params.get("path")
            if path:
                self.filesystem_controller.create_directory(path)
                
        elif action_type == "move_file":
            src = params.get("src")
            dst = params.get("dst")
            if src and dst:
                self.filesystem_controller.move_file(src, dst)
                
        elif action_type == "copy_file":
            src = params.get("src")
            dst = params.get("dst")
            if src and dst:
                self.filesystem_controller.copy_file(src, dst)
                
        # --- Système et Fichiers ---
        elif action_type == "list_directory":
            path = params.get("path")
            if path:
                items = self.filesystem_controller.list_directory(path)
                import json
                return f"Contenu du dossier: {json.dumps(items)}"
                
        elif action_type == "file_read":
            path = params.get("path")
            if path:
                content = self.filesystem_controller.read_file(path)
                return f"Contenu du fichier:\n{content[:2000]}" # Limiter la taille
                
        elif action_type == "file_write":
            path = params.get("path")
            content = params.get("content")
            mode = params.get("mode", "w")
            if path and content:
                self.filesystem_controller.write_file(path, content, mode)
                
        elif action_type == "file_delete":
            path = params.get("path")
            if path:
                self.filesystem_controller.delete_file(path)
                items = self.filesystem_controller.list_directory(path)
                import json
                return f"Contenu du dossier: {json.dumps(items)}"
                
        elif action_type == "system_command":
            command = params.get("command")
            if command:
                import subprocess
                try:
                    logger.info(f"Exécution de la commande système: {command}")
                    result = subprocess.run(
                        ["powershell", "-Command", command],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        logger.info(f"Commande réussie: {result.stdout}")
                        return f"Succès:\n{result.stdout[:500]}"
                    else:
                        logger.error(f"Erreur de commande ({result.returncode}): {result.stderr}")
                        return f"Erreur:\n{result.stderr[:500]}"
                except Exception as e:
                    logger.error(f"Exception lors de la commande système: {e}")
                    return f"Exception:\n{str(e)}"
                
        else:
            logger.warning(f"Type d'action non supporté ou ignoré: {action_type}")

    def _end_session(self, session_id: str, status: str) -> None:
        """Termine une session.

        Args:
            session_id: ID de la session.
            status: Statut final de la session.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE session
                SET fin = CURRENT_TIMESTAMP, statut = ?
                WHERE id = ?
                """,
                (status, session_id),
            )
            conn.commit()

        logger.info(f"Session terminée: {session_id} (statut: {status})")

        # Créer une note Obsidian si le logger est disponible
        if self.obsidian_logger:
            try:
                # Récupérer les informations de la session
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT instruction_initiale FROM session WHERE id = ?",
                        (session_id,),
                    )
                    row = cursor.fetchone()
                    instruction = row[0] if row else "Inconnue"

                # Récupérer les tâches de la session
                tasks = self.planner.get_session_tasks(session_id)
                task_descriptions = [task.description for task in tasks]

                # Créer la note de session
                self.obsidian_logger.create_session_note(
                    session_id=session_id,
                    instruction=instruction,
                    resume=f"Session terminée avec statut: {status}",
                    tasks=task_descriptions,
                    status=status,
                )
                logger.info("Note Obsidian créée pour la session")
            except Exception as e:
                logger.error(f"Erreur lors de la création de la note Obsidian: {e}")

    def stop(self) -> None:
        """Arrête l'orchestrateur."""
        self.running = False
        logger.info("Orchestrateur arrêté")

    def classify_action(self, action_type: str, parameters: dict) -> SecurityLevel:
        """Classifie une action selon son niveau de sécurité.

        Args:
            action_type: Type de l'action.
            parameters: Paramètres de l'action.

        Returns:
            Niveau de sécurité de l'action.
        """
        action = Action(action_type=action_type, parameters=parameters)
        decision = self.security.classify(action)
        return decision.level


def main() -> None:
    """Point d'entrée principal pour l'exécution du module."""
    # Charger les variables d'environnement
    load_dotenv()

    # Parser les arguments
    parser = argparse.ArgumentParser(description="Agent IA local pour le contrôle d'ordinateur")
    parser.add_argument("instruction", nargs="?", help="Instruction à exécuter")
    parser.add_argument("--readonly", action="store_true", help="Mode lecture seule")
    parser.add_argument("--db", default=os.getenv("DB_PATH", "./agent.db"), help="Chemin vers la base de données")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"), help="Niveau de logging")

    args = parser.parse_args()

    # Configurer le logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Vérifier l'instruction
    if not args.instruction:
        logger.error("Veuillez fournir une instruction")
        parser.print_help()
        return

    # Créer l'orchestrateur
    orchestrator = Orchestrator(db_path=args.db, readonly_mode=args.readonly)

    # Exécuter l'instruction
    logger.info(f"Démarrage de l'agent avec instruction: {args.instruction}")
    session_id = asyncio.run(orchestrator.run(args.instruction))

    logger.info(f"Session terminée: {session_id}")


if __name__ == "__main__":
    main()
