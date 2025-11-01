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
        return self.__self
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

class Inventory:
    pass

    
