import asyncio
import logging
from typing import Optional

from dotenv import load_dotenv
load_dotenv()  # Charge .env dès le démarrage du serveur

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import json

from agent.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

app = FastAPI(title="Hacktoberfest API")


@app.on_event("startup")
async def warm_installed_apps() -> None:
    """Indexe les applications du PC avant la première demande d'ouverture."""
    import threading

    from agent.actions.app_catalog import warm_catalog
    from agent.voice.listener import warm_engine

    threading.Thread(target=warm_catalog, name="app-catalog", daemon=True).start()
    threading.Thread(target=warm_engine, name="voice-engine", daemon=True).start()

    from agent.core.llm import GemmaModel, use_gemma

    if use_gemma():
        print(GemmaModel().describe_status(), flush=True)

# Serve static files from the frontend directory
frontend_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
else:
    logger.debug(f"Frontend dist not found at {frontend_dir} — running in dev mode via Vite/Electron.")

@app.get("/")
async def root():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not built. Run npm run build in frontend."}


# ─────────────────────────────────────────────────────────────
#  CONVERSATION HISTORY  (contexte multi-tours)
# ─────────────────────────────────────────────────────────────
conversation_history: list[dict] = []   # [{role, content}, ...]

MAX_HISTORY = 20   # garder les 20 derniers échanges

def _add_to_history(role: str, content: str):
    conversation_history.append({"role": role, "content": content})
    if len(conversation_history) > MAX_HISTORY:
        conversation_history.pop(0)


# ─────────────────────────────────────────────────────────────
#  CHAT ROUTER  — cerveau conversationnel
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es Hacktoberfest, un agent autonome de contrôle d'ordinateur.
Tu es intelligent, direct et chaleureux. Tu parles toujours en français.

Ta mission : analyser chaque message de l'utilisateur et décider s'il faut :
  A) Avoir une conversation naturelle (salutation, question, explication, etc.)
  B) Exécuter une tâche sur l'ordinateur (ouvrir une app, taper du texte, chercher sur le web, créer un fichier, etc.)

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après :

Pour une conversation :
{"type": "chat", "response": "Ta réponse naturelle ici."}

Pour une tâche à exécuter :
{"type": "command", "task": "description claire de la tâche", "ack": "Message naturel annonçant ce que tu vas faire."}

Exemples :
- "bonjour" → {"type": "chat", "response": "Bonjour ! Je suis Hacktoberfest, ton agent. Qu'est-ce que je peux faire pour toi ?"}
- "ouvre chrome" → {"type": "command", "task": "ouvrir l'application Chrome", "ack": "Je lance Chrome pour toi."}
- "c'est quoi obsidian ?" → {"type": "chat", "response": "Obsidian est un éditeur de notes..."}
- "cherche les dernières news sur l'IA" → {"type": "command", "task": "rechercher sur le web : dernières news sur l'intelligence artificielle", "ack": "Je cherche ça tout de suite."}
- "qu'est-ce que tu peux faire ?" → {"type": "chat", "response": "Je peux ouvrir des applications, taper du texte, faire des recherches web, créer des dossiers, déplacer des fichiers et exécuter des commandes système. Dis-moi ce dont tu as besoin !"}
"""

def _build_gemini_messages() -> list[dict]:
    """Construit l'historique de conversation au format Gemini."""
    msgs = []
    for turn in conversation_history[-10:]:   # 10 derniers tours max
        role = "user" if turn["role"] == "user" else "model"
        msgs.append({"role": role, "parts": [{"text": turn["content"]}]})
    return msgs


def _local_classify(user_message: str) -> dict:
    """
    Classifieur local sans API — utilisé comme fallback quand Gemini
    est indisponible (quota 429, pas de clé, erreur réseau).
    """
    msg = user_message.lower().strip()

    # 1. Vérifier si c'est une commande d'action claire
    action_keywords = [
        "ouvre", "lance", "démarre", "ferme", "quitte", "arrête",
        "cherche", "trouve", "crée", "fais", "écris", "tape",
        "verrouille", "vide", "capture", "prends", "mets", "déplace",
        "ouvrir", "lancer", "démarrer", "fermer", "quitter", "arrêter",
        "chercher", "trouver", "créer", "faire", "écrire", "taper",
        "verrouiller", "vider", "capturer", "prendre", "mettre", "déplacer"
    ]
    for ak in action_keywords:
        # Si on trouve un verbe d'action, c'est une commande
        if ak in msg:
            return {"type": "command", "task": user_message, "ack": "Compris, je m'en occupe."}

    # 2. Réponses rapides aux salutations
    quick_responses = {
        "bonjour": "Bonjour ! Je suis Hacktoberfest, ton agent autonome. Qu'est-ce que je peux faire pour toi ?",
        "bonsoir": "Bonsoir ! Je suis là. Dis-moi ce dont tu as besoin.",
        "salut":   "Salut ! Prêt à agir. Qu'est-ce que tu veux faire ?",
        "hello":   "Hello ! Dis-moi ce que tu veux que je fasse.",
        "merci":   "Avec plaisir ! Autre chose pour toi ?",
    }
    for key, resp in quick_responses.items():
        if key in msg:
            return {"type": "chat", "response": resp}
            
    # 3. Triggers de conversation (questions sur l'agent)
    chat_triggers = [
        "comment tu vas", "comment ça va", "ça va",
        "qu'est-ce que tu", "que peux-tu", "que sais-tu",
        "c'est quoi", "explique", "raconte", "dis-moi",
        "tu peux", "tu es", "qui es-tu", "présente-toi",
        "j'ai une question", "que fais-tu",
    ]
    for trigger in chat_triggers:
        if trigger in msg:
            return {"type": "chat", "response": "Je suis Hacktoberfest — je peux ouvrir des apps, taper du texte, faire des recherches, créer des dossiers et exécuter des commandes. Dis-moi ce dont tu as besoin !"}

    # Fallback par défaut : on tente de l'exécuter comme une commande
    return {"type": "command", "task": user_message, "ack": "Compris, je m'en occupe."}


async def chat_router(user_message: str) -> dict:
    """
    Envoie le message à Gemini Flash pour décider si c'est
    une conversation ou une commande. Fallback local si API indisponible.

    Ouvrir ou fermer une application ne dépend pas du modèle : le catalogue
    local des applications installées s'en charge.
    """
    from agent.core.fast_parser import FastParser

    app_action = FastParser().parse_app_action(user_message)
    if app_action and app_action[0] in {"open", "close"}:
        return {"type": "command", "task": user_message, "ack": "Compris, je m'en occupe."}

    from agent.core.llm import GemmaModel, extract_json, redact, use_gemma

    if use_gemma():
        try:
            model = GemmaModel()
            raw = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.complete(
                    SYSTEM_PROMPT,
                    conversation_history[-8:],
                    user_message,
                ),
            )
            return extract_json(raw)
        except Exception as exc:
            logger.warning("Gemma injoignable (%s) — secours local.", redact(str(exc)))
            return _local_classify(user_message)

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _local_classify(user_message)

    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=api_key)

        history_parts = []
        for turn in conversation_history[-8:]:
            role = "user" if turn["role"] == "user" else "model"
            history_parts.append({"role": role, "parts": [{"text": turn["content"]}]})
        history_parts.append({"role": "user", "parts": [{"text": user_message}]})

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=history_parts,
                config={"system_instruction": SYSTEM_PROMPT}
            )
        )

        raw = response.text.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        return json.loads(raw.strip())

    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            logger.warning("Quota Gemini dépassé — fallback local activé.")
        else:
            logger.error(f"Erreur chat_router: {e}")
        return _local_classify(user_message)


# ─────────────────────────────────────────────────────────────
#  CONNECTION MANAGER
# ─────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
orchestrator_instance: Optional[Orchestrator] = None
current_session_id: Optional[str] = None
pending_confirmation: Optional[asyncio.Future] = None


# ─────────────────────────────────────────────────────────────
#  HUMANIZE LOG
# ─────────────────────────────────────────────────────────────
def humanize_log(level: str, message: str) -> str | None:
    """Passes through messages that are already human-friendly,
    silently drops raw technical logs."""
    msg = message.strip()

    ignore_patterns = [
        "Session créée:",
        "Session terminée:",
        "Capture d'écran:",
        "--- Itération",
        "Fast-Track:",
        "Exécution de l'action:",
        "Exécution de la commande",
        "Exécution de la tâche:",
        "Exécution de:",
        "Tâche accomplie",
        "Plus de tâches en attente",
        "Action '",
        "Niveau de sécurité:",
        "Commande réussie:",
        "GOOGLE_API_KEY non trouvée",
        "OBSIDIAN_VAULT_PATH non trouvée",
    ]
    for pat in ignore_patterns:
        if pat in msg:
            return None

    if level in ("ERROR", "WARNING") and not any(
        k in msg for k in ["J'ai", "Je ", "L'app", "Le texte", "Dossier", "Fichier", "Commande", "C'est"]
    ):
        clean = msg.replace("Erreur lors de l'exécution de la tâche:", "").strip()
        clean = clean.replace("Erreur lors du parsing LLM de l'action:", "").strip()
        return f"J'ai rencontré un souci : {clean}" if clean else "J'ai rencontré un problème inattendu."

    clean = msg
    for prefix in ("[INFO]", "[WARNING]", "[ERROR]", "[DEBUG]"):
        clean = clean.replace(prefix, "").strip()
    return clean if clean else None


# ─────────────────────────────────────────────────────────────
#  WEB CALLBACKS
# ─────────────────────────────────────────────────────────────
class WebCallbacks:
    """Callbacks for Orchestrator to communicate with WebSocket."""

    async def log_message(self, level: str, message: str):
        human = humanize_log(level, message)
        if human is None:
            return
        await self.send_message(human)

    async def send_message(self, text: str):
        """Send a conversational message and add to history."""
        _add_to_history("agent", text)
        await manager.broadcast(json.dumps({
            "type": "log",
            "level": "INFO",
            "message": text
        }))

    async def request_confirmation(self, action_type: str, params: dict) -> bool:
        global pending_confirmation
        pending_confirmation = asyncio.Future()

        action_labels = {
            "system_command": f"exécuter la commande : `{params.get('command', '')}`",
            "move_file":      f"déplacer `{params.get('src', '')}` vers `{params.get('dst', '')}`",
            "copy_file":      f"copier `{params.get('src', '')}` vers `{params.get('dst', '')}`",
            "app_close":      f"fermer l'application `{params.get('app_name', '')}`",
        }
        human_desc = action_labels.get(action_type, f"effectuer l'action `{action_type}`")
        msg = f"J'ai besoin de ta confirmation pour {human_desc}. Tu valides ?"

        _add_to_history("agent", msg)
        await manager.broadcast(json.dumps({
            "type": "confirmation_request",
            "action_type": action_type,
            "params": params,
            "message": msg
        }))

        try:
            result = await asyncio.wait_for(pending_confirmation, timeout=300.0)
            return result
        except asyncio.TimeoutError:
            await self.send_message("Tu as mis trop de temps à répondre, j'annule cette action par précaution.")
            return False
        finally:
            pending_confirmation = None

callbacks = WebCallbacks()


# ─────────────────────────────────────────────────────────────
#  WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    # Message de bienvenue à la connexion
    welcome = "Bonjour ! Je suis Hacktoberfest, ton agent autonome. Je suis prêt — dis-moi ce que tu veux faire."
    await websocket.send_text(json.dumps({"type": "log", "level": "INFO", "message": welcome}))
    _add_to_history("agent", welcome)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "instruction":
                instruction = message["instruction"]
                asyncio.create_task(handle_message(instruction))

            elif message["type"] == "confirmation_response":
                global pending_confirmation
                if pending_confirmation and not pending_confirmation.done():
                    pending_confirmation.set_result(message["approved"])

            elif message["type"] == "voice_start":
                asyncio.create_task(_listen_voice(websocket))

            elif message["type"] == "voice_stop":
                from agent.voice.listener import cancel_listen

                cancel_listen()

            elif message["type"] == "stop":
                if orchestrator_instance:
                    orchestrator_instance.stop()
                    await callbacks.send_message("D'accord, j'arrête ce que je fais.")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ─────────────────────────────────────────────────────────────
#  MESSAGE HANDLER — conversation ou commande
# ─────────────────────────────────────────────────────────────
_voice_lock = asyncio.Lock()


async def _listen_voice(websocket: WebSocket) -> None:
    """Écoute une phrase au micro et la renvoie à l'interface."""
    if _voice_lock.locked():
        await websocket.send_text(json.dumps({"type": "voice_status", "state": "busy"}))
        return

    from agent.voice.listener import listen_once

    loop = asyncio.get_running_loop()

    def _on_partial(text: str) -> None:
        if not text:
            return
        payload = json.dumps({"type": "voice_partial", "text": text})
        asyncio.run_coroutine_threadsafe(websocket.send_text(payload), loop)

    levels: list[int] = []

    def _on_level(level: int) -> None:
        levels.append(level)
        payload = json.dumps({"type": "voice_level", "level": level})
        asyncio.run_coroutine_threadsafe(websocket.send_text(payload), loop)

    async with _voice_lock:
        await websocket.send_text(json.dumps({"type": "voice_status", "state": "listening"}))
        try:
            text = await loop.run_in_executor(None, lambda: listen_once(_on_partial, _on_level))
        except Exception as exc:
            logger.error("Écoute vocale: %s", exc)
            await websocket.send_text(json.dumps({
                "type": "voice_status",
                "state": "error",
                "message": "Je n'arrive pas à utiliser le microphone. Vérifie qu'il est branché et autorisé pour les applications de bureau.",
            }))
            return

        if text is None:
            await websocket.send_text(json.dumps({"type": "voice_status", "state": "idle"}))
            return

        peak = max(levels) if levels else 0
        hint = ""
        if not text and peak < 8:
            hint = (
                "Je ne reçois aucun son. Le micro utilisé est celui de l'ordinateur : "
                "le casque n'est pas branché. Parle près de l'écran."
            )
        await websocket.send_text(json.dumps({
            "type": "voice_result",
            "text": text,
            "level": peak,
            "hint": hint,
        }))


async def handle_message(instruction: str):
    """Route le message : conversation naturelle OU exécution de tâche."""
    _add_to_history("user", instruction)

    # Demander à Gemini de classifier le message
    routed = await chat_router(instruction)

    if routed.get("type") == "chat":
        # Réponse conversationnelle directe
        await callbacks.send_message(routed.get("response", "..."))

    elif routed.get("type") == "command":
        # Annoncer ce qu'on va faire
        ack = routed.get("ack", f"Je m'en occupe : {instruction}")
        await callbacks.send_message(ack)

        # ⚠️ On passe TOUJOURS l'instruction originale à l'orchestrateur.
        # Le fast_parser s'appuie sur les mots exacts de l'utilisateur.
        # La reformulation du LLM (routed["task"]) est ignorée ici.
        await run_agent(instruction)

    else:
        await callbacks.send_message("Je ne suis pas sûr de comprendre. Peux-tu reformuler ?")



async def run_agent(instruction: str):
    global orchestrator_instance, current_session_id

    db_path = os.getenv("DB_PATH", "./agent.db")
    orchestrator_instance = Orchestrator(db_path=db_path)
    orchestrator_instance.callbacks = callbacks

    current_session_id = await orchestrator_instance.run(instruction)
    await callbacks.send_message("C'est tout bon. Autre chose pour toi ?")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
