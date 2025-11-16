# Blue Prince — Version Python (Projet simplifié)

Ce dépôt contient une version simplifiée et jouable du jeu Blue Prince, développée en Python avec la bibliothèque pygame.  
Le projet met en œuvre l’exploration progressive du manoir, la sélection de pièces compatibles, la gestion d’un inventaire, les portes verrouillées, les objets interactifs et un système de boutique.

Le jeu fonctionne avec ou sans images. Si aucune ressource graphique n’est fournie, un affichage minimaliste (placeholders colorés) est utilisé automatiquement.

---

## Structure du projet

```
projet-jeu-python-main/
│
├── entities.py                 ← fichier principal
│
├── model/
│   ├── pictures/rooms/         ← images des salles (optionnelles)
│   ├── items/                  ← icônes des ressources
│   └── ...
│
└── README.md
```

---

## Prérequis

Le projet nécessite :

- Python 3.9 ou plus
- La bibliothèque pygame

Fichier requirements.txt :

```
pygame>=2.6
```

Installation :

```bash
pip install -r requirements.txt
```

ou simplement :

```bash
pip install pygame
```

---

## Lancer le jeu

Depuis le répertoire principal (contenant entities.py) :

```bash
python entities.py
```

---

## Utilisation des images (optionnelle)

Les images des salles doivent être placées dans :

```
model/pictures/rooms/
```

Les icônes des ressources doivent être placées dans :

```
model/items/
```

Si ces dossiers sont absents ou vides, le jeu reste entièrement fonctionnel grâce aux placeholders colorés utilisés par défaut.

---

## Commandes (AZERTY)

| Action                                      | Touche(s)            |
|---------------------------------------------|-----------------------|
| Déplacement vers le haut                    | Z ou flèche haut      |
| Déplacement vers le bas                     | S ou flèche bas       |
| Déplacement vers la gauche                  | Q ou flèche gauche    |
| Déplacement vers la droite                  | D ou flèche droite    |
| Interaction (porte, coffre, casier, shop)   | E                     |
| Confirmer le placement d’une pièce          | Entrée                |
| Repiocher les pièces proposées (coûte 1 dé) | R                     |
| Quitter le jeu                              | Échap                 |

---

## Fonctionnement général

### Génération du manoir
Le manoir est une grille de 9 lignes sur 5 colonnes.  
Le joueur commence dans l’Entrance Hall (bas du manoir) et doit atteindre l’Antechamber (haut du manoir).

À chaque tentative d’entrée dans une case vide, le jeu génère automatiquement une sélection de 1 à 3 pièces compatibles selon :

- la direction d’arrivée,
- les portes de la pièce,
- la position (bord, centre, coin),
- le coût en gemmes,
- une rotation automatique garantissant un placement valide.

Le joueur choisit une pièce ou repioche une nouvelle sélection en utilisant un dé.

### Deck et rareté
Chaque salle a un degré de rareté déterminant :

- le nombre de copies dans le deck initial,
- la probabilité d’être tirée.

Le jeu garantit qu’au moins une pièce à coût nul est proposée lorsqu’elle est possible.

### Inventaire
L’inventaire comprend des consommables (pas, pièces, gemmes, clés, dés) et des objets permanents (pelle, marteau, kit de crochetage, détecteur de métaux, patte de lapin).

### Portes et verrous
Les portes sont associées à un niveau de verrouillage dépendant de la profondeur dans le manoir :

- niveau 0 : passage libre
- niveau 1 : kit ou clé
- niveau 2 : clé obligatoire

Une fenêtre de confirmation est affichée lorsque l’ouverture nécessite une ressource.

### Objets interactifs
Certaines salles génèrent des objets interactifs :

- coffre
- casier
- site de fouille

Chacun possède sa logique de loot et un état ouvert/fermé.

### Effets de salles
Les salles peuvent appliquer des effets lors :

- du tirage (on_draw),
- de l’entrée (on_enter).

Exemples : gain de ressources, apparition d’un shop, objets permanents, dispersion de ressources dans le manoir.

### Conditions de fin
- Victoire : entrer dans l’Antechamber.  
- Défaite : absence de pas disponibles.

---

## Notes techniques

- Le projet repose sur un seul fichier Python regroupant l’ensemble de la logique et de l’affichage.
- Le rendu graphique comprend : grille, portes, verrous, sélection de pièces, inventaire, messages contextuels, boutique, popups.
- Le jeu reste pleinement jouable sans ressources graphiques.

---