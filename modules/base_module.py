# -*- coding: utf-8 -*-
"""
Module de base pour tous les modules du plugin MapCEN
"""


class BaseModule:
    """
    Classe de base pour tous les modules du plugin MapCEN.
    Chaque module doit hériter de cette classe et implémenter les méthodes requises.
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du module
        
        Args:
            parent: Le parent de ce module (généralement l'instance principale du plugin)
        """
        self.parent = parent
        self.dlg = None
        self.initialized = False
    
    def setup(self, dlg):
        """
        Configure le module avec la boîte de dialogue principale
        
        Args:
            dlg: La boîte de dialogue principale du plugin
        """
        self.dlg = dlg
        if not self.initialized:
            self.init()
            self.initialized = True
    
    def init(self):
        """
        Initialise le module (connexions des signaux, etc.)
        Cette méthode doit être implémentée par les classes enfants
        """
        raise NotImplementedError("La méthode init() doit être implémentée par les classes enfants")
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module
        Cette méthode doit être implémentée par les classes enfants
        """
        raise NotImplementedError("La méthode cleanup() doit être implémentée par les classes enfants")
