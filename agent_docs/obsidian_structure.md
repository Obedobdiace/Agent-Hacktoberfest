# Structure Obsidian

## Vue d'ensemble

L'agent génère automatiquement des notes dans le vault Obsidian défini par `OBSIDIAN_VAULT_PATH`.

## Structure du Vault

```
vault/
├── Sessions/           → Une note par session
├── Tâches/             → Log des tâches et sous-tâches
├── Erreurs/            → Cas d'échec pour amélioration future
├── KB/                 → Connaissances apprises par application
└── Recherches/         → Notes de recherche structurée
```

## Templates de Notes

### Session

**Chemin :** `Sessions/YYYY-MM-DD_HH-MM_session.md`

```markdown
---
date: 2024-01-15
tags: [session]
---

# Session 2024-01-15 14:30

## Instruction Initiale
[Instruction de l'utilisateur]

## Résumé
[Résumé automatique de ce qui a été accompli]

## Tâches Exécutées
- [x] Tâche 1
- [x] Tâche 2
- [ ] Tâche 3 (non complétée)

## Actions
- [14:31] Capture écran
- [14:32] Clic sur bouton (RISKY - approuvé)
- [14:33] Saisie "google.com" (RISKY - approuvé)

## Statut
✅ Terminée avec succès / ❌ Échec / ⚠️ Annulée

## Notes
[Notes additionnelles]
```

### Tâche

**Chemin :** `Tâches/YYYY-MM-DD_tache_[id].md`

```markdown
---
date: 2024-01-15
tags: [tache]
---

# Tâche : [Description]

## Contexte
Session : [ID session]
Instruction : [Instruction initiale]

## Sous-tâches
- [x] Sous-tâche 1
- [x] Sous-tâche 2
- [ ] Sous-tâche 3

## Actions Exécutées
[Liste des actions avec timestamps]

## Résultat
✅ Succès / ❌ Échec

## Erreurs (si applicable)
[Description des erreurs rencontrées]
```

### Erreur

**Chemin :** `Erreurs/YYYY-MM-DD_erreur_[type].md`

```markdown
---
date: 2024-01-15
tags: [erreur]
---

# Erreur : [Type]

## Contexte
Session : [ID session]
Tâche : [ID tâche]
Action tentée : [Description]

## Description de l'Erreur
[Message d'erreur détaillé]

## Screenshot
[Chemin vers la capture d'écran]

## Analyse
[Pourquoi cela a échoué]

## Suggestions d'Amélioration
- [ ] Suggestion 1
- [ ] Suggestion 2
```

### Connaissance (KB)

**Chemin :** `KB/[Application]/[Catégorie]/[Titre].md`

```markdown
---
date: 2024-01-15
tags: [kb, application]
application: [Nom de l'application]
categorie: [Catégorie]
---

# [Titre]

## Application
[Nom de l'application]

## Description
[Description de la connaissance]

## Comment l'utiliser
[Instructions d'utilisation]

## Exemples
[Exemples concrets]

## Date de découverte
2024-01-15
```

### Recherche

**Chemin :** `Recherches/YYYY-MM-DD_[Sujet].md`

```markdown
---
date: 2024-01-15
tags: [recherche]
---

# Recherche : [Sujet]

## Question
[Question initiale]

## Méthodologie
[Comment la recherche a été menée]

## Résultats
[Résultats trouvés]

## Sources
- [Source 1](URL)
- [Source 2](URL)

## Conclusions
[Conclusions tirées]
```

## Conventions de Nommage

### Sessions
- Format : `YYYY-MM-DD_HH-MM_session.md`
- Exemple : `2024-01-15_14-30_session.md`

### Tâches
- Format : `YYYY-MM-DD_tache_[id].md`
- Exemple : `2024-01-15_tache_abc123.md`

### Erreurs
- Format : `YYYY-MM-DD_erreur_[type].md`
- Exemple : `2024-01-15_erreur_element_not_found.md`

### KB
- Format : `[Application]/[Catégorie]/[Titre].md`
- Exemple : `Chrome/Raccourcis/Nouvelle_Onglet.md`

### Recherches
- Format : `YYYY-MM-DD_[Sujet].md`
- Exemple : `2024-01-15_Comment_automatiser_Excel.md`

## Intégration avec le Code

Toute écriture dans Obsidian DOIT passer par `obsidian/logger.py` :

```python
from agent.obsidian.logger import ObsidianLogger

logger = ObsidianLogger()

# Créer une note de session
logger.create_session_note(
    session_id="abc123",
    instruction="Ouvrir Chrome",
    resume="Chrome ouvert avec succès"
)

# Logger une erreur
logger.log_error(
    session_id="abc123",
    error_type="element_not_found",
    description="Bouton non trouvé",
    screenshot_path="/path/to/screenshot.png"
)
```

## Frontmatter

Toutes les notes doivent inclure du frontmatter YAML avec :
- `date` : Date de création
- `tags` : Tags pour la recherche
- Champs spécifiques selon le type de note
