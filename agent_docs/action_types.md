# Types d'Actions

## Vue d'ensemble

Liste exhaustive des types d'actions supportées par l'agent, classées par module.

## Actions Souris (actions/mouse.py)

### mouse_click

Clique sur une position de l'écran.

**Paramètres :**
```json
{
  "x": 500,
  "y": 300,
  "button": "left",  // left, right, middle
  "clicks": 1
}
```

**Niveau de sécurité :** RISKY

### mouse_drag

Fait un glisser-déposer.

**Paramètres :**
```json
{
  "start_x": 100,
  "start_y": 100,
  "end_x": 500,
  "end_y": 500,
  "duration": 0.5  // secondes
}
```

**Niveau de sécurité :** RISKY

### mouse_scroll

Fait défiler l'écran.

**Paramètres :**
```json
{
  "x": 500,
  "y": 300,
  "clicks": 5,  // positif = vers le bas, négatif = vers le haut
  "direction": "down"  // up, down
}
```

**Niveau de sécurité :** RISKY

### mouse_move

Déplace la souris sans cliquer.

**Paramètres :**
```json
{
  "x": 500,
  "y": 300,
  "duration": 0.2
}
```

**Niveau de sécurité :** RISKY

## Actions Clavier (actions/keyboard.py)

### keyboard_type

Tape du texte.

**Paramètres :**
```json
{
  "text": "hello world",
  "interval": 0.01  // délai entre chaque caractère
}
```

**Niveau de sécurité :** RISKY

### keyboard_press

Appuie sur une touche ou combinaison.

**Paramètres :**
```json
{
  "key": "enter"  // enter, escape, ctrl+c, etc.
}
```

**Niveau de sécurité :** RISKY

### keyboard_hotkey

Combinaison de touches (hotkey).

**Paramètres :**
```json
{
  "keys": ["ctrl", "c"]  // ctrl+c, ctrl+v, alt+tab, etc.
}
```

**Niveau de sécurité :** RISKY

## Actions Applications (actions/apps.py)

### app_open

Ouvre une application.

**Paramètres :**
```json
{
  "app_name": "chrome",  // chrome, notepad, excel, etc.
  "args": []  // arguments optionnels
}
```

**Niveau de sécurité :** RISKY

### app_close

Ferme une application.

**Paramètres :**
```json
{
  "app_name": "chrome",
  "force": false  // force close si true
}
```

**Niveau de sécurité :** RISKY

### app_focus

Met le focus sur une application.

**Paramètres :**
```json
{
  "app_name": "chrome"
}
```

**Niveau de sécurité :** RISKY

## Actions Vision (vision/capture.py)

### screen_capture

Prend une capture d'écran.

**Paramètres :**
```json
{
  "region": null  // null = écran complet, ou {"top": 0, "left": 0, "width": 1920, "height": 1080}
}
```

**Niveau de sécurité :** SAFE

### element_capture

Prend une capture d'une région spécifique.

**Paramètres :**
```json
{
  "element_id": "abc123",
  "bbox": {"x": 100, "y": 100, "width": 200, "height": 50}
}
```

**Niveau de sécurité :** SAFE

## Actions OCR (vision/ocr.py)

### ocr_extract

Extrait le texte d'une capture.

**Paramètres :**
```json
{
  "image_path": "/path/to/image.png",
  "language": ["en", "fr"]  // langues à détecter
}
```

**Niveau de sécurité :** SAFE

### ocr_search

Recherche du texte dans une capture.

**Paramètres :**
```json
{
  "image_path": "/path/to/image.png",
  "search_text": "button",
  "language": ["en"]
}
```

**Niveau de sécurité :** SAFE

## Actions Analyse (vision/analyzer.py)

### analyze_screen

Analyse une capture avec l'LLM vision.

**Paramètres :**
```json
{
  "image_path": "/path/to/image.png",
  "question": "Que vois-tu sur cette image ?",
  "context": "L'utilisateur cherche le bouton de connexion"
}
```

**Niveau de sécurité :** SAFE

### find_element

Trouve un élément spécifique sur l'écran.

**Paramètres :**
```json
{
  "image_path": "/path/to/image.png",
  "element_description": "bouton de connexion bleu",
  "context": "Page de login"
}
```

**Niveau de sécurité :** SAFE

## Actions Fichier (non implémentées dans v1)

### file_write

Écrit dans un fichier.

**Paramètres :**
```json
{
  "path": "/path/to/file.txt",
  "content": "contenu du fichier",
  "mode": "write"  // write, append
}
```

**Niveau de sécurité :** CRITICAL

### file_delete

Supprime un fichier.

**Paramètres :**
```json
{
  "path": "/path/to/file.txt"
}
```

**Niveau de sécurité :** CRITICAL

## Actions Système (non implémentées dans v1)

### system_command

Exécute une commande système.

**Paramètres :**
```json
{
  "command": "dir",
  "args": []
}
```

**Niveau de sécurité :** CRITICAL

## Conventions

- Tous les paramètres sont en JSON
- Les coordonnées sont en pixels (origine en haut à gauche)
- Les durées sont en secondes
- Les chemins sont absolus
- Les niveaux de sécurité sont définis dans `security.py`
