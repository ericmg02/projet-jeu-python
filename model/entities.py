class Port:
    def __init__(self,level):
        self.level=int(level)

class Piece:
    def __init__(self,nom,ports,cout,degre_rarete,cond_deplac,couleur,obj,image_id=None):
        self.__nom=nom
        self.__image_id=image_id
        self.__cout=cout
        self.__degre_rarete=degre_rarete
        self.__ports=ports
        self.__cond_deplac=cond_deplac
        self.__couleur=couleur
        self.__obj=obj

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
    def proba_tirage(self): #pour calculer la proba de tirer une piece suivant sa rareté
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
        self.objets_consommables[nom_objet] += quantitee
    def retirer(self, nom_objet, quantitee):
        if self.objets_consommables[nom_objet] >= quantitee:
            self.objets_consommables[nom_objet] -= quantitee
    #objets permanents
    def ajouter_perm(self, nom_objet):
        self.objets_permanents[nom_objet] = True

    
