# Règles de Sécurité

## Classification des Actions

Toute action générée par l'agent DOIT être classifiée via `security.classify(action)` avant exécution.

### Niveaux de Classification

| Niveau | Type d'action | Validation requise | Comportement |
|--------|--------------|-------------------|--------------|
| `SAFE` | Lecture, capture écran, OCR, navigation | Aucune — exécution directe | Exécutée immédiatement sans confirmation |
| `RISKY` | Clic, saisie clavier, écriture fichier, ouverture app | Aperçu affiché à l'utilisateur | L'utilisateur voit l'action et peut l'annuler |
| `CRITICAL` | Suppression fichier, envoi message, modification système | Confirmation "OUI" explicite | L'utilisateur doit taper "OUI" pour confirmer |

## Liste Noire Absolue

Ces opérations ne peuvent JAMAIS être exécutées sans validation explicite de l'utilisateur, même si demandé :

- `os.remove`, `os.unlink`, `shutil.rmtree`, `rmdir` — toute suppression de fichier
- `DROP TABLE`, `DELETE FROM`, `TRUNCATE` sans transaction rollback
- Envoi de messages, emails, ou publication sur le réseau
- Modification du registre Windows (`RegDeleteKey`, `RegDeleteValue`)
- `format`, `rd /s`, ou toute commande shell destructive
- `git push`, `git commit --amend` sans confirmation

## Chemins Protégés

L'agent ne doit JAMAIS écrire ou modifier ces chemins :

```python
PROTECTED_PATHS = [
    "~/Documents",
    "~/Pictures",
    "~/Desktop",
    "C:/Windows",
    "C:/Program Files",
    "C:/Program Files (x86)",
    "~/.ssh",
    "~/.env",
    "~/.gitconfig",
    "~/AppData/Roaming",
]
```

Toute tentative d'action sur ces chemins doit être bloquée avec une erreur explicite.

## Bouton d'Arrêt d'Urgence

L'agent DOIT toujours écouter ces raccourcis clavier pour s'arrêter immédiatement :

- `Échap` (Escape) — arrêt immédiat de l'action en cours
- `Ctrl+Shift+Q` — arrêt complet de l'agent

Ces listeners doivent être actifs en permanence et avoir la priorité maximale.

## Validation Multi-Étapes

Pour les actions CRITICAL :

1. Afficher un aperçu détaillé de ce qui va se passer
2. Demander confirmation explicite (l'utilisateur doit taper "OUI")
3. Attendre 3 secondes de délai avant exécution (possibilité d'annuler)
4. Logger la décision dans la base de données

## Mode Lecture Seule

Si `READONLY_MODE=true` dans `.env` :
- Aucune action de type RISKY ou CRITICAL ne peut être exécutée
- Seules les actions SAFE sont permises
- L'agent fonctionne en mode observation uniquement

## Audit Trail

Toutes les décisions de sécurité sont loggées dans la table `action` avec :
- `security_level` : SAFE, RISKY, ou CRITICAL
- `user_approved` : booléen indiquant si l'utilisateur a approuvé
- `blocked_reason` : raison du blocage si applicable
