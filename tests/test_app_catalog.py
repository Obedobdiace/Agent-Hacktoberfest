"""Résolution des applications installées, sans lancer de programme."""

from agent.actions.app_catalog import AppCatalog, InstalledApp, best_match
from agent.core.fast_parser import FastParser


def _app(name: str, norm: str, target: str = "app.exe") -> InstalledApp:
    return InstalledApp(name=name, norm=norm, target=target, kind="exe", process_name=name)


def test_exact_name_wins() -> None:
    apps = [_app("Spotify", "spotify"), _app("Spotify Premium Helper", "spotify premium helper")]
    hit, score = best_match("spotify", apps)
    assert hit is not None
    assert hit.name == "Spotify"
    assert score == 1.0


def test_chrome_prefers_the_browser() -> None:
    apps = [
        _app("Google Chrome", "google chrome"),
        _app("Chrome Remote Desktop", "chrome remote desktop"),
    ]
    hit, _score = best_match("chrome", apps)
    assert hit is not None
    assert hit.name == "Google Chrome"


def test_generic_microsoft_is_ambiguous() -> None:
    apps = [
        _app("Microsoft Edge", "microsoft edge"),
        _app("Microsoft Store", "microsoft store"),
    ]
    hit, _score = best_match("microsoft", apps)
    assert hit is None


def test_word_does_not_open_wordpad() -> None:
    hit, score = best_match("word", [_app("WordPad", "wordpad")])
    assert hit is None
    assert score < 0.84


def test_catalog_uses_aliases_and_system_apps() -> None:
    catalog = AppCatalog(
        apps=[
            _app("Visual Studio Code", "visual studio code", r"C:\fake\Code.exe"),
            _app("Spotify", "spotify", r"C:\fake\Spotify.exe"),
        ]
    )
    assert catalog.resolve("code") is not None
    assert catalog.resolve("code").name == "Visual Studio Code"
    assert catalog.resolve("spotify").name == "Spotify"
    assert catalog.resolve("bloc-notes").target == "notepad.exe"
    assert catalog.resolve("calculatrice").target == "calc.exe"
    assert catalog.resolve("cette-application-n-existe-pas") is None


def test_parse_open_and_close_without_model() -> None:
    parser = FastParser()
    assert parser.parse_app_action("ouvre spotify") == ("open", "spotify")
    assert parser.parse_app_action("Ouvre l'application Bloc-notes") == ("open", "bloc-notes")
    assert parser.parse_app_action("ferme chrome s'il te plaît") == ("close", "chrome")
    assert parser.parse_app_action("lance une recherche sur les chats") is None
    assert parser.parse("ouvre chrome") is None
    assert parser.parse("luminosité à 40") is not None
