# -*- coding: utf-8 -*-
"""
Module de cartographie des périmètres écologiques pour le plugin MapCEN
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsVectorLayer,
    QgsDataSourceUri
)
from qgis.utils import iface
import os
import urllib
import csv
import io
from datetime import date

from .base_module import BaseModule


class CartoPerimetresEcologiquesModule(BaseModule):
    """
    Module pour la cartographie des périmètres écologiques
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du module
        """
        super(CartoPerimetresEcologiquesModule, self).__init__(parent)
        self.layout_carto_perim_eco = None
        self.my_map1 = None
        self.layout = None
        self.manager = None
        self.scalebar = None
    
    def init(self):
        """
        Initialise le module (connexions des signaux, etc.)
        """
        # Charger les périmètres écologiques disponibles
        self._charger_liste_perimetres_ecologiques()
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module
        """
        # Supprimer la mise en page si elle existe
        if self.layout_carto_perim_eco:
            manager = QgsProject.instance().layoutManager()
            layout_name = 'Mise en page automatique MapCEN (Périmètres écologiques)'
            if manager.layoutByName(layout_name):
                manager.removeLayout(manager.layoutByName(layout_name))
        
        # Masquer la combobox des périmètres écologiques
        if self.dlg and self.dlg.mComboBox_3.isVisible():
            self.dlg.mComboBox_3.hide()
            self.dlg.label_15.hide()
    
    def _charger_liste_perimetres_ecologiques(self):
        """
        Charge la liste des périmètres écologiques disponibles depuis le fichier CSV
        et les ajoute à la combobox
        """
        try:
            # Lire le fichier CSV contenant les flux CEN
            url_open = urllib.request.urlopen("https://raw.githubusercontent.com/CEN-Nouvelle-Aquitaine/fluxcen/main/flux.csv")
            flux = url_open.read().decode('utf-8')
            
            # Créer un dictionnaire à partir du CSV
            csvReader = list(csv.DictReader(io.StringIO(flux), delimiter=';'))
            
            # Filtrer les lignes pour ne garder que les données correspondantes à la catégorie "Périmètres écologiques"
            filtered_rows = [row for row in csvReader if row['categorie'] == 'Périmètres écologiques']
            
            nom_perim_eco = []
            
            for item in filtered_rows:
                # Récupérer tous les noms des flux pour les ajouter à une liste
                nom_perim_eco.append(item['Nom_couche_plugin'])
            
            # Faire apparaître la comboBox et configurer son contenu
            self.dlg.mComboBox_3.clear()
            self.dlg.mComboBox_3.setDefaultText("Sélectionnez un/des périmètre(s) écologique(s)")
            if not self.dlg.mComboBox_3.isVisible():
                self.dlg.mComboBox_3.show()
            self.dlg.mComboBox_3.setCurrentIndex(-1)
            self.dlg.mComboBox_3.addItems(nom_perim_eco)
            
            # Afficher le label associé
            self.dlg.label_15.setText("Sélectionnez un/des périmètre(s) écologique(s)")
            self.dlg.label_15.show()
            
        except Exception as e:
            QMessageBox.warning(self.dlg, "Erreur", f"Impossible de charger la liste des périmètres écologiques: {str(e)}")
    
    def chargement_perim_eco(self):
        """
        Charge les couches de périmètres écologiques sélectionnées
        """
        try:
            # Lire le fichier CSV contenant les flux CEN
            url_open = urllib.request.urlopen("https://raw.githubusercontent.com/CEN-Nouvelle-Aquitaine/fluxcen/main/flux.csv")
            flux = url_open.read().decode('utf-8')
            
            # Créer un dictionnaire à partir du CSV
            csvReader = list(csv.DictReader(io.StringIO(flux), delimiter=';'))
            
            # Filtrer les lignes pour ne garder que les données correspondantes à la catégorie "Périmètres écologiques"
            filtered_rows = [row for row in csvReader if row['categorie'] == 'Périmètres écologiques']
            
            # Récupérer les périmètres écologiques sélectionnés
            selected_perimeters = self.dlg.mComboBox_3.checkedItems()
            
            if not selected_perimeters:
                QMessageBox.warning(self.dlg, "Avertissement", "Veuillez sélectionner au moins un périmètre écologique.")
                return
            
            # Charger chaque périmètre sélectionné
            for perimetre in selected_perimeters:
                # Trouver les informations correspondantes dans le CSV
                perim_info = next((item for item in filtered_rows if item['Nom_couche_plugin'] == perimetre), None)
                
                if perim_info:
                    # Créer l'URI pour la couche WFS
                    uri = QgsDataSourceUri()
                    uri.setParam("url", perim_info['url'])
                    uri.setParam("typename", perim_info['nom_technique'])
                    
                    # Appliquer l'authentification si nécessaire
                    from qgis.utils import plugins
                    map_cen_instance = plugins['map_cen']
                    if not map_cen_instance.apply_authentication_if_needed(uri):
                        continue  # Passer au périmètre suivant si l'authentification échoue
                    
                    # Charger la couche
                    layer = QgsVectorLayer(uri.uri(), perimetre, "WFS")
                    
                    if not layer.isValid():
                        QMessageBox.warning(self.dlg, "Erreur de chargement", f"Impossible de charger la couche '{perimetre}'.")
                    else:
                        QgsProject.instance().addMapLayer(layer)
            
            # Zoomer sur l'étendue des sites sélectionnés
            sites_layer = QgsProject.instance().mapLayersByName("Sites gérés CEN-NA")[0]
            sites_layer.removeSelection()
            
            for site in self.dlg.mComboBox.checkedItems():
                sites_layer.selectByExpression(f'"nom_site"= \'{site.replace("\'", "\'\'")}\''
                                             , QgsVectorLayer.AddToSelection)
            
            iface.mapCanvas().zoomToSelected(sites_layer)
            
        except Exception as e:
            QMessageBox.warning(self.dlg, "Erreur", f"Erreur lors du chargement des périmètres écologiques: {str(e)}")
    
    def mise_en_page(self):
        """
        Génère la mise en page pour la cartographie des périmètres écologiques
        """
        # Vérifier que des sites sont sélectionnés
        if not self.dlg.mComboBox.checkedItems():
            QMessageBox.warning(self.dlg, "Avertissement", "Veuillez sélectionner au moins un site.")
            return
        
        # Vérifier que des périmètres écologiques sont sélectionnés
        if not self.dlg.mComboBox_3.checkedItems():
            QMessageBox.warning(self.dlg, "Avertissement", "Veuillez sélectionner au moins un périmètre écologique.")
            return
        
        # Charger les périmètres écologiques si ce n'est pas déjà fait
        self.chargement_perim_eco()
        
        # Créer une nouvelle mise en page
        self.manager = QgsProject.instance().layoutManager()
        layout_name = 'Mise en page automatique MapCEN (Périmètres écologiques)'
        
        # Supprimer la mise en page si elle existe déjà
        if self.manager.layoutByName(layout_name):
            self.manager.removeLayout(self.manager.layoutByName(layout_name))
        
        self.layout = QgsPrintLayout(QgsProject.instance())
        self.layout.initializeDefaults()
        self.layout.setName(layout_name)
        
        # Ajouter une carte à la mise en page
        self.my_map1 = QgsLayoutItemMap(self.layout)
        self.my_map1.setRect(20, 20, 20, 20)
        
        # Définir l'étendue de la carte
        canvas = iface.mapCanvas()
        self.my_map1.setExtent(canvas.extent())
        
        # Ajouter la carte à la mise en page
        self.layout.addLayoutItem(self.my_map1)
        self.my_map1.attemptMove(QgsLayoutPoint(5, 30, QgsUnitTypes.LayoutMillimeters))
        self.my_map1.attemptResize(QgsLayoutSize(287, 150, QgsUnitTypes.LayoutMillimeters))
        
        # Ajouter un titre à la mise en page
        title = QgsLayoutItemLabel(self.layout)
        self.layout.addLayoutItem(title)
        titre = str(', '.join(self.dlg.mComboBox.checkedItems()))
        title.setText(titre)
        title.setFont(QFont("Calibri", 16, QFont.Bold))
        title.attemptMove(QgsLayoutPoint(5, 6, QgsUnitTypes.LayoutMillimeters))
        title.attemptResize(QgsLayoutSize(297, 7, QgsUnitTypes.LayoutMillimeters))
        title.setHAlign(Qt.AlignHCenter)
        title.setVAlign(Qt.AlignHCenter)
        title.adjustSizeToText()
        self.layout.addItem(title)
        
        # Ajouter un sous-titre à la mise en page
        subtitle = QgsLayoutItemLabel(self.layout)
        self.layout.addLayoutItem(subtitle)
        date_du_jour = date.today().strftime("%d/%m/%Y")
        titre = f"Périmètres d'intérêts écologiques à proximité des sites ({date_du_jour})"
        subtitle.setText(titre)
        subtitle.setFont(QFont("Calibri", 14))
        subtitle.attemptMove(QgsLayoutPoint(5, 14, QgsUnitTypes.LayoutMillimeters))
        subtitle.attemptResize(QgsLayoutSize(297, 7, QgsUnitTypes.LayoutMillimeters))
        subtitle.setHAlign(Qt.AlignHCenter)
        subtitle.setVAlign(Qt.AlignHCenter)
        subtitle.adjustSizeToText()
        self.layout.addItem(subtitle)
        
        # Ajouter le logo CEN NA en haut à gauche de la page
        layoutItemPicture = QgsLayoutItemPicture(self.layout)
        layoutItemPicture.setResizeMode(QgsLayoutItemPicture.Zoom)
        layoutItemPicture.setMode(QgsLayoutItemPicture.FormatRaster)
        layoutItemPicture.setPicturePath(os.path.dirname(os.path.dirname(__file__)) + '/logo.jpg')
        
        layoutItemPicture.attemptMove(QgsLayoutPoint(5.5, 3.5, QgsUnitTypes.LayoutMillimeters))
        layoutItemPicture.attemptResize(QgsLayoutSize(720, 249, QgsUnitTypes.LayoutPixels))
        
        self.layout.addLayoutItem(layoutItemPicture)
        
        # Ajouter l'échelle à la mise en page
        self.scalebar = QgsLayoutItemScaleBar(self.layout)
        self.scalebar.setStyle('Single Box')
        self.scalebar.setLinkedMap(self.my_map1)
        self.scalebar.applyDefaultSize()
        self.scalebar.applyDefaultSettings()
        
        self.scalebar.setNumberOfSegments(2)
        self.scalebar.setNumberOfSegmentsLeft(0)
        
        self.layout.addLayoutItem(self.scalebar)
        self.scalebar.attemptMove(QgsLayoutPoint(206, 185, QgsUnitTypes.LayoutMillimeters))
        self.scalebar.setFixedSize(QgsLayoutSize(50, 15))
        
        # Ajouter la flèche du Nord
        north = QgsLayoutItemPicture(self.layout)
        north.setPicturePath(os.path.dirname(os.path.dirname(__file__)) + "/NorthArrow_02.svg")
        self.layout.addLayoutItem(north)
        north.attemptResize(QgsLayoutSize(19, 14, QgsUnitTypes.LayoutMillimeters))
        north.attemptMove(QgsLayoutPoint(273, 184, QgsUnitTypes.LayoutMillimeters))
        
        # Ajouter les crédits
        info = [f"Réalisation : DSI / CEN Nouvelle-Aquitaine ({date_du_jour}) \n Source: © Fond carto IGN, cadastre ETALAB, MNHN-INPN, CEN Nouvelle-Aquitaine"]
        credit_text = QgsLayoutItemLabel(self.layout)
        credit_text.setText(info[0])
        credit_text.setFont(QFont("Calibri", 11))
        self.layout.addLayoutItem(credit_text)
        credit_text.attemptMove(QgsLayoutPoint(158.413, 148, QgsUnitTypes.LayoutMillimeters))
        credit_text.attemptResize(QgsLayoutSize(133.737, 16, QgsUnitTypes.LayoutMillimeters))
        credit_text.setBackgroundEnabled(True)
        credit_text.setBackgroundColor(QColor('white'))
        credit_text.setItemOpacity(0.7)
        credit_text.setHAlign(Qt.AlignHCenter)
        credit_text.setVAlign(Qt.AlignVCenter)
        
        # Ajouter la mise en page au projet via son gestionnaire
        self.manager.addLayout(self.layout)
        
        self.layout_carto_perim_eco = QgsProject.instance().layoutManager().layoutByName(layout_name).clone()
        
        self.dlg.graphicsView.setScene(self.layout_carto_perim_eco)
