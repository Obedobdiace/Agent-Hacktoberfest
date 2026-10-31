import os

filepath = r"c:\Users\Admin\Music\the gestue\Computer User\agent\core\orchestrator.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

task_replacement = '''    async def _execute_task(self, session_id: str, task) -> None:
        """Exécute une tâche spécifique de manière itérative (ReAct).

        Args:
            session_id: ID de la session.
            task: Tâche à exécuter.
        """
        logger.info(f"Exécution de: {task.description}")

        max_iterations = 20
        iteration = 0
        action_history = []
        task_completed = False

        while self.running and iteration < max_iterations and not task_completed:
            iteration += 1
            logger.info(f"--- Itération {iteration} pour la tâche: {task.description} ---")

            # Capturer l'écran
            screenshot_path = self.screen_capture.capture_full_screen()
            logger.info(f"Capture d'écran: {screenshot_path}")

            action_to_execute = None

            if self.vision_analyzer:
                import json
                import os
                
                # Construire l'historique
                history_str = "Aucune action précédente."
                if action_history:
                    history_str = "\\n".join([f"- {a['action']} (Params: {a.get('params', {})}) -> {a.get('result', 'OK')}" for a in action_history[-5:]])

                # Charger le manifeste d'outils
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
                    match = re.search(r'recherche\\s+(?:sur\\s+)?(.+)', instruction_lower)
                    query = match.group(1).strip() if match else instruction_lower.replace("recherche", "").strip()
                    query = re.sub(r'\\s+et\\s+crée.*$', '', query, flags=re.IGNORECASE)
                    action_type = "web_search"
                    action_params = {"query": query, "session_id": session_id, "instruction": task.description}
                elif "dossier" in instruction_lower and "crée" in instruction_lower:
                    import re
                    match = re.search(r'crée\\s+(?:un\\s+)?dossier\\s+(?:nommé\\s+)?["\\\']?([^"\\\']+)["\\\']?', instruction_lower)
                    path = match.group(1).strip() if match else "Nouveau dossier"
                    action_type = "create_directory"
                    action_params = {"path": path}
                
                if action_type:
                    action_to_execute = {"action_type": action_type, "params": action_params}

            if not action_to_execute:
                logger.warning("Aucune action déterminée, arrêt de la boucle pour cette tâche.")
                break

            action_type = action_to_execute["action_type"]
            action_params = action_to_execute.get("params", {})

            if action_type == "task_complete":
                msg = action_params.get("message", "Tâche terminée.")
                logger.info(f"Tâche accomplie selon l'agent : {msg}")
                task_completed = True
                break
                
            if action_type == "ask_human":
                question = action_params.get("question", "J'ai besoin de votre aide, pouvez-vous m'aiguiller ?")
                print(f"\\n[QUESTION DE L'AGENT] {question}")
                rep = input("Votre réponse : ")
                action_history.append({
                    "action": action_type,
                    "params": action_params,
                    "result": f"Réponse de l'utilisateur : {rep}"
                })
                continue
            
            # Classifier l'action pour la sécurité
            security_level = self.classify_action(action_type, action_params)
            logger.info(f"Action '{action_type}' - Niveau de sécurité: {security_level.value}")

            if self.security.readonly_mode:
                logger.warning(f"Action bloquée (readonly mode)")
                action_history.append({"action": action_type, "params": action_params, "result": "bloqué (readonly)"})
                break
                
            if security_level.value == "CRITICAL":
                print(f"\\n[SECURITE] L'agent souhaite exécuter une action CRITIQUE : {action_type}")
                print(f"Paramètres : {action_params}")
                rep = input("Confirmez-vous l'exécution de cette commande ? [o/N] : ")
                if rep.lower() not in ['o', 'y', 'oui', 'yes']:
                    logger.warning("Action CRITIQUE annulée par l'utilisateur.")
                    action_history.append({"action": action_type, "params": action_params, "result": "annulée par l'utilisateur"})
                    continue

            # Exécuter l'action
            await self._execute_action(action_type, action_params)
            
            action_history.append({
                "action": action_type,
                "params": action_params,
                "result": "Exécutée avec succès"
            })
            
            import asyncio
            await asyncio.sleep(1.0)
            
        if not task_completed and iteration >= max_iterations:
            logger.warning("Nombre maximum d'itérations atteint pour la tâche.")'''

action_replacement = '''    async def _execute_action(self, action_type: str, params: dict) -> None:
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
                        prompt = f"Tu es un assistant IA. L'utilisateur a demandé : '{instruction}'.\\n\\nVoici les résultats d'une recherche web :\\n{formatted_content}\\n\\nRédige une réponse ou un résumé utile basé sur ces résultats."
                    else:
                        prompt = f"Tu es un assistant IA. L'utilisateur a demandé : '{instruction}'.\\n\\nRédige une réponse utile, sans résultats."
                        
                    summary = self.vision_analyzer.generate_text(prompt)
                    formatted_content = f"## Résumé IA\\n\\n{summary}\\n\\n## Sources brutes\\n\\n{formatted_content}"

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
                
        # --- Système ---
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
                    else:
                        logger.error(f"Erreur de commande ({result.returncode}): {result.stderr}")
                except Exception as e:
                    logger.error(f"Exception lors de la commande système: {e}")
                
        else:
            logger.warning(f"Type d'action non supporté ou ignoré: {action_type}")'''

start_task = "    async def _execute_task(self, session_id: str, task) -> None:"
end_task = "    def _extract_text_to_type(self, instruction: str) -> Optional[str]:"
task_idx1 = content.find(start_task)
task_idx2 = content.find(end_task)
if task_idx1 != -1 and task_idx2 != -1:
    content = content[:task_idx1] + task_replacement + "\\n\\n" + content[task_idx2:]

start_action = "    async def _execute_action(self, action_type: str, params: dict) -> None:"
end_action = "    def _end_session(self, session_id: str, status: str) -> None:"
action_idx1 = content.find(start_action)
action_idx2 = content.find(end_action)
if action_idx1 != -1 and action_idx2 != -1:
    content = content[:action_idx1] + action_replacement + "\\n\\n" + content[action_idx2:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Remplacement terminé avec succès.")
