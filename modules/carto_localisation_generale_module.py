# -*- coding: utf-8 -*-
"""
Module de cartographie de localisation générale pour le plugin MapCEN
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsVectorLayer,
    QgsWkbTypes, QgsSymbol, QgsRuleBasedRenderer, QgsGeometryGeneratorSymbolLayer
)
import os
from datetime import date

from .base_module import BaseModule


class CartoLocalisationGeneraleModule(BaseModule):
    """
    Module pour la cartographie de localisation générale
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du module
        """
        super(CartoLocalisationGeneraleModule, self).__init__(parent)
        self.layout_carto_generale = None
        self.sites_gere_centroid_layer = None
        self.depts_NA = None
        self.my_map1 = None
        self.layout = None
        self.manager = None
        self.scalebar = None
    
    def init(self):
        """
        Initialise le module (connexions des signaux, etc.)
        """
        # Sélectionner le bouton radio par défaut
        self.dlg.radioButton_4.setChecked(True)
        
        # Désactiver les boutons radio non utilisés
        self.dlg.radioButton.setEnabled(False)
        self.dlg.radioButton_2.setEnabled(False)
        self.dlg.radioButton_3.setEnabled(False)
        
        # Masquer la comboBox et son label quand le module est initialisé
        if self.dlg.mComboBox_3.isVisible():
            self.dlg.mComboBox_3.hide()
        
        self.dlg.mComboBox_3.clear()
        self.dlg.label_15.setText("")
        self.dlg.label_15.hide()
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module
        """
        # Réinitialiser les sélections
        if self.sites_gere_centroid_layer:
            self.sites_gere_centroid_layer.removeSelection()
        
        if self.depts_NA:
            self.depts_NA.removeSelection()
        
        # Supprimer la mise en page si elle existe
        if self.layout_carto_generale:
            manager = QgsProject.instance().layoutManager()
            layout_name = 'Mise en page automatique MapCEN (Carto de localisation générale)'
            if manager.layoutByName(layout_name):
                manager.removeLayout(manager.layoutByName(layout_name))
    
    def mise_en_page(self):
        """
        Génère la mise en page pour la cartographie de localisation générale
        """
        # Récupérer les couches nécessaires
        layer = QgsProject.instance().mapLayersByName("Parcelles CEN NA en MFU")[0]
        self.sites_gere_centroid_layer = QgsProject.instance().mapLayersByName("Sites gérés CEN-NA")[0]
        self.depts_NA = QgsProject.instance().mapLayersByName("Département")[0]
        
        # Appliquer le style aux départements
        myRenderer = self.depts_NA.renderer()
        if self.depts_NA.geometryType() == QgsWkbTypes.PolygonGeometry:
            mySymbol1 = QgsSymbol.defaultSymbol(self.depts_NA.geometryType())
            mySymbol1.setColor(QColor(255, 255, 255, 0))  # Transparent
            mySymbol1.symbolLayer(0).setStrokeColor(QColor(0, 0, 0))  # Contour noir
            mySymbol1.symbolLayer(0).setStrokeWidth(0.1)  # Épaisseur fine
            myRenderer.setSymbol(mySymbol1)
        
        self.depts_NA.triggerRepaint()
        
        # Sélectionner le département actif
        departement = self.dlg.mComboBox_4.currentText()[0:2]
        self.depts_NA.selectByExpression(f'"insee_dep"= \'{departement}\'', QgsVectorLayer.SetSelection)
        
        # Réinitialiser les sélections précédentes
        self.sites_gere_centroid_layer.removeSelection()
        layer.removeSelection()
        
        # Sélectionner les sites cochés dans la combobox
        for sites in self.dlg.mComboBox.checkedItems():
            self.sites_gere_centroid_layer.selectByExpression(
                f'"nom_site"= \'{sites.replace("\'", "\'\'")}\''
                , QgsVectorLayer.AddToSelection
            )
        
        # Zoomer sur les sites sélectionnés
        from qgis.utils import iface
        iface.mapCanvas().zoomToSelected(self.sites_gere_centroid_layer)
        
        # Appliquer un style pour mettre en évidence les sites sélectionnés
        rules = (
            ('Site CEN sélectionné', "is_selected()", 'red'),
        )
        
        # Créer un nouveau renderer basé sur des règles
        symbol = QgsSymbol.defaultSymbol(self.sites_gere_centroid_layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)
        
        # Récupérer la règle "racine"
        root_rule = renderer.rootRule()
        
        for label, expression, color_name in rules:
            # Créer un clone (une copie) de la règle par défaut
            rule = root_rule.children()[0].clone()
            # Définir le libellé, l'expression et la couleur
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            symbol_layer = rule.symbol().symbolLayer(0)
            color = symbol_layer.color()
            generator = QgsGeometryGeneratorSymbolLayer.create({})
            generator.setSymbolType(QgsSymbol.Marker)
            generator.setGeometryExpression("centroid($geometry)")
            generator.setColor(QColor('Red'))
            rule.symbol().setColor(QColor(color_name))
            # Ajouter la règle à la liste des règles
            rule.symbol().changeSymbolLayer(0, generator)
            root_rule.appendChild(rule)
        
        # Supprimer la règle par défaut
        root_rule.removeChildAt(0)
        
        # Appliquer le renderer à la couche
        self.sites_gere_centroid_layer.setRenderer(renderer)
        
        # Créer une nouvelle mise en page
        self.manager = QgsProject.instance().layoutManager()
        layout_name = 'Mise en page automatique MapCEN (Carto de localisation générale)'
        
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
        titre = f"Localisation générale ({date_du_jour})"
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
        
        self.layout_carto_generale = QgsProject.instance().layoutManager().layoutByName(layout_name).clone()
        
        self.dlg.graphicsView.setScene(self.layout_carto_generale)
        
        # Mettre en évidence les entités sélectionnées
        self.highlight_features()
    
    def highlight_features(self):
        """
        Met en évidence les entités sélectionnées
        """
        # Appliquer un style simple pour les départements
        single_symbol_renderer = self.depts_NA.renderer()
        symbol = single_symbol_renderer.symbol()
        symbol.setColor(QColor.fromRgb(255, 0, 0, 0))  # Transparent avec contour rouge
        
        # Supprimer la sélection pour rafraîchir l'affichage
        self.depts_NA.removeSelection()
