Parfait — voici un **README.md complet, propre et prêt à mettre sur GitHub**, avec sections, format pro et clair. Tu peux copier-coller directement dans ton dépôt.

---

# 🎮 Blue Prince — Python Game

Un projet simplifié du jeu *Blue Prince*, développé en Python avec **pygame**.
Le jeu peut fonctionner **avec ou sans images** : si aucune image n’est fournie, il affichera automatiquement des placeholders colorés.

---

## 📦 Requirements

Créez un fichier `requirements.txt` contenant :

```
pygame
```

---

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

*(Alternative si vous n’utilisez pas le fichier requirements :)*

```bash
pip install pygame
```

---

## 🖼️ Configuration des Images (optionnel)

Pour un rendu visuel plus fidèle :

1. Placez le fichier `.py` du jeu dans un dossier projet.
2. Créez dans ce dossier un sous-dossier nommé :

```
images
```

3. Déposez-y toutes les images nécessaires
   (ex : `Entrance_Hall_Icon.webp`, `Kitchen_Icon.webp`, etc.).

> Si aucune image n’est trouvée, le jeu utilisera des blocs colorés comme alternative.

---

## ▶️ Lancer le Jeu

Placez-vous dans le répertoire qui contient le fichier principal du jeu, puis exécutez :

```bash
python votre_fichier_jeu.py
```

*(Remplacez `votre_fichier_jeu.py` par le nom réel du fichier.)*

---

## 🎮 Contrôles (AZERTY)

| Action                       | Touche          |
| ---------------------------- | --------------- |
| Déplacement Haut             | Z / ↑           |
| Déplacement Bas              | S / ↓           |
| Déplacement Gauche           | Q / ←           |
| Déplacement Droite           | D / →           |
| Interagir (porte / objet)    | ESPACE / E      |
| Confirmer une pièce          | ENTER           |
| Redessiner options de pièces | R (coûte un dé) |
| Quitter le jeu               | ESC             |

---

## 🧩 Fonctionnement du Jeu (Résumé rapide)

* Déplacement du joueur dans un manoir généré pièce par pièce.
* Chaque pièce peut contenir :
  objets, portes, interactions, choix aléatoires.
* Le joueur utilise des **dés (dice)** pour redessiner des options.
* Objectif : explorer, sélectionner, progresser.

---

## 💡 Notes

* Compatible Python 3.8+
* Aucune installation complexe : un simple `pygame` suffit.
* Le jeu reste fonctionnel même sans dossier `images/`.

---

