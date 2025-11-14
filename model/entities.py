"""
Blue Prince - simplified project implementation (single file).
Place images in an 'images/' folder next to this file. Works even without images.
Controls (AZERTY):
  Z = up, Q = left, S = down, D = right
  SPACE = open door / move
  ENTER = choose room when drawing
  R = spend a die to redraw options (during selection)
  I = toggle inventory view
"""
import pygame
import random
import os
from collections import defaultdict
from abc import ABC,abstractmethod


# -------------------------
# Provided base classes (kept and slightly adapted)
# -------------------------
class Port:
    def __init__(self, level):
        self.level = int(level)

class Piece:
    def __init__(self, nom, ports, cout, degre_rarete, cond_deplac, couleur, obj, image_id=None):
        self.__nom = nom
        self.__image_id = image_id
        self.__cout = cout
        self.__degre_rarete = degre_rarete
        self.__ports = ports  # e.g. dict {'up': True, 'down': True, ...}
        self.__cond_deplac = cond_deplac
        self.__couleur = couleur
        self.__obj = obj

    @property
    def nom(self):
        return self.__nom
    @property
    def cout(self):
        return self.__cout
    @property
    def ports(self):
        return self.__ports
    @property
    def degre_rarete(self):
        return self.__degre_rarete
    @property
    def couleur(self):
        return self.__couleur
    @property
    def image_id(self):
        return self.__image_id
    @property
    def cond_deplac(self):
        return self.__cond_deplac
    @property
    def obj(self):
        return self.__obj

    #methode
    def proba_tirage(self): #pour calculer la probab de tirer une piece suivant sa rareté
        return 1/(3**self.__degre_rarete)

class Inventory:
    def __init__(self):
        self.objets_consommables = { "pas" : 70, "pieces" : 0, "gemmes" : 2, "cles" : 0, "des" : 0}
        self.objets_permanents = {
            "pelle" : False,
            "marteau" : False,
            "kit_de_crochetage" : False,
            "detecteur_de_metaux" : False,
            "patte_de_lapin" : False}

    #methodes
    #objets consommables
    def ajouter_conso(self, nom_objet, quantitee):
        """Ajoute (ou crée) une quantité pour un consommable.

        Si le consommable existe, incrémente sa quantité ; sinon, crée l'entrée
        avec la quantité indiquée.

        Args:
            nom_objet: Nom du consommable (ex. "cles", "gemmes").
            quantitee: Quantité à ajouter (>= 0).

        Returns:
            None
        """   
        if nom_objet in self.objets_consommables:
            self.objets_consommables[nom_objet] += quantitee
        else:
            self.objets_consommables[nom_objet] = quantitee

    def retirer(self, nom_objet, quantitee):
        """Retire une quantité d'un consommable s'il y a assez de stock.

            Vérifie la quantité disponible et ne décrémente que si elle est suffisante.

            Args:
                nom_objet: Nom du consommable à débiter.
                quantitee: Quantité à retirer (> 0).

            Returns:
                bool: True si le retrait a été effectué ; False sinon (stock insuffisant
                ou consommable inexistant).
        """
        if self.objets_consommables.get(nom_objet, 0) >= quantitee:
            self.objets_consommables[nom_objet] -= quantitee
            return True
        return False

    #objets permanents
    def ajouter_perm(self, nom_objet):
        """Ajoute/active un objet permanent dans l'inventaire.

        Marque l'objet permanent comme disponible (True). Si la clé n'existait pas,
        elle est créée.

        Args:
            nom_objet: Nom de l'objet permanent (ex. "pelle", "marteau").

        Returns:
            None
        """  
        self.objets_permanents[nom_objet] = True

LOOT_TABLE_CHEST=[
    ("gemmes",1,0.35),
    ("cles",1,0.40),
    ("pieces",15,0.50),
]
LOOT_TABLE_CASIER=[
    ("cles",1,0.60),
    ('pieces',10,0.30),
]
LOOT_TABLE_DIG=[
    ("pieces",8,0.50),
    ("cles",1,0.20),
    ("gemmes",1,0.20),
]
def _roll_loot(table):
    "Returns a list of (resource, amount) according to independent probabilities. If nothing falls, gives consolation coins" 
    out=[]
    for name,amt,p in table:
        if random.random()<p:
            out.append((name,amt))
    if not out:
            out=[('pieces',5)]
    return out   

class Interactable(ABC):
    """Classe abstraite représentant un élément interactif dans le manoir.

        Cette classe définit l’interface commune pour tous les objets avec lesquels
        le joueur peut interagir (coffres, casiers, sites de fouille, etc.).  
        Chaque sous-classe doit préciser un `label`, un symbole visuel (`emoji`)
        et la logique de l’interaction (`interact`).

        Attributs:
            opened (bool): Indique si l’objet a déjà été ouvert/utilisé.
                        Par défaut à False.

        Méthodes abstraites:
            label() -> str:
                Retourne le nom descriptif de l’objet (ex. "un coffre").
            emoji() -> str:
                Retourne un caractère ou emoji représentant visuellement l’objet.
            interact(game, cell):
                Définit le comportement lorsque le joueur interagit avec l’objet.
                Doit être implémentée par les sous-classes.
        """
    def __init__(self):
        self.opened=False
    @abstractmethod
    def label(self)-> str:
        pass
    @abstractmethod
    def emoji(self)-> str:
        pass
    @abstractmethod
    def interact(self,game,cell):
        pass

class Chest(Interactable):
    def label(self) -> str:
        return "a chest"

    def emoji(self) -> str:
        return "🧰"

    def interact(self, game, cell):
        if self.opened:
            game.turn_msg = "The chest is empty."
            return
        # cle ou marteau
        if game.inventory.objets_consommables.get("cles", 0) > 0:
            game.inventory.retirer("cles", 1)
            msg = "Used a key to open the chest."
        elif game.inventory.objets_permanents.get("marteau"):
            msg = "Used the hammer to smash the chest."
        else:
            game.turn_msg = "A chest is here. You need a key or the hammer."
            return

        loot = _roll_loot(LOOT_TABLE_CHEST)
        self.opened = True
        game.turn_msg = msg
        for name, amt in loot:
            game.inventory.ajouter_conso(name, amt)
            game.turn_msg += f" → +{amt} {name}"


class Casier(Interactable):
    def label(self) -> str:
        return "a locker"

    def emoji(self) -> str:
        return "🔒"

    def interact(self, game, cell):
        if self.opened:
            game.turn_msg = "The locker is empty."
            return
        # just key
        if game.inventory.objets_consommables.get("cles", 0) > 0:
            game.inventory.retirer("cles", 1)
        else:
            game.turn_msg = "A locker is here. You need a key."
            return

        loot = _roll_loot(LOOT_TABLE_CASIER)
        self.opened = True
        game.turn_msg = "Locker opened"
        for name, amt in loot:
            game.inventory.ajouter_conso(name, amt)
            game.turn_msg += f" → +{amt} {name}"


class DigSite(Interactable):
    def label(self) -> str:
        return "a dig site"

    def emoji(self) -> str:
        return "⛏️"

    def interact(self, game, cell):
        if self.opened:
            game.turn_msg = "Nothing left to dig here."
            return
        if not game.inventory.objets_permanents.get("pelle"):
            game.turn_msg = "You found a dig site. You need a shovel."
            return

        loot = _roll_loot(LOOT_TABLE_DIG)
        self.opened = True
        game.turn_msg = "You dug the site"
        for name, amt in loot:
            game.inventory.ajouter_conso(name, amt)
            game.turn_msg += f" → +{amt} {name}"
# -------------------------
# Game-specific code
# -------------------------
CELL_W = 70   
CELL_H = 70   
ROWS = 9
COLS = 5
WINDOW_W = COLS*CELL_W + 400   
WINDOW_H = ROWS*CELL_H + 80

MARGIN = 3


IMAGES_FOLDER = "images"

pygame.init()
FONT = pygame.font.SysFont("Arial", 16)
BIG = pygame.font.SysFont("Arial", 22, bold=True)

def load_image(name, size=(CELL_W, CELL_H)):
    path = os.path.join(IMAGES_FOLDER, name)
    try:
        im = pygame.image.load(path).convert_alpha()
        im = pygame.transform.smoothscale(im, size)
        return im
    except Exception:
        return None

# Basic room catalog (small set for the demo). Each entry is a Piece instance.
# ports = dict indicating which sides have doors relative to piece center (up/down/left/right)
# cond_deplac is simple placeholder (None or 'edge' meaning only border)
ROOM_CATALOG = []

def make_piece(nom, imgfile, ports, cout, rare, cond, couleur, obj):
    p = Piece(nom, ports, cout, rare, cond, couleur, obj, image_id=imgfile)
    return p

# We'll define a small catalog with representative pieces
ROOM_CATALOG.extend([
    make_piece("Entrance Hall", "Entrance_Hall_Icon.png", {'up':True,'down':False,'left':False,'right':False}, 0, 0, None, "blue", {'on_enter': {'type':'start'}}),
    make_piece("Antechamber", "antechamber.png", {'up':False,'down':True,'left':True,'right':True}, 0, 3, None, "blue", {'on_enter': {'type':'goal'}}),
    make_piece("Vault", "vault_Icon.png", {'up':True,'down':True,'left':False,'right':False}, 3, 3, None, "blue", {'on_enter': {'type':'coins','amount':40}}),
    make_piece("Veranda", "veranda.webp", {'up':True,'down':True,'left':True,'right':False}, 2, 2, 'edge', "green", {'on_draw': {'type':'inc_green_weight'}}),
    make_piece("Den", "den.webp", {'up':True,'down':True,'left':True,'right':True}, 0, 1, None, "blue", {'on_draw': {'type':'gem_always'}}),
    make_piece("Maid's Chamber", "maid_chamber.webp", {'up':True,'down':True,'left':False,'right':True}, 0, 1, None, "purple", {'on_draw': {'type':'inc_find_objects'}}),
    make_piece("Garden", "garden.png", {'up':True,'down':True,'left':True,'right':True}, 0, 2, 'edge', "green", {'on_enter': {'type':'maybe_gem','chance':0.5}}),
    make_piece("Furnace", "furnace.png", {'up':False,'down':True,'left':True,'right':True}, 0, 2, None, "orange", {'on_draw': {'type':'inc_fire_weight'}}),
    make_piece("Bedroom", "bedroom.webp", {'up':True,'down':True,'left':True,'right':True}, 0, 1, None, "purple", {'on_enter': {'type':'food','amount':10}}),
    make_piece("Empty", "empty.png", {'up':True,'down':True,'left':True,'right':True}, 0, 0, None, "blue", {}),
    make_piece("Storage", "empty.png", {'up':True,'down':True,'left':True,'right':True}, 0, 1, None, "orange",{'on_enter': {'type':'spawn','spawn':'chest'}}),
    make_piece("Locker Room", "empty.png", {'up':True,'down':True,'left':True,'right':True}, 0, 1, None, "orange",{'on_enter': {'type':'spawn','spawn':'casier'}}),    make_piece("Courtyard", "empty.png", {'up':True,'down':True,'left':True,'right':True}, 0, 1, 'edge', "green",{'on_enter': {'type':'spawn','spawn':'dig_site'}}),
    make_piece("Shop","empty.png",{'up':True,'down':True,'left':True,'right':True},0,1, None,'yellow',{'on_enter':{'type':'shop'}}),
])

# multiplicity in initial deck (you can change)
INITIAL_DECK = []
for p in ROOM_CATALOG:
    # add multiple instances for balance: more commons than rares
    mult = 1 if p.degre_rarete>=3 else 3 if p.degre_rarete==2 else 5 if p.degre_rarete==1 else 7
    for _ in range(mult):
        INITIAL_DECK.append(p)

def weighted_sample_no_replacement(pool, k):
    """Select k distinct elements from pool using weight = p.proba_tirage()"""
    pool = list(pool)
    selected = []
    available = pool[:]
    for _ in range(min(k, len(pool))):
        weights = [x.proba_tirage() for x in available]
        tot = sum(weights)
        if tot==0:
            choice = random.choice(available)
        else:
            r = random.random()*tot
            cum=0
            for i,w in enumerate(weights):
                cum += w
                if r<=cum:
                    choice = available[i]
                    break
        selected.append(choice)
        available.remove(choice)
    return selected

# Game state containers
class Cell:
    """Représente une case du plateau de jeu.

        Chaque cellule peut contenir une pièce de type `Piece`, un ensemble de portes
        (avec leurs niveaux de verrou), et éventuellement un objet interactif
        (`Interactable`) comme un coffre, un casier ou un site de fouille.

        Attributs:
            piece (Piece | None): La pièce placée sur cette case, ou None si vide.
            doors (dict[str, int | None]): Dictionnaire des portes adjacentes,
                associant chaque direction ('up','down','left','right') à un niveau
                de verrou :
                    - 0 : porte ouverte
                    - 1 : verrou faible
                    - 2 : verrou fort
                    - None : pas de porte
            interactable (Interactable | None): Objet interactif présent sur la case,
                ou None s’il n’y en a pas.
        """    
    def __init__(self):
        self.piece = None
        # doors stored as dict of lock level for each direction when created: 0/1/2
        self.doors = {'up':None,'down':None,'left':None,'right':None}
        self.interactable=None #type interactable or None

DIRS = {'up':(-1,0), 'down':(1,0), 'left':(0,-1), 'right':(0,1)}
OPP  = {'up':'down','down':'up','left':'right','right':'left'}

class Game:
    """Boucle et état principal du jeu « Blue Prince ».
        Cette classe orchestre la pioche/placement des pièces, le déplacement
        du joueur sur la grille, la gestion des portes/verrous, l’inventaire,
        ainsi que les interactions avec les éléments interactifs (coffre, casier,
        site de fouille). Elle maintient tout l’état nécessaire au rendu Pygame.
    
    Attributs:
        deck (list[Piece]): Pioche courante (copies superficielles des pièces définies dans le catalogue), mélangée au démarrage.

        grid (list[list[Cell]]): Grille de cellules (ROWS x COLS) contenant éventuellement une `Piece`, des portes et un interactif.

        player_r (int): Ligne actuelle du joueur dans la grille.

        player_c (int): Colonne actuelle du joueur dans la grille.

        inventory (Inventory): Inventaire du joueur (consommables et permanents).

        turn_msg (str): Message court de feedback affiché à l’écran.

        selection_mode (bool): True si on est en mode « choix de salle ».

        candidates (list[Piece]): Liste de pièces candidates lors d’un placement.

        selection_pos (int): Index de la pièce sélectionnée dans `candidates`.

        target_cell (tuple[int,int] | None): Coordonnées (r,c) de la cellule ciblée lors d’un placement, sinon None.

        running (bool): Indique si la partie est en cours (pour terminer proprement la boucle de jeu).
    
    """    
    def __init__(self):
        self.deck = INITIAL_DECK[:]  # shallow copies of Piece references; removing an element prevents further draws
        random.shuffle(self.deck)
        # grid of cells
        self.grid = [[Cell() for _ in range(COLS)] for __ in range(ROWS)]
        # place entrance at bottom middle
        start_r = ROWS-1
        start_c = COLS//2
        entrance_piece = next((p for p in ROOM_CATALOG if p.nom=="Entrance Hall"), None)
        self.grid[start_r][start_c].piece = entrance_piece
        self.player_r = start_r
        self.player_c = start_c
        # mark the entrance cell doors initialization (all doors default None)
        self.inventory = Inventory()
        self.turn_msg = "Welcome to Blue Prince - simplified."
        self.selection_mode = False
        self.candidates = []
        self.selection_pos = 0
        self.target_cell = None
        self.running = True
        self.in_shop=False

    def in_bounds(self, r,c):
        """Vérifie si des coordonnées sont dans les limites de la grille.

        Args:
            r: Index de ligne.
            c: Index de colonne.

        Returns:
            True si (r, c) est à l’intérieur du plateau ; False sinon.
        """    
        return 0<=r<ROWS and 0<=c<COLS
    
    def fits_board_and_direction(self, piece, tr, tc, direction):
        """
        Teste si une pièce peut être placée en (tr, tc) en respectant :
        - contrainte 'edge'
        - ports qui ne sortent pas du plateau
        - compatibilité de ports avec les voisins

        C'est le filtre demandé dans l'énoncé (ports & bords).
        """
        # contrainte 'edge' : la pièce ne peut aller qu'en bord si cond_deplac == 'edge'
        if piece.cond_deplac == 'edge':
            if tr not in (0, ROWS - 1) and tc not in (0, COLS - 1):
                return False

        # le reste (ports / voisins) est déjà géré par can_place_piece
        return self.can_place_piece(piece, tr, tc, direction)

    def generate_candidates(self, tr, tc, direction):
        """
        Génère jusqu'à 3 pièces candidates pour la case (tr, tc) en venant
        de 'direction', en respectant :
            - fits_board_and_direction (ports + bords)
            - filtre par gemmes
            - robustesse : au moins 1 choix coût 0 si possible

        Retourne une liste de 1 à 3 pièces. Liste vide si aucune pièce légale.
        """
        # 1) toutes les pièces LEGALISABLES sur cette case
        legal_pool = []
        for p in self.deck:
            if self.fits_board_and_direction(p, tr, tc, direction):
                legal_pool.append(p)

        if not legal_pool:
            return []

        # 2) filtre par gemmes (comme dans ton code original),
        #    mais on ne perd jamais les pièces de coût 0
        gems = self.inventory.objets_consommables.get('gemmes', 0)
        pool = [p for p in legal_pool if p.cout == 0 or p.cout <= gems]

        # si après filtre on n'a plus rien (pas assez de gemmes et pas de pièces à 0),
        # on tombe en secours sur toutes les pièces légales
        if not pool:
            pool = legal_pool[:]  # fallback, en théorie rare si le deck est bien conçu

        # 3) robustesse : au moins 1 choix coût 0 si possible
        zero_cost_rooms = [p for p in pool if p.cout == 0]

        candidates = []
        if zero_cost_rooms:
            # on force UNE pièce à coût 0
            free_choice = random.choice(zero_cost_rooms)
            candidates.append(free_choice)

            # puis jusqu'à 2 autres distinctes
            remaining_pool = [p for p in pool if p is not free_choice]
            others = weighted_sample_no_replacement(remaining_pool, 2)
            candidates.extend(others)
        else:
            # il n'existe aucune pièce coût 0 légale -> on prend juste 3 parmi le pool
            candidates = weighted_sample_no_replacement(pool, 3)

        return candidates[:3]

    def can_place_piece(self, piece, tr, tc, from_dir):
        """Teste si une pièce peut être placée en (tr, tc) en respectant les règles.

        Règles vérifiées :
        1) La pièce doit avoir un port vers la case d’origine (direction opposée).
        2) Aucun port de la pièce ne doit sortir du plateau.
        3) Compatibilité des ports avec les voisins déjà posés (réciprocité).

        Args:
            piece: La pièce candidate.
            tr: Ligne cible.
            tc: Colonne cible.
            from_dir: Direction depuis laquelle on arrive ('up','down','left','right').

        Returns:
            True si le placement est légal ; False sinon.
        """ 
    # 1) la piece doit avoir un port vers l'origin
        if not piece.ports.get(OPP[from_dir], False):
            return False

        # 2) aucune port peuve sortir du tableau
        for d,(dr,dc) in DIRS.items():
            if piece.ports.get(d, False):
                nr, nc = tr+dr, tc+dc
                if not self.in_bounds(nr, nc):
                    return False

        # 3) compatibilité avec les voisins qui sont déjà placées
        for d,(dr,dc) in DIRS.items():
            nr, nc = tr+dr, tc+dc
            if self.in_bounds(nr, nc):
                neigh = self.grid[nr][nc].piece
                if neigh is not None:
                    # si la piece a une port vers le voisin, le voisin doit avoir un porte vers elle
                    if piece.ports.get(d, False) and not neigh.ports.get(OPP[d], False):
                        return False
                    # si le voisin a une porte donnant sur cette pièce, celle-ci doit renvoyer la porte
                    if neigh.ports.get(OPP[d], False) and not piece.ports.get(d, False):
                        return False
        return True


    def neighbor_target(self, direction):
        """Renvoie la case voisine à partir de la position du joueur.

            Args:
                direction: 'up', 'down', 'left' ou 'right'.

            Returns:
                Un tuple (r, c) des coordonnées de la case voisine.
        """
        dr,dc = 0,0
        if direction=='up': dr=-1
        if direction=='down': dr=1
        if direction=='left': dc=-1
        if direction=='right': dc=1
        return self.player_r+dr, self.player_c+dc

    def door_lock_for_target_row(self, target_row):
        """Calcule un niveau de verrou (0/1/2) selon la ligne cible.

        Les portes ont plus de chances d’être verrouillées en haut du plateau.

        Args:
            target_row: Index de ligne de la case cible.

        Returns:
            int: 0 (déverrouillée), 1 (verrou faible), ou 2 (verrou fort).
        
        """
        # linear mapping: bottom row -> 0, top row -> 2
        if ROWS <=1:
            return 0
        #distance from 'grown', 0 in bottom, 1 on top
        t = (ROWS-1 - target_row) / (ROWS-1) 
        if target_row==ROWS-1:
            return 0 #first row always 0
        if target_row==0:
            return 2 #last row always 0
        p2=0.1+0.7*t
        p0=0.7-0.6*t
        p1=max(0.0,1.0-p0-p2)
        r=random.random()
        if r<p0:
            return 0
        elif r<p0+p1:
            return 1
        else:
            return 2
        

    def open_door_or_move(self, direction):
        """Ouvre une porte et se déplace, ou lance la sélection d’une nouvelle salle.

        Si la case voisine contient déjà une pièce, tente d’ouvrir la porte selon
        l’inventaire (clé/kit) puis consomme un pas et entre dans la salle.
        Sinon, passe en mode sélection et propose des pièces valides à placer.
        """
        tr, tc = self.neighbor_target(direction)
        if not self.in_bounds(tr, tc):
            self.turn_msg = "A wall. Can't go there."
            return

        cell = self.grid[tr][tc]

        # --- CASE 1 : la case a déjà une pièce -> déplacement ---
        if cell.piece is not None:
            # check door lock (si la porte était définie)
            lock = cell.doors.get(self.opposite(direction))
            if lock is None:
                lock = 0

            if lock > 0:
                opened = False
                if self.inventory.objets_permanents.get("kit_de_crochetage") and lock == 1:
                    # kit ouvre niveau 1 gratuitement
                    self.turn_msg = "Used kit to open a level 1 door."
                    opened = True
                elif self.inventory.objets_permanents.get("marteau") and lock <= 2:
                    # marteau : tu as laissé comme non utilisé pour les portes
                    pass
                else:
                    if self.inventory.objets_consommables.get("cles", 0) > 0:
                        self.inventory.retirer("cles", 1)
                        self.turn_msg = "Used a key to open the door."
                        opened = True
                    else:
                        self.turn_msg = "Door is locked and you have no key/kit."
                        return

                if opened:
                    cur_cell = self.grid[self.player_r][self.player_c]
                    target_cell = self.grid[tr][tc]
                    # porte ouverte dans les deux sens
                    cur_cell.doors[direction] = 0
                    target_cell.doors[self.opposite(direction)] = 0

            # déplacement consomme 1 pas
            if self.inventory.objets_consommables["pas"] <= 0:
                self.turn_msg = "No steps left! You can't move."
                return

            self.inventory.retirer("pas", 1)
            self.player_r, self.player_c = tr, tc
            self.in_shop=False
            self.on_enter(cell)
            return

        # --- CASE 2 : la case est vide -> mode sélection ---
        else:
            # direction réelle par rapport au joueur (sécurité)
            dr = tr - self.player_r
            dc = tc - self.player_c
            dir_map = {(-1, 0): 'up', (1, 0): 'down', (0, -1): 'left', (0, 1): 'right'}
            real_dir = dir_map.get((dr, dc), direction)

            candidates = self.generate_candidates(tr, tc, real_dir)
            if not candidates:
                self.turn_msg = "No legal rooms can be placed here."
                return

            self.selection_mode = True
            self.candidates = candidates
            self.selection_pos = 0
            self.target_cell = (tr, tc)
            self.turn_msg = "Choose a room (ENTER) or press R to redraw (spend a die)."
            return

    def interact_current_cell(self):
        """Déclenche l’interaction avec l’objet interactif de la case courante.

            Met à jour `turn_msg` selon le résultat.

            Returns:
                None
        """
        if cell.piece and cell.piece.obj.get('on_enter', {}).get('type') == 'shop':
            self.shop_menu()
            return
        
        cell = self.grid[self.player_r][self.player_c]
        it = cell.interactable
        if not isinstance(it, Interactable):
            self.turn_msg = "Nothing to interact with."
            return
        it.interact(self, cell)

    def opposite(self, direction):
        """Donne la direction opposée à celle fournie.

        Args:
            direction: 'up','down','left' ou 'right'.

        Returns:
            La direction opposée ('down','up','right' ou 'left').
        """
        return {'up':'down','down':'up','left':'right','right':'left'}[direction]

    def on_enter(self, cell):
        """Applique les effets d’entrée d’une salle et événements aléatoires.

        Traite les effets 'on_enter' (pièces, nourriture, victoire, spawn d’objets
        interactifs, etc.) et les trouvailles aléatoires, puis met à jour `turn_msg`.

        Args:
            cell: La cellule dans laquelle le joueur vient d’entrer.

        Returns:
            None
        """
        p = cell.piece
        if not p:
            return
        self.in_shop=False #par defaut on n'est pas dans une shop
        effects = p.obj.get('on_enter') if p.obj else None
        if effects:
            t = effects.get('type')
            if t == 'coins':
                amt = effects.get('amount',0)
                self.inventory.ajouter_conso('pieces', amt)
                self.turn_msg = f"Found {amt} coins!"
            elif t == 'food':
                amt = effects.get('amount',0)
                self.inventory.ajouter_conso('pas', amt)
                self.turn_msg = f"Ate food and regains {amt} steps!"
            elif t == 'goal':
                self.turn_msg = "You reached the Antechamber! You win!"
                self.running = False
            elif t == 'start':
                self.turn_msg = "Back at the Entrance."
            elif t == 'spawn':
                what = effects.get('spawn')
                if isinstance(cell.interactable, Interactable) and not cell.interactable.opened:
                    
                    return
                if what == 'chest':
                    cell.interactable = Chest()
                elif what == 'casier':
                    cell.interactable = Casier()
                elif what == 'dig_site':
                    cell.interactable = DigSite()
            
                if cell.interactable:
                    self.turn_msg = f"You found {cell.interactable.label()}! Press E to interact."
            elif t=='shop':
                self.turn_msg='You entered the shop. Press E to trade.'
                self.in_shop=True

            else:
                self.turn_msg = f"Entered {p.nom}."
        else:
             # Salle sans effet spécial
            self.turn_msg = f"Entered {p.nom}."

        # possibility to find gems or items randomly
        # if detecteur_de_metaux increases keys/coins chance; patte_de_lapin increases chance to find items
        base_find = random.random()
        if base_find < 0.08 + (0.05 if self.inventory.objets_permanents.get('patte_de_lapin') else 0):
            # randomly give something
            found = random.choice(['gemmes','cles','des','pieces','pas'])
            if found=='gemmes':
                self.inventory.ajouter_conso('gemmes',1)
                self.turn_msg += " Found 1 gem."
            elif found=='cles':
                self.inventory.ajouter_conso('cles',1)
                self.turn_msg += " Found 1 key."
            elif found=='des':
                self.inventory.ajouter_conso('des',1)
                self.turn_msg += " Found 1 die."
            elif found=='pieces':
                self.inventory.ajouter_conso('pieces',5)
                self.turn_msg += " Found some coins."
            elif found=='pas':
                self.inventory.ajouter_conso('pas',3)
                self.turn_msg += " Found 3 steps."

    def confirm_selection(self):
        """Confirme la pièce choisie, la pose et gère les effets associés.

        Débite le coût en gemmes si nécessaire, place la pièce, initialise le niveau
        de verrou des portes, applique les effets 'on_draw', puis tente d’entrer
        dans la nouvelle salle.

        Returns:
            None
        """
        if not self.selection_mode or not self.target_cell:
            return
        index = self.selection_pos
        choice = self.candidates[index]
        tr,tc = self.target_cell
        # check gem cost
        if choice.cout>0:
            if self.inventory.objets_consommables.get('gemmes',0) < choice.cout:
                self.turn_msg = "Not enough gems to choose that room."
                return
            else:
                self.inventory.retirer('gemmes', choice.cout)
        # place the piece
        self.grid[tr][tc].piece = choice
        # set door locks based on target row
        lock_level = self.door_lock_for_target_row(tr)
        # set both sides door lock (from current cell to placed cell)
        cur = self.grid[self.player_r][self.player_c]
        # figure direction
        dr = tr - self.player_r
        dc = tc - self.player_c
        dir_map = {( -1,0):'up',(1,0):'down',(0,-1):'left',(0,1):'right'}
        direction = dir_map.get((dr,dc))
        if direction:
            cur.doors[direction] = lock_level
            self.grid[tr][tc].doors[self.opposite(direction)] = lock_level
        # remove chosen instance from deck (one occurrence)
        try:
            self.deck.remove(choice)
        except ValueError:
            pass
        # apply on_draw effects
        od = choice.obj.get('on_draw') if choice.obj else None
        if od:
            typ = od.get('type')
            if typ == 'gem_always':
                self.inventory.ajouter_conso('gemmes',1)
                self.turn_msg = "You drew a room and found a gem!"
            elif typ == 'inc_green_weight':
                # simplistic: add extra copy of green-ish rooms to deck to increase chance
                greens = [p for p in ROOM_CATALOG if p.couleur=='green']
                if greens:
                    self.deck.extend(random.choices(greens, k=2))
                    self.turn_msg = "This veranda increases green rooms in the deck."
            elif typ == 'inc_find_objects':
                # set a permanent that increases find chance (simulate)
                self.inventory.ajouter_perm('patte_de_lapin')
                self.turn_msg = "You found something increasing find chances (patte_de_lapin)."
            elif typ == 'inc_fire_weight':
                # add furnace-like pieces
                fires = [p for p in ROOM_CATALOG if p.nom=='Furnace']
                if fires:
                    self.deck.extend(random.choices(fires, k=2))
                    self.turn_msg = "Furnace makes furnace-like rooms more common in the deck."
        
        else:
            self.turn_msg=f"Placed {choice.nom} at row {tr},lock={lock_level}"
        
        # exit selection mode and enter the new room (move)
        self.selection_mode = False
        self.candidates = []
        self.selection_pos = 0
        self.target_cell = None

        if direction:
            self.open_door_or_move(direction)

    def redraw_candidates_spend_die(self):
        """Repioche des pièces candidates en dépensant un dé.

        Respecte les contraintes de placement (ports + bords) et,
        si possible, assure au moins une option à coût 0.
        """
        if self.inventory.objets_consommables.get('des', 0) <= 0:
            self.turn_msg = "No dice to spend."
            return
        if not self.selection_mode or not self.target_cell:
            self.turn_msg = "Not in selection mode."
            return

        self.inventory.retirer('des', 1)

        tr, tc = self.target_cell
        # recalculer la direction depuis le joueur vers la case cible
        dr = tr - self.player_r
        dc = tc - self.player_c
        dir_map = {(-1, 0): 'up', (1, 0): 'down', (0, -1): 'left', (0, 1): 'right'}
        direction = dir_map.get((dr, dc))

        candidates = self.generate_candidates(tr, tc, direction)
        if not candidates:
            self.turn_msg = "No legal rooms to redraw here."
            return

        self.candidates = candidates
        self.selection_pos = 0
        self.turn_msg = "Redrew candidates (spent a die)."


    def has_legal_moves(self):
        """Indique s’il reste au moins un coup légal.

        Un coup légal est soit :
        - entrer par une porte voisine ouvrable (déverrouillée/ouvrable avec clé/kit),
        - soit placer une pièce compatible et abordable sur une case adjacente.

        Returns:
            True s’il existe un coup légal ; False sinon.
        """
        gems = self.inventory.objets_consommables.get('gemmes', 0)
        keys = self.inventory.objets_consommables.get('cles', 0)
        has_kit = self.inventory.objets_permanents.get('kit_de_crochetage', False)

        for d,(dr,dc) in DIRS.items():
            tr, tc = self.player_r + dr, self.player_c + dc
            if not self.in_bounds(tr, tc):
                continue
            cell = self.grid[tr][tc]

            # a) mouvement vers une piece, est ce que je peut ouvrir la porte?
            if cell.piece is not None:
                lock = cell.doors.get(OPP[d])
                lock = 0 if lock is None else lock
                if lock == 0:
                    return True
                if lock == 1 and (has_kit or keys > 0):
                    return True
                if lock == 2 and keys > 0:
                    return True

            # b) Aménagement d'une nouvelle salle : existe-t-il une pièce valable/abordable ?
            else:
                
                for p in self.deck:
                    if p.cond_deplac == 'edge' and (tr not in (0, ROWS-1) and tc not in (0, COLS-1)):
                        continue
                    if not self.can_place_piece(p, tr, tc, d):
                        continue
                    if p.cout == 0 or p.cout <= gems:
                        return True

        return False
    
    def shop_menu(self):
        """
        The player can buy items using coins.
        Prices:
            -key: 10 coins
            -Die: 25 coins
            -Steps(5): 8 coins
        """
        coins=self.inventory.objets_consommables.get('pieces',0)
        if not hasattr(self, "shop_cycle"):
            self.shop_cycle = 0

        if self.shop_cycle == 0:
            cost = 10
            if coins >= cost:
                self.inventory.retirer("pieces", cost)
                self.inventory.ajouter_conso("cles", 1)
                self.turn_msg = "Bought 1 key for 10 coins."
            else:
                self.turn_msg = "Not enough coins to buy a key (10 needed)."

        elif self.shop_cycle == 1:
            cost = 25
            if coins >= cost:
                self.inventory.retirer("pieces", cost)
                self.inventory.ajouter_conso("des", 1)
                self.turn_msg = "Bought 1 die for 25 coins."
            else:
                self.turn_msg = "Not enough coins to buy a die (25 needed)."

        elif self.shop_cycle == 2:
            cost = 8
            if coins >= cost:
                self.inventory.retirer("pieces", cost)
                self.inventory.ajouter_conso("pas", 5)
                self.turn_msg = "Bought 5 steps for 8 coins."
            else:
                self.turn_msg = "Not enough coins to buy steps (8 needed)."

        # move to next option
        self.shop_cycle = (self.shop_cycle + 1) % 3

# -------------------------
# Pygame rendering
# -------------------------
import pygame
pygame.font.init()

# try emoji font first, fallback to Arial
try:
    EMOJI_FONT = pygame.font.Font("C:/Windows/Fonts/seguiemj.ttf", 18)
except:
    try:
        EMOJI_FONT = pygame.font.Font("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 18)
    except:
        EMOJI_FONT = pygame.font.SysFont("Arial", 18)

def draw_game(screen, game):
    """Rend l’état courant du jeu sur l’écran Pygame.

    Dessine le plateau (grille de cellules), le joueur, les portes avec leur
    niveau de verrou, les pièces (image ou placeholder coloré), les badges
    d’objets interactifs (emoji), ainsi que le panneau latéral droit contenant
    l’inventaire (consommables et permanents) et l’historique de messages.
    Si `game.selection_mode` est actif, affiche une surcouche avec la liste
    de pièces candidates à placer et surbrille la sélection.

    Args:
        screen: Surface Pygame cible sur laquelle dessiner.
        game: Instance de `Game` dont l’état (grille, inventaire, messages,
            sélection, etc.) est utilisé pour le rendu.

    Returns:
        None

    Notes:
        - Les dimensions de cellules/plateau sont déterminées par les constantes
          globales (`CELL_W`, `CELL_H`, `ROWS`, `COLS`) et par la taille de fenêtre.
        - Les images des pièces sont chargées via `load_image(...)`. En cas d’échec,
          un rectangle coloré et le nom abrégé de la pièce sont affichés.
        - Les niveaux de portes sont indiqués par des pastilles colorées :
            0 → gris (ouvert), 1 → orange (verrou faible), 2 → rouge (verrou fort).
        - Les objets interactifs non ouverts affichent un petit emoji dans le coin
          supérieur droit de la cellule.
        - En mode sélection, une couche semi-transparente et un panneau central
          listent jusqu’à trois candidats avec coût/rareté, et encadrent l’option
          courante.
        """
    screen.fill((30,30,30))
    # grid
    ox = 20
    oy = 20
    for r in range(ROWS):
        for c in range(COLS):
            x = ox + c*CELL_W
            y = oy + r*CELL_H
            cell = game.grid[r][c]
            rect = pygame.Rect(x+MARGIN, y+MARGIN, CELL_W-2*MARGIN, CELL_H-2*MARGIN)
            # background
            pygame.draw.rect(screen, (60,60,60), rect)
            # if piece, draw image or box and name
            if cell.piece:
                img = load_image(cell.piece.image_id)
                if img:
                    screen.blit(img, (rect.x, rect.y))
                else:
                    # colored placeholder based on piece color
                    clr = {'green':(60,130,60),'purple':(110,60,110),'orange':(200,120,60),'blue':(60,90,160)}.get(cell.piece.couleur,(120,120,120))
                    pygame.draw.rect(screen, clr, rect)
                    txt = FONT.render(cell.piece.nom[:10], True, (255,255,255))
                    screen.blit(txt, (rect.x+4, rect.y+4))
            else:
                # unexplored
                pygame.draw.rect(screen, (20,20,20), rect)
            # draw player
            if (r,c)==(game.player_r, game.player_c):
                pygame.draw.rect(screen, (255,255,0), rect, 3)

            # interactable indicator (chest, casier or dig site)
            if isinstance(cell.interactable, Interactable) and not cell.interactable.opened:
                emoji = cell.interactable.emoji()
                badge = EMOJI_FONT.render(emoji, True, (255, 255, 255))
                screen.blit(badge, (rect.right - 24, rect.top))


            # draw door lock marker (if doors set)
            cell_doors = cell.doors
            for i,dir in enumerate(['up','left','right','down']):
                lv = cell_doors.get(dir)
                if lv is not None:
                    # small colored dot near side with number
                    if dir=='up':
                        px,py = rect.centerx, rect.top+3
                    elif dir=='down':
                        px,py = rect.centerx, rect.bottom-6
                    elif dir=='left':
                        px,py = rect.left+3, rect.centery
                    else:
                        px,py = rect.right-6, rect.centery
                    color = (150,150,150) if lv==0 else (200,120,60) if lv==1 else (200,60,60)
                    pygame.draw.circle(screen, color, (px,py), 6)
    panel_x = COLS*CELL_W + 40
    pygame.draw.rect(screen, (25, 25, 25), (panel_x-15, 10, WINDOW_W - panel_x - 25, WINDOW_H - 20), border_radius=10)
    pygame.draw.rect(screen, (60, 60, 70), (panel_x-15, 10, WINDOW_W - panel_x - 25, 40), border_radius=10)
    screen.blit(EMOJI_FONT.render("📦 Inventory", True, (255,255,255)), (panel_x, 18))

    inv = game.inventory
        # --- right panel ---
    
    y = 60
    screen.blit(EMOJI_FONT.render("🧺 Consumables", True, (210,210,255)), (panel_x, y))

    y += 22
    for k,v in inv.objets_consommables.items():
        bar_len = min(120, v*2)  # small visual bar
        pygame.draw.rect(screen, (80,80,150), (panel_x+130, y+5, bar_len, 6))
        txt = FONT.render(f"{k:10s} : {v}", True, (230,230,230))
        screen.blit(txt, (panel_x+5, y))
        y += 20

    y += 8
    screen.blit(EMOJI_FONT.render("⚙️  Permanents", True, (210,210,255)), (panel_x, y))

    y += 22
    for k,v in inv.objets_permanents.items():
        color = (100,220,100) if v else (160,160,160)
        status = "✔" if v else "✖"
        txt = FONT.render(f"{status} {k}", True, color)
        screen.blit(txt, (panel_x+5, y))
        y += 22


    # bottom message
    msgsurf = FONT.render("Msg: " + game.turn_msg, True, (240,240,240))
    screen.blit(msgsurf, (panel_x, WINDOW_H - 40))
    # selection mode overlay
    if game.selection_mode:
        # darken
        s = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        s.fill((0,0,0,150))
        screen.blit(s, (0,0))
        # small panel at center
        w = 520
        h = 160
        px = (WINDOW_W - w)//2
        py = (WINDOW_H - h)//2
        pygame.draw.rect(screen, (50,50,60), (px,py,w,h))
        pygame.draw.rect(screen, (200,200,220), (px,py,w,24))
        screen.blit(BIG.render("Choose a room (ENTER) or R to redraw (spend die)", True, (0,0,0)), (px+6,py))
        # display candidates
        cx = px+10
        cy = py+36
        for i,cand in enumerate(game.candidates):
            crect = pygame.Rect(cx + i*(w//3), cy, (w//3)-10, h-56)
            pygame.draw.rect(screen, (80,80,90), crect)
            # image or placeholder
            img = load_image(cand.image_id, size=(crect.w-8, crect.h-30))
            if img:
                screen.blit(img, (crect.x+4, crect.y+4))
            else:
                pygame.draw.rect(screen, (100,100,120), (crect.x+4, crect.y+4, crect.w-8, crect.h-30))
            # name and cost
            screen.blit(FONT.render(cand.nom, True, (255,255,255)), (crect.x+6, crect.y+crect.h-24))
            screen.blit(FONT.render(f"Cost(gem): {cand.cout}  Rarity: {cand.degre_rarete}", True, (210,210,210)), (crect.x+6, crect.y+crect.h-10))
            if i==game.selection_pos:
                pygame.draw.rect(screen, (255,255,0), crect, 3)

def game_loop():
    """Boucle principale Pygame : gestion des événements, rendu et cycle de jeu.

    Initialise la fenêtre, l’horloge et l’état `Game`, puis:
      - traite les événements clavier (déplacement, interaction, sélection,
        relance des candidats, inventaire, sortie avec ESC),
      - met à jour les messages/état de fin (plus de pas, absence de coups légaux),
      - dessine l’interface via `draw_game(...)`,
      - limite la cadence d’affichage (clock.tick(30)).

    La boucle se termine proprement en cas de fermeture de la fenêtre, pression
    d’ESC, ou quand `game.running` devient False (Game Over / victoire).

    Returns:
        None
    """
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Blue Prince - simplified")
    clock = pygame.time.Clock()
    game = Game()

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if game.selection_mode:
                    if ev.key == pygame.K_RETURN:
                        game.confirm_selection()
                    elif ev.key == pygame.K_r:
                        game.redraw_candidates_spend_die()
                    elif ev.key in (pygame.K_LEFT, pygame.K_q):  # Q key or left arrow
                        game.selection_pos = max(0, game.selection_pos-1)
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        game.selection_pos = min(len(game.candidates)-1, game.selection_pos+1)
                else:
                    # movement keys (Z Q S D or arrows)
                    if ev.key in (pygame.K_z, pygame.K_UP):
                        game.open_door_or_move('up')
                    elif ev.key in (pygame.K_s, pygame.K_DOWN):
                        game.open_door_or_move('down')
                    elif ev.key in (pygame.K_q, pygame.K_LEFT):
                        game.open_door_or_move('left')
                    elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                        game.open_door_or_move('right')
                    elif ev.key==pygame.K_e:
                        game.interact_current_cell()
                    elif ev.key == pygame.K_i:
                        # toggle inventory? (we always show)
                        pass
                    
        # check lose condition
        if game.inventory.objets_consommables.get('pas',0) <= 0:
            game.turn_msg = "You ran out of steps! Game Over."
            game.running = False
        elif not game.selection_mode and not game.has_legal_moves():
            game.turn_msg = "Bloqué – plus de coup légal. Game Over."
            game.running = False

        # draw
        draw_game(screen, game)
        pygame.display.flip()
        clock.tick(30)
        if not game.running:
            # show message for a moment then quit
            pygame.time.delay(1500)
            pygame.quit()
            return


if __name__ == "__main__":
    game_loop()      # arranca el juego normal




