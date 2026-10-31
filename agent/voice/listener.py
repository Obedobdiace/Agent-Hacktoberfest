"""Écoute une phrase au microphone avec le reconnaisseur Windows (hors ligne).

Le moteur de reconnaissance reste ouvert : le premier chargement est lent,
les écoutes suivantes répondent dès que la phrase est finie.
"""

from __future__ import annotations

import base64
import logging
import subprocess
import threading

logger = logging.getLogger(__name__)

_CREATE_NO_WINDOW = 0x08000000

_SCRIPT = r"""
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo 'fr-FR'
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine $culture
try {
    $engine.SetInputToDefaultAudioDevice()
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $engine.InitialSilenceTimeout = [TimeSpan]::FromSeconds(10)
    $engine.BabbleTimeout = [TimeSpan]::FromSeconds(12)
    $engine.EndSilenceTimeout = [TimeSpan]::FromSeconds(1.4)
    try { $engine.UpdateRecognizerSetting('CFGConfidenceRejectionThreshold', 10) } catch {}
    [Console]::Out.WriteLine('READY')
    [Console]::Out.Flush()
    while ($true) {
        $cmd = [Console]::In.ReadLine()
        if ([string]::IsNullOrEmpty($cmd) -or $cmd -eq 'STOP') { break }
        if ($cmd -ne 'LISTEN') { continue }
        $gate = New-Object System.Threading.ManualResetEvent $false
        $builder = New-Object System.Text.StringBuilder
        $pack = @($gate, $builder)
        $null = Register-ObjectEvent -InputObject $engine -EventName SpeechHypothesized -MessageData $pack -Action {
            $text = $EventArgs.Result.Text
            if ($text) {
                [Console]::Out.WriteLine('PARTIAL:' + $text)
                [Console]::Out.Flush()
            }
        }
        $null = Register-ObjectEvent -InputObject $engine -EventName SpeechRecognized -MessageData $pack -Action {
            $text = $EventArgs.Result.Text
            if ($text) {
                $hold = $Event.MessageData[1]
                [void]$hold.Clear()
                [void]$hold.Append($text)
                [Console]::Out.WriteLine('PARTIAL:' + $text)
                [Console]::Out.Flush()
            }
            $Event.MessageData[0].Set()
        }
        $null = Register-ObjectEvent -InputObject $engine -EventName RecognizeCompleted -MessageData $pack -Action {
            $Event.MessageData[0].Set()
        }
        try {
            $engine.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Single)
            $deadline = (Get-Date).AddSeconds(28)
            while (-not $gate.WaitOne(0) -and (Get-Date) -lt $deadline) {
                Wait-Event -Timeout 0.25 | Out-Null
                try {
                    [Console]::Out.WriteLine('LEVEL:' + $engine.AudioLevel)
                    [Console]::Out.Flush()
                } catch {}
            }
            $heard = $builder.ToString()
            if ($heard) {
                [Console]::Out.WriteLine('TEXT:' + $heard)
            } else {
                [Console]::Out.WriteLine('TEXT:')
            }
        } catch {
            [Console]::Out.WriteLine('ERR:' + $_.Exception.Message)
        } finally {
            try { $engine.RecognizeAsyncCancel() } catch {}
            Get-EventSubscriber | Where-Object { $_.SourceObject -eq $engine } | ForEach-Object { Unregister-Event -SourceIdentifier $_.SourceIdentifier }
            [Console]::Out.Flush()
        }
    }
} finally {
    $engine.Dispose()
}
"""

_lock = threading.Lock()
_cancel = threading.Event()
_process: subprocess.Popen[str] | None = None


def _readline(pipe, timeout: float) -> str:
    box: list[str] = []

    def _read() -> None:
        box.append(pipe.readline())

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError
    return box[0] if box else ""


def _stop_process() -> None:
    global _process
    process = _process
    _process = None
    if process is None or process.poll() is not None:
        return
    try:
        if process.stdin:
            process.stdin.write("STOP\n")
            process.stdin.flush()
    except OSError:
        process.kill()
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()


def cancel_listen() -> None:
    """Interrompt l'écoute en cours. Ne prend pas le verrou : listen_once le tient."""
    _cancel.set()
    process = _process
    if process is not None and process.poll() is None:
        process.kill()


def _ensure_engine() -> subprocess.Popen[str]:
    """Démarre le reconnaisseur s'il n'est pas déjà prêt. À appeler sous _lock."""
    global _process
    if _process is not None and _process.poll() is None:
        return _process

    encoded = base64.b64encode(_SCRIPT.encode("utf-16le")).decode("ascii")
    try:
        process = subprocess.Popen(
            ["powershell", "-NoProfile", "-STA", "-EncodedCommand", encoded],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_CREATE_NO_WINDOW,
        )
    except OSError as exc:
        logger.error("Impossible de lancer la reconnaissance vocale: %s", exc)
        raise RuntimeError("reconnaissance vocale indisponible") from exc

    _process = process
    try:
        ready = _readline(process.stdout, 60)
    except TimeoutError as exc:
        _stop_process()
        raise RuntimeError("le reconnaisseur vocal n'a pas démarré") from exc

    if process.poll() is not None or not ready.startswith("READY"):
        _stop_process()
        logger.error("Reconnaissance vocale: démarrage refusé (%r)", ready.strip())
        raise RuntimeError("reconnaissance vocale indisponible")
    logger.info("Reconnaisseur vocal prêt")
    return process


def warm_engine() -> None:
    """Charge le reconnaisseur en avance, au démarrage du serveur."""
    try:
        with _lock:
            _ensure_engine()
    except Exception:
        logger.exception("Échec du préchargement du reconnaisseur vocal")


def listen_once(on_partial=None, on_level=None) -> str | None:
    """Retourne la phrase entendue. on_partial et on_level informent l'interface en direct."""
    import time

    _cancel.clear()
    with _lock:
        if _cancel.is_set():
            return None
        process = _ensure_engine()
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("reconnaissance vocale indisponible")
        try:
            process.stdin.write("LISTEN\n")
            process.stdin.flush()
            deadline = time.monotonic() + 32
            line = ""
            while time.monotonic() < deadline:
                line = _readline(process.stdout, max(0.5, deadline - time.monotonic())).strip()
                if line.startswith("PARTIAL:"):
                    if on_partial is not None:
                        on_partial(line[8:].strip())
                    continue
                if line.startswith("LEVEL:"):
                    if on_level is not None:
                        try:
                            on_level(int(line[6:] or "0"))
                        except ValueError:
                            pass
                    continue
                if line.startswith("PROBLEM:"):
                    continue
                break
        except (OSError, TimeoutError) as exc:
            logger.warning("Écoute vocale interrompue: %s", exc)
            _stop_process()
            if _cancel.is_set():
                return None
            return ""

    if _cancel.is_set():
        return None
    text = line.strip()
    if text.startswith("ERR:"):
        logger.error("Reconnaissance vocale: %s", text[4:])
        raise RuntimeError(text[4:] or "reconnaissance vocale indisponible")
    if text.startswith("TEXT:"):
        return text[5:].strip()
    if text.startswith("PARTIAL:"):
        return text[8:].strip()
    return ""
