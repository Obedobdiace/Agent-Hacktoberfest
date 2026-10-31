"""Module pour les actions sur le système de fichiers."""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

class FileSystemController:
    """Contrôleur pour les opérations sur le système de fichiers."""

    def __init__(self) -> None:
        """Initialise le contrôleur du système de fichiers."""
        pass

    def create_directory(self, path_str: str) -> bool:
        """Crée un dossier.

        Args:
            path_str: Chemin du dossier à créer.

        Returns:
            True si succès, False sinon.
        """
        path = Path(path_str)
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Dossier créé: {path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier {path}: {e}")
            return False

    def list_directory(self, path_str: str) -> list[str]:
        """Liste le contenu d'un dossier.

        Args:
            path_str: Chemin du dossier.

        Returns:
            Liste des noms de fichiers et dossiers.
        """
        path = Path(path_str).expanduser()
        try:
            if not path.exists() or not path.is_dir():
                logger.error(f"Dossier introuvable ou invalide: {path}")
                return []
            
            items = [item.name for item in path.iterdir()]
            logger.info(f"Contenu de {path} listé ({len(items)} éléments)")
            return items
        except Exception as e:
            logger.error(f"Erreur lors du listage de {path}: {e}")
            return []

    def move_file(self, src_str: str, dst_str: str) -> bool:
        """Déplace un fichier ou un dossier.

        Args:
            src_str: Chemin source.
            dst_str: Chemin destination.

        Returns:
            True si succès, False sinon.
        """
        src = Path(src_str)
        dst = Path(dst_str)
        try:
            if not src.exists():
                logger.error(f"Source introuvable: {src}")
                return False
            
            # Si destination est un dossier, on déplace dedans
            if dst.is_dir():
                shutil.move(str(src), str(dst / src.name))
            else:
                shutil.move(str(src), str(dst))
            
            logger.info(f"Élément déplacé de {src} vers {dst}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du déplacement de {src} vers {dst}: {e}")
            return False

    def copy_file(self, src_str: str, dst_str: str) -> bool:
        """Copie un fichier ou un dossier.

        Args:
            src_str: Chemin source.
            dst_str: Chemin destination.

        Returns:
            True si succès, False sinon.
        """
        src = Path(src_str)
        dst = Path(dst_str)
        try:
            if not src.exists():
                logger.error(f"Source introuvable: {src}")
                return False

            if src.is_dir():
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(dst))
            
            logger.info(f"Élément copié de {src} vers {dst}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la copie de {src} vers {dst}: {e}")
            return False

    def read_file(self, path_str: str) -> str:
        """Lit le contenu d'un fichier."""
        path = Path(path_str).expanduser()
        try:
            if not path.exists() or not path.is_file():
                return f"Erreur: Le fichier {path} n'existe pas ou n'est pas un fichier."
            return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Erreur de lecture {path}: {e}")
            return f"Erreur de lecture: {e}"

    def write_file(self, path_str: str, content: str, mode: str = "w") -> bool:
        """Écrit du contenu dans un fichier."""
        path = Path(path_str).expanduser()
        try:
            # S'assurer que le dossier parent existe
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if mode == "a":
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                path.write_text(content, encoding="utf-8")
                
            logger.info(f"Fichier écrit: {path}")
            return True
        except Exception as e:
            logger.error(f"Erreur d'écriture {path}: {e}")
            return False

    def delete_file(self, path_str: str) -> bool:
        """Supprime un fichier ou un dossier vide."""
        path = Path(path_str).expanduser()
        try:
            if not path.exists():
                return False
            if path.is_dir():
                path.rmdir() # Seulement si vide
            else:
                path.unlink()
            logger.info(f"Fichier/Dossier supprimé: {path}")
            return True
        except Exception as e:
            logger.error(f"Erreur de suppression {path}: {e}")
            return False
