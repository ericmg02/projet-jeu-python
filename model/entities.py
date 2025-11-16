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

class Piece:
    def __init__(self, nom, ports, cout, degre_rarete, zones_autorisees, couleur, obj, image_id=None):
        # attributs de base
        self.__nom = nom
        self.__image_id = image_id
        self.__cout = cout
        self.__degre_rarete = degre_rarete
        self.__ports = ports
        self.__couleur = couleur
        self.__obj = obj

        # IMPORTANT : toujours définir __cond_deplac pour éviter l'AttributeError
        self.__cond_deplac = None
        # zones_autorisees peut être :
        # - une liste/ensemble de zones -> on le garde comme zones_autorisees
        # - une string ('edge', 'corner', 'center', etc.) -> on la traite comme cond_deplac
        if isinstance(zones_autorisees, str):
            # ici on utilise la string comme contrainte de déplacement
            self.__cond_deplac = zones_autorisees
            self.__zones_autorisees = None
        elif zones_autorisees:
            # liste / set / tuple de zones
            self.__zones_autorisees = set(zones_autorisees)
        else:
            self.__zones_autorisees = None

    # propriétés
    @property
    def zones_autorisees(self):
        return self.__zones_autorisees

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
        # si jamais on a oublié de le définir, on renvoie None plutôt qu'une erreur
        return self.__cond_deplac

    @property
    def obj(self):
        return self.__obj

    # méthode
    def proba_tirage(self):
        """Pour calculer la probabilité de tirer une pièce suivant sa rareté."""
        return 1 / (3 ** self.__degre_rarete)

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
# --- Shop items (always available in any shop room) ---
SHOP_ITEMS = [
    {   "code": "cles",
        "label": "Key (+1)",
        "cost": 10,
        "target": "cles",
        "amount": 1,},

    {"code": "pas",
        "label": "Steps (+5)",
        "cost": 8,
        "target": "pas",
        "amount": 5,},

    {"code": "food",
        "label": "Food (+10 steps)",
        "cost": 12,
        "target": "pas",
        "amount": 10,},
]

def _roll_loot(table,has_detector=False):
    "Returns a list of (resource, amount) according to independent probabilities. If nothing falls, gives consolation coins" 
    out=[]
    for name,amt,p in table:
        if has_detector and name in ("cles", "pieces"):
            eff_p = min(1.0, p + 0.15)   # +15% but with more than 100%
        else:
            eff_p = p

        if random.random()<eff_p:
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
        
        has_detector = game.inventory.objets_permanents.get("detecteur_de_metaux", False)
        loot = _roll_loot(LOOT_TABLE_CHEST,has_detector=has_detector)
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
        
        has_detector = game.inventory.objets_permanents.get("detecteur_de_metaux", False)
        loot = _roll_loot(LOOT_TABLE_CASIER,has_detector=has_detector)
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
        
        has_detector = game.inventory.objets_permanents.get("detecteur_de_metaux", False)
        loot = _roll_loot(LOOT_TABLE_DIG,has_detector=has_detector)
        self.opened = True
        game.turn_msg = "You dug the site"
        for name, amt in loot:
            game.inventory.ajouter_conso(name, amt)
            game.turn_msg += f" → +{amt} {name}"
# -------------------------
# Game-specific code
# -------------------------
CELL_W = 80  
CELL_H = 80   
ROWS = 9
COLS = 5
WINDOW_W = COLS*CELL_W + 400  
WINDOW_H = ROWS*CELL_H + 80
# pour l'antichambre : tout en haut au milieu
GOAL_R = 0              # ligne du haut
GOAL_C = COLS // 2      # même colonne que l'Entrance Hall
MARGIN = 3


IMAGES_FOLDER = "model/pictures/rooms/"

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

def make_piece(nom, imgfile, ports, cout, rare, zones_autorisees, couleur, obj):
    return Piece(nom, ports, cout, rare, zones_autorisees, couleur, obj, image_id=imgfile)

# We'll define a small catalog with representative pieces
ROOM_CATALOG.extend([
    # Entrée
    make_piece("Entrance Hall", "Entrance_Hall_Icon.png",
               {'up': True, 'down': False, 'left': True, 'right': True},
               0, 0, None, "blue",
               {'on_enter': {'type': 'start'}}),
    # antichambre
    make_piece("Antechamber", "Antechamber_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 3, None, "blue",
               {'on_enter': {'type': 'goal'}}),
    ##
    make_piece("Attic", "Attic_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               3, 3, None, "blue",
               {'on_enter': {'type': 'attic_loot'}}),

    make_piece("Ballroom", "Ballroom_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               2, 2, None, "blue",
               {'on_enter': {'type': 'set_gems', 'amount': 2}}),

    make_piece("Bedroom", "Bedroom_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               0, 1, None, "purple",
               {'on_enter': {'type': 'steps_gain', 'amount': 2}}),

    make_piece("Billiard Room", "Billiard_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               0, 1, None, "blue",
               {}),

    make_piece("Boiler Room", "Boiler_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               1, 2, None, "blue",
               {'on_enter':{'type':'marteau'}}),

    make_piece("Bookshop", "Bookshop_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 3, 'corner', "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Bunk Room", "Bunk_Room_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 2, None, "purple",
               {'on_enter': {'type': 'steps_gain', 'amount': 4}}),

    make_piece("Boudoir", "Boudoir_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               0, 1, None, "purple",
               {'on_enter': {'type': 'steps_gain', 'amount': 2}}),

    make_piece("Chamber of Mirrors", "Chamber_of_Mirrors_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 3, 'center', "blue",
               {}),
    make_piece("Chapel", "Chapel_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "red",
               {'on_enter': {'type': 'lose_coin', 'amount': 1}}),

    make_piece("Cloister", "Cloister_Icon.png",
               {'up': True, 'down': True, 'left': True, 'right': True},
               0, 1, None, "green", {}),

    make_piece("Closet", "Closet_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, None, "blue", {}),

    make_piece("Coat Check", "Coat_Check_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, None, "blue", {}),

    make_piece("Commissary", "Commissary_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 2, None, "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Conference Room", "Conference_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               1, 2, None, "blue", {}),

    make_piece("Corridor", "Corridor_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               0, 0, None, "orange", {}),

    make_piece("Courtyard", "Courtyard_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, 'edge', "green",
               {'on_enter': {'type': 'spawn', 'spawn': 'dig_site'}}),

    make_piece("Darkroom", "Darkroom_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "red", {}),

    make_piece("Den", "Den_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "blue",
               {'on_draw': {'type': 'gem_always'}}),

    make_piece("Dining Room", "Dining_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               1, 2, None, "blue",
               {'on_enter': {'type': 'food', 'amount': 6}}),

    make_piece("Drafting Studio", "Drafting_Studio_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'allow_new_floorplan'}}),

    make_piece("Drawing Room", "Drawing_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               1, 2, None, "blue",
               {}),

    make_piece("East Wing Hall", "East_Wing_Hall_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "orange",
               {}),

    make_piece("Foyer", "Foyer_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               0, 1, None, "orange",
               {}),

    make_piece("Freezer", "Freezer_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'freeze_accounts'}}),

    make_piece("Furnace", "Furnace_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 2, None, "red",
               {'on_draw': {'type': 'inc_fire_weight'}}),

    make_piece("Gallery", "Gallery_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               0, 1, None, "blue",
               {}),

    make_piece("Garage", "Garage_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, 'corner', "blue",
               {'on_enter': {'type': 'detecteur_de_metaux'}}),

    make_piece("Great Hall", "Great_Hall_Icon.png",
               {'up': True, 'down': True, 'left': True, 'right': True},
               0, 1, None, "orange",
               {}),
    make_piece("Greenhouse", "Greenhouse_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               1, 2, 'edge', "green",
               {'on_draw': {'type': 'inc_green_weight'}}),

    make_piece("Guest Bedroom", "Guest_Bedroom_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 2, None, "purple",
               {'on_enter': {'type': 'food', 'amount': 10}}),

    make_piece("Gymnasium", "Gymnasium_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "red",
               {'on_enter': {'type': 'food', 'amount': +2}}),

    make_piece("Hallway", "Hallway_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 0, None, "orange",
               {}),

    make_piece("Her Ladyship's Chamber", "Her_Ladyship's_Chamber_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 2, None, "purple",
               {}),

    make_piece("Kitchen", "Kitchen_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 2, 'edge', "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Laboratory", "Laboratory_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 2, None, "blue",
               {'on_enter':{'type':'detecteur_de_metaux'}}),

    make_piece("Laundry Room", "Laundry_Room_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, None, "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Lavatory", "Lavatory_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, None, "red",
               {}),

    make_piece("Library", "Library_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 3, 'center', "blue",
               {'on_draw': {'type': 'inc_rare_weight'}}),

    make_piece("Locker Room", "Locker_Room_Icon.png",
               {'up': True, 'down': True, 'left': False,  'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'kit_de_crochetage'}}),

    make_piece("Locksmith", "Locksmith_Icon.png",
               {'up': False, 'down': True,  'left': False, 'right': False},
               1, 2, 'edge', "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Maid's Chamber", "Maid_Chamber_Icon.png",
               {'up': False, 'down': True, 'left': True,  'right': False},
               0, 2, None, "red",
               {'on_draw': {'type': 'dec_find_objects'}}),

    make_piece("Mail Room", "Mail_Room_Icon.png",
               {'up': False, 'down': True, 'left': False,  'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'mail_package'}}),

    make_piece("Master Bedroom", "Master_Bedroom_Icon.png",
               {'up': False,  'down': True,  'left': False, 'right': False},
               2, 3, None, "purple",
               {'on_enter': {'type': 'steps_per_room'}}),

    make_piece("Morning Room", "Morning_Room_Icon.png",
               {'up': False,  'down': True, 'left': True,  'right': False},
               1, 2, 'edge', "green",
               {'on_enter': {'type': 'set_gems_next_day', 'amount': 2}}),

    make_piece("Mount Holly Gift Shop", "Mount_Holly_Gift_Shop_Icon.png",
               {'up': False,  'down': True,  'left': True, 'right': True},
               1, 2, 'edge', "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Music Room", "Music_Room_Icon.png",
               {'up': False,  'down': True,  'left': True,  'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'gain_keys_mixed'}}),

    make_piece("Nook", "Nook_Icon.png",
               {'up': False, 'down': True,  'left': True, 'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'gain_keys', 'amount': 1}}),

    make_piece("Nursery", "Nursery_Icon.png",
               {'up': False,  'down': True,  'left': False,  'right': False},
               1, 2, None, "purple",
               {'on_enter': {'type': 'bonus_for_bedrooms'}}),

    make_piece("Observatory", "Observatory_Icon.png",
               {'up': False, 'down': True,  'left': True, 'right': False},
               1, 3, 'center', "blue",
               {'on_draw': {'type': 'observatory_bonus'}}),

    make_piece("Office", "Office_Icon.png",
               {'up': False, 'down': True, 'left': True,  'right': False},
               1, 1, None, "blue",
               {'on_enter': {'type': 'spread_coins'}}),

    make_piece("Pantry", "Pantry_Icon.png",
               {'up': False, 'down': True,  'left': True, 'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'coins', 'amount': 4}}),

    make_piece("Parlor", "Parlor_Icon.png",
               {'up': False, 'down': True, 'left': True,  'right': False},
               0, 1, None, "blue",
               {'on_enter':{'type':'kit_de_crochetage'}}),

    make_piece("Passageway", "Passageway_Icon.png",
               {'up': True,  'down': True,  'left': True,  'right': True},
               0, 0, None, "orange",
               {}),

    make_piece("Patio", "Patio_Icon.png",
               {'up': False,  'down': True, 'left': True,  'right': False},
               1, 2, 'edge', "green",
               {'on_enter': {'type': 'spread_gems_green'}}),

    make_piece("Pump Room", "Pump_Room_Icon.png",
               {'up': False,  'down': True,  'left': True, 'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'water_control'}}),

    make_piece("Room 8", "Room_8_Icon.png",
               {'up': False, 'down': True,  'left': True, 'right': False},
               0, 1, None, "blue",
               {}),

    make_piece("Room 46", "Room_46_Icon.png",
               {'up': False, 'down': False, 'left': False, 'right': False},
               0, 0, 'center', "blue",
               {}),

    make_piece("Rotunda", "Rotunda_Icon.png",
               {'up': False,  'down': True,  'left': True,  'right': False},
               2, 3, 'center', "blue",
               {'on_enter': {'type': 'rotate_house'}}),
    
    make_piece("Rumpus Room", "Rumpus_Room_Icon.png",
               {'up': True,  'down': True,  'left': False,  'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'coins', 'amount': 8}}),

    make_piece("Sauna", "Sauna_Icon.png",
               {'up': False, 'down': True,  'left': False, 'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'steps_next_day', 'amount': 20}}),

    make_piece("Secret Garden", "Secret_Garden_Icon.png",
               {'up': False,  'down': True,  'left': True,  'right': True},
               1, 2, 'edge', "green",
               {'on_enter': {'type': 'spread_fruit'}}),

    make_piece("Secret Passage", "Secret_Passage_Icon.png",
               {'up': False, 'down': True,  'left': False, 'right': False},
               0, 1, None, "orange",
               {'on_enter': {'type': 'teleport_color_choice'}}),

    make_piece("Security", "Security_Icon.png",
               {'up': False,  'down': True, 'left': True,  'right': True},
               1, 2, None, "blue",
               {'on_enter': {'type': 'view_inventory'}}),

    make_piece("Servant's Quarters", "Servant_Quarters_Icon.png",
               {'up': False,  'down': True, 'left': False, 'right': False},
               0, 2, None, "purple",
               {'on_enter': {'type': 'gain_keys_per_bedroom'}}),

    make_piece("Showroom", "Showroom_Icon.png",
               {'up': True,  'down': True,  'left': False, 'right': False},
               1, 2, 'edge', "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("Spare Room", "Spare_Room_Icon.png",
               {'up': True, 'down': True, 'left': False,  'right': False},
               0, 1, None, "blue",
               {'on_enter':{'type':'kit_de_crochetage'}}),

    make_piece("Storeroom", "Storeroom_Icon.png",
               {'up': False,  'down': True,  'left': False, 'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'pelle'}}),

    make_piece("Study", "Study_Icon.png",
               {'up': False, 'down': True, 'left': False,  'right': False},
               1, 3, 'center', "blue",
               {'on_draw': {'type': 'study_redraw_bonus'}}),
    make_piece("Terrace", "Terrace_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               1, 2, 'edge', "green",
               {'on_enter': {'type': 'green_rooms_free'}}),

    make_piece("The Armory", "The_Armory_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               1, 2, None, "yellow",
               {'on_enter': {'type': 'shop'}}),

    make_piece("The Pool", "The_Pool_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               1, 2, 'center', "blue",
               {'on_draw': {'type': 'add_pool_rooms'}}),

    make_piece("Trophy Room", "Trophy_Room_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': False},
               2, 3, 'center', "blue",
               {'on_enter': {'type': 'set_gems', 'amount': 8}}),

    make_piece("Utility Closet", "Utility_Closet_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               0, 1, None, "blue",
               {'on_enter': {'type': 'breaker_box'}}),

    make_piece("Vault", "Vault_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               2, 3, 'center', "blue",
               {'on_enter': {'type': 'coins', 'amount': 40}}),

    make_piece("Veranda", "Veranda_Icon.png",
               {'up': True, 'down': True, 'left': False, 'right': False},
               1, 2, 'edge', "green",
               {'on_enter': {'type': 'inc_find_objects'}}),

    make_piece("Walk-in Closet", "Walk-in_Closet_Icon.png",
               {'up': False, 'down': True, 'left': False, 'right': False},
               1, 2, None, "blue",
               {'on_enter': {'type': 'storeroom_loot'}}),

    make_piece("Weight Room", "Weight_Room_Icon.png",
               {'up': True, 'down': True, 'left': True, 'right': True},
               1, 2, None, "red",
               {'on_enter': {'type': 'lose_half_steps'}}),

    make_piece("West Wing Hall", "West_Wing_Hall_Icon.png",
               {'up': False, 'down': True, 'left': True, 'right': True},
               0, 1, None, "orange",
               {}),
    make_piece("Wine Cellar", "Wine_Cellar_Icon.png",
           {'up': False, 'down': True, 'left': False, 'right': False},
           1, 2, None, "blue",
           {'on_enter': {'type': 'gemmes', 'amount': 3}}),

    make_piece("Workshop", "Workshop_Icon.png",
            {'up': True, 'down': True, 'left': False, 'right': False},
            1, 2, None, "blue",
            {'on_enter': {'type': 'combine_items'}}),

    make_piece("The Foundation", "theFoundation.png",
            {'up': False, 'down': True, 'left': True, 'right': True},
            2, 3, 'center', "blue",
            {'on_enter': {'type': 'no_daily_reset'}}),

])

# multiplicity in initial deck (you can change)
INITIAL_DECK = []
for p in ROOM_CATALOG:
    # ni Entrance Hall ni Antechamber dans la pioche
    if p.nom in ("Entrance Hall", "Antechamber"):
        continue
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
DIRS = {'up':(-1,0), 'down':(1,0), 'left':(0,-1), 'right':(0,1)}
OPP  = {'up':'down','down':'up','left':'right','right':'left'}
DIR_ORDER = ['up', 'right', 'down', 'left']

def rotated_ports(ports_dict, quarter_turns):
    """
    quarter_turns = 0,1,2,3 (0°, 90°, 180°, 270° dans le sens horaire).
    Retourne un nouveau dict ports tourné.
    """
    quarter_turns = quarter_turns % 4
    new_ports = {}
    for i, d in enumerate(DIR_ORDER):
        has_port = ports_dict.get(d, False)
        # nouvelle direction après rotation
        new_dir = DIR_ORDER[(i + quarter_turns) % 4]
        new_ports[new_dir] = has_port
    return new_ports

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
        self.rotation = 0   # 0,1,2,3 → 0°, 90°, 180°, 270°
        self.doors = {'up':None,'down':None,'left':None,'right':None}
        self.interactable=None
        #flags poru des effets uniques
        self.steps_bonus_used = False
        self.coins_collected = False


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

        # place Antechamber at fixed goal position (top middle)
        goal_piece = next((p for p in ROOM_CATALOG if p.nom == "Antechamber"), None)
        if goal_piece is not None:
            self.grid[GOAL_R][GOAL_C].piece = goal_piece

        # mark the entrance cell doors initialization (all doors default None)
        self.inventory = Inventory()
        self.turn_msg = "Welcome to Blue Prince - simplified."
        self.selection_mode = False
        self.candidates = []
        self.selection_pos = 0
        self.target_cell = None
        self.running = True
        self.in_shop=False
        self.shop_active=False 
        self.shop_index=0
        self.scattered_coins=defaultdict(int)
        self.scattered_gems=defaultdict(int)

        # Popup pour portes verrouillées : demander si on utilise une clé
        self.lock_prompt_active = False
        self.lock_prompt_dir = None
        self.lock_prompt_target = None  # (row, col) de la salle derrière la porte
        self.lock_prompt_lock = 0
        self.lock_prompt_choice = 0  # 0 = Oui (utiliser la clé), 1 = Non (garder la clé)

        # pour effet game over
        self.game_over = False
        self.game_over_reason = ""  

    def in_bounds(self, r,c):
        """Vérifie si des coordonnées sont dans les limites de la grille.

        Args:
            r: Index de ligne.
            c: Index de colonne.

        Returns:
            True si (r, c) est à l’intérieur du plateau ; False sinon.
        """    
        return 0<=r<ROWS and 0<=c<COLS
    
    def cell_ports(self, r, c):
        cell = self.grid[r][c]
        if not cell.piece:
            return {'up':False,'down':False,'left':False,'right':False}
        return rotated_ports(cell.piece.ports, cell.rotation)
    
    def piece_ports_with_rotation(self, piece, rotation):
        return rotated_ports(piece.ports, rotation)
    
    def fits_board_and_direction(self, piece, tr, tc, direction):
        """
        Teste si une pièce peut être placée en (tr, tc) en respectant :
        - contrainte 'edge'
        - ports qui ne sortent pas du plateau
        - compatibilité de ports avec les voisins

        C'est le filtre demandé dans l'énoncé (ports & bords).
        """
        # contrainte 'edge' : la pièce ne peut aller qu'en bord si cond_deplac == 'edge'
        cond = piece.cond_deplac
        on_edge = (tr == 0 or tr == ROWS-1 or tc == 0 or tc == COLS-1)
        in_corner = (tr in (0, ROWS-1) and tc in (0, COLS-1))
        in_center = (0 < tr < ROWS-1 and 0 < tc < COLS-1)

        if cond == 'edge' and not on_edge:
            return False
        if cond == 'corner' and not in_corner:
            return False
        if cond == 'center' and not in_center:
            return False
        # si cond == None ou 'any' → pas de contrainte

        # le reste (ports / voisins) est déjà géré
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


    def can_place_with_ports(self, ports, tr, tc, from_dir):
        # 1) la pièce doit avoir un port vers l'origine
        if not ports.get(OPP[from_dir], False):
            return False

        # 2) aucun port ne doit sortir du plateau
        for d, (dr, dc) in DIRS.items():
            if ports.get(d, False):
                nr, nc = tr + dr, tc + dc
                if not self.in_bounds(nr, nc):
                    return False

        # 3) compatibilité avec les voisins déjà posés
        for d, (dr, dc) in DIRS.items():
            nr, nc = tr + dr, tc + dc
            if self.in_bounds(nr, nc):
                neigh_cell = self.grid[nr][nc]
                neigh_piece = neigh_cell.piece
                if neigh_piece is not None:
                    neigh_ports = self.cell_ports(nr, nc)
                    if ports.get(d, False) and not neigh_ports.get(OPP[d], False):
                        return False
                    if neigh_ports.get(OPP[d], False) and not ports.get(d, False):
                        return False
        return True
    
    def can_place_piece(self, piece, tr, tc, from_dir):
        """
        Retourne True si au moins une rotation permet de placer la pièce.
        (la rotation exacte sera choisie ailleurs)
        """
        for rot in range(4):
            ports = self.piece_ports_with_rotation(piece, rot)
            if self.can_place_with_ports(ports, tr, tc, from_dir):
                return True
        return False


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

        Version adoucie :
        - Les 2 premières lignes en partant du bas sont quasiment toujours ouvertes.
        - Les niveaux 2 commencent à apparaître au milieu, et deviennent fréquents en haut.
        """

        # Sécurité : plateau dégénéré
        if ROWS <= 1:
            return 0

        # Ligne du bas (Entrance) : jamais de verrou
        if target_row == ROWS - 1:
            return 0

        # Ligne du haut (Antechamber) : toujours très verrouillé
        if target_row == 0:
            return 2
        
        row_probs = {
            8: (1.0, 0.0, 0.0), # juste au-dessus de l'entrée  tout ouvert
            7: (0.8, 0.2, 0.0),   # un peu de lvl 1
            6: (0.6, 0.3, 0.1),  # très rarement lvl 2
            5: (0.4, 0.4, 0.2),
            4: (0.25, 0.4, 0.35),
            3: (0.15, 0.35, 0.5),
            2: (0.1, 0.3, 0.6),
            1: (0.05, 0.25, 0.7),
        }

        #si ROWS a changé et que la ligne n'est pas dans la table, on fallback doux
        if target_row not in row_probs:
            p0, p1, p2 = 0.5, 0.3, 0.2
        else:
            p0, p1, p2 = row_probs[target_row]

        r = random.random()
        if r < p0:
            return 0
        elif r < p0 + p1:
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
            cur_cell = self.grid[self.player_r][self.player_c]

            #vérifier qu'il y a bien une porte entre les deux salles
            cur_ports = self.cell_ports(self.player_r, self.player_c)
            tgt_ports = self.cell_ports(tr, tc)
            if not (cur_ports.get(direction, False) and
                    tgt_ports.get(self.opposite(direction), False)):
                # pas de porte → pas de déplacement possible
                self.turn_msg = "No door in that direction."
                return

            #lire le verrou du point de vue de la salle actuelle
            lock = cur_cell.doors.get(direction)
            if lock is None:
                lock = 0

            if lock > 0:
                # Cas 1 : niveau 1 avec kit -> on l'utilise automatiquement (gratuit)
                if lock == 1 and self.inventory.objets_permanents.get("kit_de_crochetage"):
                    self.turn_msg = "Door lvl 1: kit used."
                    cur_cell.doors[direction] = 0
                    cell.doors[self.opposite(direction)] = 0

                else:
                    # Pas de kit utilisable -> on propose d'utiliser une clé via popup
                    if self.inventory.objets_consommables.get("cles", 0) > 0:
                        # On ne dépense pas encore la clé, on demande d'abord
                        self.lock_prompt_active = True
                        self.lock_prompt_dir = direction
                        self.lock_prompt_target = (tr, tc)
                        self.lock_prompt_lock = lock
                        self.lock_prompt_choice = 0  # par défaut : "Oui"

                        if lock == 1:
                            self.turn_msg = "Door lvl 1: use a key?"
                        else:
                            self.turn_msg = "Door lvl 2: use a key?"
                        return
                    else:
                        # Pas de kit ni clé
                        if lock == 1:
                            self.turn_msg = "Door lvl 1: locked. Need key or kit."
                        else:
                            self.turn_msg = "Door lvl 2: locked. Need a key (kit doesn't work)."
                        return

            #déplacer le joueur (coût 1 pas)
            if self.inventory.objets_consommables["pas"] <= 0:
                self.turn_msg = "No steps left! You can't move."
                return

            self.inventory.retirer("pas", 1)
            self.player_r, self.player_c = tr, tc
            self.in_shop = False
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
        
        cell = self.grid[self.player_r][self.player_c]

        # Si la salle est une shop, E sert à ouvrir/fermer le menu
        if cell.piece and cell.piece.obj.get('on_enter', {}).get('type') == 'shop':
            if not self.shop_active:
                # On ouvre le menu
                self.shop_active = True
                self.shop_index = 0
                item = SHOP_ITEMS[self.shop_index]
                self.turn_msg = (
                    f"Shop open: {item['label']} ({item['cost']} coins). "
                    "Use ←/→ to choose, ENTER to buy, E to close."
                )
            else:
                # On ferme le menu
                self.shop_active = False
                self.turn_msg = "Closed the shop."
            return
        
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
        
        # Récupérer les ressources dispersées éventuellement présentes ici
        pos = (self.player_r, self.player_c)
        coins_here = self.scattered_coins.get(pos, 0)
        gems_here = self.scattered_gems.get(pos, 0)
        if coins_here or gems_here:
            if coins_here:
                self.inventory.ajouter_conso('pieces', coins_here)
            if gems_here:
                self.inventory.ajouter_conso('gemmes', gems_here)
            self.turn_msg = f"You pick up {coins_here} coins and {gems_here} gems scattered here."
            self.scattered_coins[pos] = 0
            self.scattered_gems[pos] = 0

        self.in_shop=False #par defaut on n'est pas dans une shop
        self.shop_active=False
        effects = p.obj.get('on_enter') if p.obj else None
        if effects:
            t = effects.get('type')
            if t == 'coins':
                amt = effects.get('amount', 0)

                if cell.coins_collected:
                    #on reprend pas les pièces à chaque passage
                    self.turn_msg = f"Entered {p.nom}."
                else:
                    self.inventory.ajouter_conso('pieces', amt)
                    self.turn_msg = f"Found {amt} coins!"
                    cell.coins_collected = True

            elif t == 'food':
                amt = effects.get('amount', 0)

                # bonus de nourriture appliqué une seule fois par salle
                already_eaten = getattr(cell, "food_eaten", False)
                if already_eaten:
                    # on ne redonne pas de pas si on revient
                    self.turn_msg = f"Entered {p.nom}."
                else:
                    self.inventory.ajouter_conso('pas', amt)
                    self.turn_msg = f"Ate food and regains {amt} steps!"
                    cell.food_eaten = True

                #bonus appliqué une seule fois par salle
                already_used = getattr(cell, "steps_bonus_used", False)
                if already_used:
                    #pas de bonus supplémentaire si on revient dans la même room
                    self.turn_msg = f"Entered {p.nom}."
                else:
                    # On compense aussi le coût de déplacement (-1 pas)
                    # pour que le gain net soit bien de `amt` pas.
                    self.inventory.ajouter_conso('pas', amt + 1)
                    self.turn_msg = f"You feel rested and gain {amt} extra steps."
                    cell.steps_bonus_used = True

            elif t=='steps_gain':
                amt=effects.get('amount',0)
                if cell.steps_bonus_used:
                    self.turn_msg='f"Entered {p.nom}.'
                else:
                    self.inventory.ajouter_conso('pas',amt)
                    self.turn_msg=f"You feel rested again {amt} extra steps."
                    cell.steps_bonus_used=True

            elif t=='lose_coin':
                amt=effects.get('amount',1)
                available=self.inventory.objets_consommables.get('pieces',0)
                lost=min(amt,available)
                if lost > 0:
                    self.inventory.retirer('pieces',lost)
                    self.turn_msg=f"You lose {lost} coin(s) in {p.nom}."
                else:
                    self.turn_msg=f"{p.nom} would take your coins, but you have none..."

            elif t=='spread_gems_green':
                #Patio: disperse 1 gemme dans chaque salle verte déjà posée
                count=0
                for rr in range(ROWS):
                    for cc in range (COLS):
                        if (rr,cc)==(self.player_r,self.player_c):
                            continue
                        other=self.grid[rr][cc]
                        if other.piece and other.piece.couleur=='green':
                            self.scattered_gems[(rr,cc)]+=1
                            count+=1
                self.turn_msg=f"You scatter gems into {count} green rooms."

            elif t=='spread_coins':
                #office: disperse 2 pièces dans chaque salle déjà posée
                count=0
                for rr in range (ROWS):
                    for cc in range (COLS):
                        if (rr,cc)==(self.player_r,self.player_c):
                            continue
                        other=self.grid[rr][cc]
                        if other.piece:
                            self.scattered_coins[(rr,cc)]+=2
                            count+=1
                self.turn_msg=f"You hide coins in {count} rooms across the house."

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
            elif t=='detecteur_de_metaux':
                self.inventory.ajouter_perm('detecteur_de_metaux')
                self.turn_msg='You found a metal detector! Keys and coins will be easier to find.'
            elif t=='kit_de_crochetage':
                if not self.inventory.objets_permanents.get('kit_de_crochetage',False):
                    self.inventory.ajouter_perm('kit_de_crochetage')
                    self.turn_msg='You found a kit de crochetage! Level-1 doors can be opened for free.'
                else:
                    self.turn_msg='You already have a kit de crochetage.'
            
            elif t=='pelle':
                if not self.inventory.objets_permanents.get('pelle',False):
                    self.inventory.ajouter_perm('pelle')
                    self.turn_msg='You found a shovel! You can now dig at dig sites.'
                else:
                    self.turn_msg='You already have a shovel.'
            elif t=='marteau':
                if not self.inventory.objets_permanents.get('marteau',False):
                    self.inventory.ajouter_perm('marteau')
                    self.turn_msg='You found a hammer! You can now break chests.'
                else:
                    self.turn_msg='You already have a hammer.'

            elif t=='shop':
                self.turn_msg='You entered the shop. Press E to trade.'
                self.in_shop=True
                self.shop_active=False
                self.shop_index=0

            else:
                self.turn_msg = f"Entered {p.nom}."
        else:
             # Salle sans effet spécial
            self.turn_msg = f"Entered {p.nom}."

        # possibility to find gems or items randomly
        # if detecteur_de_metaux increases keys/coins chance; patte_de_lapin increases chance to find items
        # patte_de_lapin : augmente la probabilité de trouver quelque chose
        # detecteur_de_metaux : biaise vers cles / pieces
        base_find = random.random()
        lapin_bonus = 0.05 if self.inventory.objets_permanents.get('patte_de_lapin') else 0.0

        # Proba de base augmentée : 15 % + bonus éventuel
        if base_find < 0.15 + lapin_bonus:
            has_detector = self.inventory.objets_permanents.get('detecteur_de_metaux', False)

            # Est-ce que le joueur est vraiment à poil pour les portes ?
            no_keys = self.inventory.objets_consommables.get('cles', 0) == 0
            no_kit = not self.inventory.objets_permanents.get('kit_de_crochetage', False)

            if no_keys and no_kit:
                # Situation de galère : on force un pool très favorable aux clés
                pool = ['cles', 'cles', 'cles', 'pieces', 'pas', 'gemmes']
            else:
                if has_detector:
                    # higher probability of finding keys and pieces
                    pool = ['gemmes', 'cles', 'cles', 'pieces', 'pieces', 'des', 'pas']
                else:
                    pool = ['gemmes', 'cles', 'des', 'pieces', 'pas']

            found = random.choice(pool)
            if found == 'gemmes':
                self.inventory.ajouter_conso('gemmes', 1)
                self.turn_msg += " Found 1 gem."
            elif found == 'cles':
                self.inventory.ajouter_conso('cles', 1)
                self.turn_msg += " Found 1 key."
            elif found == 'des':
                self.inventory.ajouter_conso('des', 1)
                self.turn_msg += " Found 1 die."
            elif found == 'pieces':
                self.inventory.ajouter_conso('pieces', 5)
                self.turn_msg += " Found some coins."
            elif found == 'pas':
                self.inventory.ajouter_conso('pas', 3)
                self.turn_msg += " Found 3 steps."

    def confirm_selection(self):
        """Confirme la pièce choisie, la pose et gère les effets associés."""
        # 1) sécurité : on vérifie qu'on est bien en mode sélection
        if not self.selection_mode or not self.target_cell:
            return

        # 2) pièce choisie par le joueur
        index = self.selection_pos
        if index < 0 or index >= len(self.candidates):
            return  # par sécurité

        choice = self.candidates[index]
        tr, tc = self.target_cell

        # 3) direction depuis le joueur vers la nouvelle case
        dr = tr - self.player_r
        dc = tc - self.player_c
        dir_map = {(-1, 0): 'up', (1, 0): 'down', (0, -1): 'left', (0, 1): 'right'}
        direction = dir_map.get((dr, dc))

        # 4) trouver une rotation valide pour cette pièce
        chosen_rot = None
        if direction is not None:
            for rot in range(4):
                ports = self.piece_ports_with_rotation(choice, rot)
                if self.can_place_with_ports(ports, tr, tc, direction):
                    chosen_rot = rot
                    break

        if chosen_rot is None:
            # normalement ne devrait pas arriver si les candidats sont bien filtrés
            self.turn_msg = "No valid orientation for that room here."
            return

        # 5) payer le coût en gemmes si besoin
        if choice.cout > 0:
            if self.inventory.objets_consommables.get('gemmes', 0) < choice.cout:
                self.turn_msg = "Not enough gems to choose that room."
                return
            else:
                self.inventory.retirer('gemmes', choice.cout)

        # 6) poser la pièce dans la grille avec la bonne rotation
        cell = self.grid[tr][tc]
        cell.piece = choice
        cell.rotation = chosen_rot

        # 7) calculer le verrou de la porte
        lock_level = self.door_lock_for_target_row(tr)

        # mettre à jour les portes dans les deux sens
        cur = self.grid[self.player_r][self.player_c]
        if direction:
            cur.doors[direction] = lock_level
            cell.doors[self.opposite(direction)] = lock_level

        # 8) retirer UNE occurrence de cette pièce du deck
        try:
            self.deck.remove(choice)
        except ValueError:
            pass

        # 9) appliquer l'effet "on_draw" éventuel
        od = choice.obj.get('on_draw') if choice.obj else None
        if od:
            typ = od.get('type')
            if typ == 'gem_always':
                self.inventory.ajouter_conso('gemmes', 1)
                self.turn_msg = "You drew a room and found a gem!"
            elif typ == 'inc_green_weight':
                greens = [p for p in ROOM_CATALOG if p.couleur == 'green']
                if greens:
                    self.deck.extend(random.choices(greens, k=2))
                    self.turn_msg = "This veranda increases green rooms in the deck."
            elif typ == 'inc_find_objects':
                self.inventory.ajouter_perm('patte_de_lapin')
                self.turn_msg = "You found something increasing find chances (patte_de_lapin)."
            elif typ == 'inc_fire_weight':
                fires = [p for p in ROOM_CATALOG if p.nom == 'Furnace']
                if fires:
                    self.deck.extend(random.choices(fires, k=2))
                    self.turn_msg = "Furnace makes furnace-like rooms more common in the deck."

            elif typ=='add_pool_rooms':
                #ajoute d'autres pièces spéciales au deck
                extra=[p for p in ROOM_CATALOG
                       if p.nom in ('Chamber of Mirrors','Room 46')]
                self.deck.extend(extra*2)
                self.turn_msg="The pool reveals hidden rooms and adds them to the deck"
        else:
            self.turn_msg = f"Placed {choice.nom} at row {tr}, lock={lock_level}"

        # 10) sortir du mode sélection
        self.selection_mode = False
        self.candidates = []
        self.selection_pos = 0
        self.target_cell = None

        # 11) enfin, essayer d'entrer dans la nouvelle salle
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
                cur_cell = self.grid[self.player_r][self.player_c]
                #convention : verrou côté salle actuelle
                lock = cur_cell.doors.get(d)
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
    
    def shop_move_selection(self, delta):
        """Déplace la sélection dans le menu de shop."""
        if not (self.in_shop and self.shop_active):
            return
        n = len(SHOP_ITEMS)
        if n == 0:
            return
        self.shop_index = (self.shop_index + delta) % n
        item = SHOP_ITEMS[self.shop_index]
        self.turn_msg = (
            f"Shop: {item['label']} ({item['cost']} coins). "
            "ENTER to buy, E to close."
        )

    def shop_buy_current(self):
        """Achète l’objet actuellement sélectionné dans le shop."""
        if not (self.in_shop and self.shop_active):
            self.turn_msg = "You are not in a shop."
            return

        item = SHOP_ITEMS[self.shop_index]
        cost = item["cost"]
        coins = self.inventory.objets_consommables.get("pieces", 0)

        if coins < cost:
            self.turn_msg = (
                f"Not enough coins for {item['label']} "
                f"(need {cost}, you have {coins})."
            )
            return

        # On paie
        self.inventory.retirer("pieces", cost)
        # On applique l'effet (simplement des consommables ici)
        self.inventory.ajouter_conso(item["target"], item["amount"])

        if item["code"] == "cles":
            gained = f"{item['amount']} key(s)"
        else:
            # steps et food transforment tous deux en pas
            gained = f"{item['amount']} steps"

        self.turn_msg = f"Bought {item['label']} for {cost} coins. Gained {gained}."
    def resolve_lock_prompt(self, use_key: bool):
        """
        Résout la popup de porte verrouillée.

        Paramètres
        ----------
        use_key : bool
            - True  -> le joueur accepte d'utiliser une clé pour ouvrir la porte.
            - False -> le joueur refuse, la porte reste verrouillée.

        Comportement
        ------------
        - Si le joueur refuse : on ferme simplement la popup et on ne bouge pas.
        - Si le joueur accepte :
            * on vérifie qu'il reste bien une clé dans l'inventaire,
            * on débite 1 clé,
            * on met le verrou de la porte à 0 des deux côtés,
            * on consomme 1 "pas" et on déplace le joueur dans la nouvelle room,
              puis on applique les effets de la room via `on_enter`.
        """
        # Si aucune popup n'est active, on ne fait rien (sécurité)
        if not self.lock_prompt_active or self.lock_prompt_dir is None or self.lock_prompt_target is None:
            return

        # On récupère les infos mémorisées au moment où la popup a été ouverte
        direction = self.lock_prompt_dir
        tr, tc = self.lock_prompt_target
        lock = self.lock_prompt_lock

        # On réinitialise l'état de la popup
        self.lock_prompt_active = False
        self.lock_prompt_dir = None
        self.lock_prompt_target = None

        # Cas où le joueur choisit "Non" : on garde la clé, la porte reste fermée
        if not use_key:
            self.turn_msg = "You decide to keep your key."
            return

        # Si on arrive ici, le joueur a choisi "Oui" -> on essaie de consommer une clé
        if self.inventory.objets_consommables.get("cles", 0) <= 0:
            # Normalement ça ne devrait pas arriver (on vérifie avant d'ouvrir la popup),
            # mais au cas où l'état a changé entre temps.
            self.turn_msg = "No key left!"
            return

        # Débiter 1 clé
        self.inventory.retirer("cles", 1)

        # Mettre la porte à 0 des deux côtés (ouverte)
        cur_cell = self.grid[self.player_r][self.player_c]
        cell = self.grid[tr][tc]
        cur_cell.doors[direction] = 0
        cell.doors[self.opposite(direction)] = 0

        # Message en fonction du niveau de verrou
        if lock == 1:
            self.turn_msg = "Door lvl 1: key used."
        else:
            self.turn_msg = "Door lvl 2: key used."

        # Puis on essaie de déplacer le joueur (il faut des pas)
        if self.inventory.objets_consommables.get("pas", 0) <= 0:
            # Porte ouverte mais pas assez de pas pour rentrer
            self.turn_msg += " But you have no steps left to move."
            return

        # Consommer 1 pas pour entrer dans la salle
        self.inventory.retirer("pas", 1)
        self.player_r, self.player_c = tr, tc
        self.in_shop = False

        # Appliquer les effets de la nouvelle room
        self.on_enter(cell)

# -------------------------
# Pygame rendering
# -------------------------
import pygame
pygame.font.init()

def load_item_image(name, size=(24, 24)):
    """Charge une icône d'objet depuis le dossier items."""
    path = os.path.join("model/items/", name)
    try:
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        return None
    
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
                    # rotation en degrés dans le sens horaire -> Pygame tourne dans le sens anti-horaire
                    angle = -90 * cell.rotation   # 0, -90, -180, -270
                    img_rot = pygame.transform.rotate(img, angle)
                    # recentrer (la taille peut changer)
                    img_rect = img_rot.get_rect(center=rect.center)
                    screen.blit(img_rot, img_rect.topleft)
                else:
                    # colored placeholder based on piece color
                    clr = {'green':(60,130,60),'purple':(110,60,110),'orange':(200,120,60),'blue':(60,90,160),'yellow': (190,170,60),
    'red':    (180,60,60),}.get(cell.piece.couleur,(120,120,120))
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
    pygame.draw.rect(
        screen,
        (25, 25, 25),
        (panel_x - 15, 10, WINDOW_W - panel_x - 25, WINDOW_H - 20),
        border_radius=10,
    )
    pygame.draw.rect(
        screen,
        (60, 60, 70),
        (panel_x - 15, 10, WINDOW_W - panel_x - 25, 40),
        border_radius=10,
    )
    screen.blit(EMOJI_FONT.render("Inventory", True, (255, 255, 255)), (panel_x, 18))

    inv = game.inventory

    # --- Consumables ---
    y = 60
    screen.blit(EMOJI_FONT.render("Consumables", True, (210, 210, 255)), (panel_x, y))

    y += 22
    for k, v in inv.objets_consommables.items():
        icon_name = {
            "pas": "steps.png",
            "pieces": "coin.png",
            "gemmes": "gems.png",
            "cles": "key.png",
            "des": "die.png",
        }.get(k, None)

        text_x = panel_x + 5

        if icon_name:
            img = load_item_image(icon_name, size=(24, 24))
            if img:
                screen.blit(img, (panel_x + 5, y))
                text_x = panel_x + 5 + 24 + 6  # texte à droite de l’icône

        bar_len = min(120, v * 2)
        pygame.draw.rect(screen, (80, 80, 150), (panel_x + 130, y + 5, bar_len, 6))

        txt = FONT.render(f"{k} : {v}", True, (230, 230, 230))
        screen.blit(txt, (text_x, y))

        y += 30

    # --- Permanents ---
    y += 8
    screen.blit(EMOJI_FONT.render("Permanents", True, (210, 210, 255)), (panel_x, y))

    y += 22
    for k, v in inv.objets_permanents.items():
        icon_name = {
            "pelle": "shovel.png",
            "marteau": "hammer.png",
            "kit_de_crochetage": "lockpick.png",
            "detecteur_de_metaux": "detector.png",
            "patte_de_lapin": "rabbitfoot.png",
        }.get(k, None)

        text_x = panel_x + 5

        if icon_name:
            img = load_item_image(icon_name, size=(24, 24))
            if img:
                if not v:
                    gray = img.copy()
                    gray.fill((80, 80, 80), None, pygame.BLEND_RGBA_MULT)
                    img = gray
                screen.blit(img, (panel_x + 5, y))
                text_x = panel_x + 5 + 24 + 6

        color = (230, 255, 230) if v else (140, 140, 140)
        txt = FONT.render(f"{k}", True, color)
        screen.blit(txt, (text_x, y))

        y += 26 
    #GAme over

    if getattr(game, "game_over", False):
        s = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        screen.blit(s, (0, 0))

        w, h = 500, 160
        px = (WINDOW_W - w) // 2
        py = (WINDOW_H - h) // 2
        pygame.draw.rect(screen, (40,40,50), (px, py, w, h), border_radius=10)
        pygame.draw.rect(screen, (200,200,220), (px, py, w, 35), border_radius=10)

        title = BIG.render("Game Over", True, (0,0,0))
        screen.blit(title, (px + 20, py + 5))

        reason = FONT.render(game.game_over_reason, True, (230,230,230))
        screen.blit(reason, (px + 20, py + 60))

        hint = FONT.render("Press ENTER or ESC to quit", True, (200,200,200))
        screen.blit(hint, (px + 20, py + 95))

    #Shop panel
    if game.in_shop:
        y += 10
        title = "🏬 Shop (press E)" if not game.shop_active else "🏬 Shop (←/→, ENTER, E)"
        screen.blit(EMOJI_FONT.render(title, True, (210,210,255)), (panel_x, y))
        y += 22

        for i, item in enumerate(SHOP_ITEMS):
            selected = (i == game.shop_index and game.shop_active)
            prefix = "> " if selected else "  "
            color = (255,255,0) if selected else (220,220,220)
            txt = FONT.render(
                f"{prefix}{item['label']}  [{item['cost']} coins]",
                True,
                color
            )
            screen.blit(txt, (panel_x+5, y))
            y += 18


    # bottom message
    msgsurf = FONT.render("Msg: " + game.turn_msg, True, (240,240,240))
    screen.blit(msgsurf, (panel_x, WINDOW_H - 40))
    
    # selection mode overlay
    if game.selection_mode:
        # fond assombri
        s = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        screen.blit(s, (0, 0))

        # panneau central
        w = 620
        h = 230
        px = (WINDOW_W - w) // 2
        py = (WINDOW_H - h) // 2
        pygame.draw.rect(screen, (50, 50, 60), (px, py, w, h), border_radius=10)
        pygame.draw.rect(screen, (200, 200, 220), (px, py, w, 30), border_radius=10)
        screen.blit(
            BIG.render("Choose a room (ENTER) or R to redraw (spend die)", True, (0, 0, 0)),
            (px + 8, py + 4)
        )

        # cartes de rooms
        cx = px + 20
        cy = py + 45
        card_w = (w - 60) // 3 # 3 cartes + marges
        card_h = h - 80

        for i, cand in enumerate(game.candidates):
            crect = pygame.Rect(cx + i * (card_w + 10), cy, card_w, card_h)
            pygame.draw.rect(screen, (80, 80, 90), crect, border_radius=8)

            #vignette carrée propre
            thumb_size = min(card_w - 20, card_h - 70)  # laisse de la place pour le texte
            img = load_image(cand.image_id, size=(thumb_size, thumb_size))
            if img:
                img_rect = img.get_rect()
                img_rect.centerx = crect.centerx
                img_rect.top = crect.top + 8
                screen.blit(img, img_rect.topleft)
            else:
                # placeholder carré
                placeholder = pygame.Rect(0, 0, thumb_size, thumb_size)
                placeholder.centerx = crect.centerx
                placeholder.top = crect.top + 8
                pygame.draw.rect(screen, (100, 100, 120), placeholder)

            display_name = cand.nom if len(cand.nom) <= 18 else cand.nom[:17] + "…"
            text_y = crect.bottom - 40
            name_surf = FONT.render(display_name, True, (255, 255, 255))
            screen.blit(name_surf, (crect.x + 6, text_y))
            info_surf = FONT.render(
                f"Cost: {cand.cout}   Rarity: {cand.degre_rarete}", True, (210, 210, 210)
            )
            screen.blit(info_surf, (crect.x + 6, text_y + 18))
            # surbrillance du sélection
            if i == game.selection_pos:
                pygame.draw.rect(screen, (255, 255, 0), crect, 3, border_radius=8)



    # --- Popup "Utiliser une clé ?" ---
    if getattr(game, "lock_prompt_active", False):
        # fond semi-transparent
        s = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        screen.blit(s, (0, 0))

        # panneau central
        w, h = 480, 170
        px = (WINDOW_W - w) // 2
        py = (WINDOW_H - h) // 2

        pygame.draw.rect(screen, (50, 50, 60), (px, py, w, h), border_radius=10)
        pygame.draw.rect(screen, (200, 200, 220), (px, py, w, 30), border_radius=10)
        screen.blit(
            BIG.render("Locked door", True, (0, 0, 0)),
            (px + 12, py + 4)
        )

        # texte principal = message actuel
        txt = FONT.render(game.turn_msg, True, (230, 230, 230))
        screen.blit(txt, (px + 20, py + 55))

        # Deux "boutons" Oui / Non
        btn_w = 140
        btn_h = 40
        gap = 40

        # position des boutons
        total_btn_width = 2 * btn_w + gap
        base_x = px + (w - total_btn_width) // 2
        y_btn = py + h - 60

        # bouton Oui (index 0)
        rect_oui = pygame.Rect(base_x, y_btn, btn_w, btn_h)
        # bouton Non (index 1)
        rect_non = pygame.Rect(base_x + btn_w + gap, y_btn, btn_w, btn_h)

        # couleurs des boutons
        for idx, (rect, label) in enumerate(((rect_oui, "Oui"), (rect_non, "Non"))):
            # arrière-plan
            pygame.draw.rect(screen, (80, 80, 95), rect, border_radius=8)

            # bord jaune si sélectionné
            if game.lock_prompt_choice == idx:
                pygame.draw.rect(screen, (255, 255, 0), rect, width=3, border_radius=8)
            else:
                pygame.draw.rect(screen, (200, 200, 220), rect, width=1, border_radius=8)

            # texte du bouton
            label_surf = BIG.render(label, True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=rect.center)
            screen.blit(label_surf, label_rect.topleft)




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
                # ESC : toujours quitter
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

                # Si Game Over : ENTER / SPACE quittent, le reste = ignoré
                if game.game_over:
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        pygame.quit()
                        return
                    continue

                # --- Si une popup de porte est active, on gère d'abord ça ---
                if game.lock_prompt_active:
                    # Flèches (ou Q/D) pour changer de choix : 0 = Oui, 1 = Non
                    if ev.key in (pygame.K_LEFT, pygame.K_q):
                        game.lock_prompt_choice = 0
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        game.lock_prompt_choice = 1
                    elif ev.key == pygame.K_RETURN:
                        # ENTER valide le choix courant
                        use_key = (game.lock_prompt_choice == 0)
                        game.resolve_lock_prompt(use_key)
                    # Tant que la popup est ouverte, on ne traite pas les autres inputs
                    continue

                # --- Sinon, logique normale du jeu ---
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
                    # Si le menu de shop est ouvert, les touches servent au shop
                    if game.shop_active:
                        if ev.key in (pygame.K_LEFT, pygame.K_q):
                            game.shop_move_selection(-1)
                        elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                            game.shop_move_selection(+1)
                        elif ev.key == pygame.K_RETURN:
                            game.shop_buy_current()
                        elif ev.key == pygame.K_e:
                            game.interact_current_cell()  # ferme le shop
                        # Les touches de mouvement sont ignorées tant que le shop est ouvert
                    
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
                        elif ev.key == pygame.K_e:
                            game.interact_current_cell()
                        elif ev.key == pygame.K_i:
                            # toggle inventory? (we always show)
                            pass
                    
        # check lose condition
        if not game.game_over:
            if game.inventory.objets_consommables.get('pas',0) <= 0:
                game.turn_msg = "You ran out of steps! Game Over."
                game.game_over = True
                game.game_over_reason = "You ran out of steps."

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
    game_loop()      # starts 