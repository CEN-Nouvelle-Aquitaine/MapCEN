# -*- coding: utf-8 -*-
"""
Gestionnaire de modules pour le plugin MapCEN
"""
from .carto_travaux_module import CartoTravauxModule
from .carto_localisation_generale_module import CartoLocalisationGeneraleModule
from .carto_perimetres_ecologiques_module import CartoPerimetresEcologiquesModule
from .carto_mfu_module import CartoMFUModule


class ModuleManager:
    """
    Gestionnaire de modules pour le plugin MapCEN.
    Gère le cycle de vie des modules et leur interaction avec le plugin principal.
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du gestionnaire de modules
        
        Args:
            parent: Le parent de ce gestionnaire (généralement l'instance principale du plugin)
        """
        self.parent = parent
        self.modules = {}
        self.active_module = None
        self.dlg = None
        
        # Initialiser les modules
        self._initialize_modules()
    
    def _initialize_modules(self):
        """
        Initialise tous les modules disponibles
        """
        self.modules = {
            'travaux': CartoTravauxModule(self.parent),
            'localisation_generale': CartoLocalisationGeneraleModule(self.parent),
            'perimetres_ecologiques': CartoPerimetresEcologiquesModule(self.parent),
            'mfu': CartoMFUModule(self.parent)
        }
    
    def setup(self, dlg):
        """
        Configure le gestionnaire avec la boîte de dialogue principale
        
        Args:
            dlg: La boîte de dialogue principale du plugin
        """
        self.dlg = dlg
        
        # Connecter les signaux de la boîte de dialogue
        self.dlg.comboBox_3.currentTextChanged.connect(self.on_module_selection_changed)
        self.dlg.commandLinkButton_4.clicked.connect(self.on_generate_button_clicked)
        self.dlg.commandLinkButton.clicked.connect(self.on_generate_mfu_clicked)
    
    def on_module_selection_changed(self, text):
        """
        Gère le changement de sélection de module dans la combobox
        
        Args:
            text: Le texte sélectionné dans la combobox
        """
        # Nettoyer le module actif s'il existe
        if self.active_module:
            self.active_module.cleanup()
            self.active_module = None
        
        # Activer le module correspondant au texte sélectionné
        if text == "Travaux":
            self.active_module = self.modules['travaux']
        elif text == "Localisation générale":
            self.active_module = self.modules['localisation_generale']
        elif text == "Périmètres écologiques":
            self.active_module = self.modules['perimetres_ecologiques']
        
        # Configurer le module actif
        if self.active_module:
            self.active_module.setup(self.dlg)
    
    def on_generate_button_clicked(self):
        """
        Gère le clic sur le bouton de génération de carte
        """
        if self.active_module:
            if hasattr(self.active_module, 'choix_mise_en_page'):
                self.active_module.choix_mise_en_page()
            elif hasattr(self.active_module, 'mise_en_page'):
                self.active_module.mise_en_page()
    
    def on_generate_mfu_clicked(self):
        """
        Gère le clic sur le bouton de génération de mise en page MFU
        """
        # Activer le module MFU
        self.active_module = self.modules['mfu']
        self.active_module.setup(self.dlg)
        
        # Générer la mise en page
        self.active_module.mise_en_page()
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par tous les modules
        """
        for module in self.modules.values():
            if module.initialized:
                module.cleanup()
        
        # Déconnecter les signaux
        if self.dlg:
            self.dlg.comboBox_3.currentTextChanged.disconnect(self.on_module_selection_changed)
            self.dlg.commandLinkButton_4.clicked.disconnect(self.on_generate_button_clicked)
            self.dlg.commandLinkButton.clicked.disconnect(self.on_generate_mfu_clicked)
