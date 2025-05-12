# -*- coding: utf-8 -*-
"""
Module de cartographie MFU (Mise en Forme Unifiée) pour le plugin MapCEN
"""
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsVectorLayer,
    QgsDataSourceUri, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsRasterLayer, QgsRectangle, QgsSymbol, QgsSimpleFillSymbolLayer,
    QgsWkbTypes, QgsLegendStyle, QgsLayoutItemPage
)
from qgis.utils import iface
import os
from datetime import date

from .base_module import BaseModule


class CartoMFUModule(BaseModule):
    """
    Module pour la cartographie MFU (Mise en Forme Unifiée)
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du module
        """
        super(CartoMFUModule, self).__init__(parent)
        self.layout = None
        self.my_map1 = None
        self.echelle = None
        self.scalebar = None
        self.template_parameters = {}
    
    def init(self):
        """
        Initialise le module (connexions des signaux, etc.)
        """
        # Connecter les signaux des boutons radio pour le format de page
        self.dlg.radioButton_6.toggled.connect(self.update_page_settings)
        self.dlg.radioButton_7.toggled.connect(self.update_page_settings)
        self.dlg.radioButton_8.toggled.connect(self.update_page_settings)
        
        # Connecter le slider de zoom
        self.dlg.horizontalSlider.valueChanged.connect(self.niveau_zoom)
        
        # Connecter le bouton d'export
        self.dlg.pushButton_2.clicked.connect(self.export_layout)
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module
        """
        # Supprimer la mise en page si elle existe
        if self.layout:
            manager = QgsProject.instance().layoutManager()
            layout_name = 'Mise en page automatique MapCEN (MFU)'
            if manager.layoutByName(layout_name):
                manager.removeLayout(manager.layoutByName(layout_name))
    
    def update_page_settings(self):
        """
        Met à jour les paramètres de la page en fonction des boutons radio sélectionnés
        """
        if not self.layout:
            return
        
        # Définir les paramètres de mise en page pour différentes tailles et orientations
        page_settings = {
            ('A4', 'Portrait'): {
                'map_size': (195, 222), 'map_position': (5, 23.5),
                'title_size': (195, 8), 'title_position': (5, 2),
                'subtitle_size': (195, 8), 'subtitle_position': (5, 10),
                'logo_size': (46, 16), 'logo_position': (5, 4),
                'legend_size': (195, 70), 'legend_position': (5, 249),
                'scalebar_size': (55, 15), 'scalebar_position': (110, 270),
                'north_size': (8.4, 12.5), 'north_position': (189, 270),
                'credit_text_size': (100, 3.9), 'credit_text_position': (200, 123),
                'credit_text2_size': (100, 3.9), 'credit_text2_position': (100, 247)
            },
            ('A4', 'Landscape'): {
                'map_size': (287, 150), 'map_position': (5, 30),
                'title_size': (287, 8), 'title_position': (5, 6),
                'subtitle_size': (287, 8), 'subtitle_position': (5, 14),
                'logo_size': (46, 16), 'logo_position': (5.5, 3.5),
                'legend_size': (287, 70), 'legend_position': (5, 185),
                'scalebar_size': (55, 15), 'scalebar_position': (206, 185),
                'north_size': (8.4, 12.5), 'north_position': (273, 184),
                'credit_text_size': (100, 3.9), 'credit_text_position': (158.413, 148),
                'credit_text2_size': (100, 3.9), 'credit_text2_position': (158.413, 154)
            },
            ('A3', 'Portrait'): {
                'map_size': (287, 350), 'map_position': (5, 23.5),
                'title_size': (287, 8), 'title_position': (5, 2),
                'subtitle_size': (287, 8), 'subtitle_position': (5, 10),
                'logo_size': (46, 16), 'logo_position': (5, 4),
                'legend_size': (287, 70), 'legend_position': (5, 377),
                'scalebar_size': (55, 15), 'scalebar_position': (200, 297),
                'north_size': (8.4, 12.5), 'north_position': (273, 297),
                'credit_text_size': (100, 3.9), 'credit_text_position': (291.5, 123),
                'credit_text2_size': (100, 3.9), 'credit_text2_position': (189, 284)
            },
            ('A3', 'Landscape'): {
                'map_size': (408.5, 222), 'map_position': (5, 23.5),
                'title_size': (409, 8), 'title_position': (5, 2),
                'subtitle_size': (409, 8), 'subtitle_position': (5, 10),
                'logo_size': (46, 16), 'logo_position': (5, 4),
                'legend_size': (405, 203), 'legend_position': (5, 249),
                'scalebar_size': (55, 15), 'scalebar_position': (323, 270),
                'north_size': (8.4, 12.5), 'north_position': (402, 270),
                'credit_text_size': (100, 3.9), 'credit_text_position': (415, 123),
                'credit_text2_size': (100, 3.9), 'credit_text2_position': (313, 247)
            }
        }

        # Détermine la taille et l'orientation de la page sélectionnée
        page_size = 'A4' if self.dlg.radioButton_6.isChecked() else 'A3'
        orientation = 'Portrait' if self.dlg.radioButton_7.isChecked() else 'Landscape'
        
        # Applique les paramètres du dictionnaire
        pc = self.layout.pageCollection()
        pc.pages()[0].setPageSize(page_size, getattr(QgsLayoutItemPage, orientation))

        settings = page_settings[(page_size, orientation)]
        for param, (width, height) in settings.items():
            if 'size' in param:
                self.template_parameters[param] = QgsLayoutSize(width, height, QgsUnitTypes.LayoutMillimeters)
            else:
                self.template_parameters[param] = QgsLayoutPoint(width, height, QgsUnitTypes.LayoutMillimeters)
        
        # Rafraîchir la mise en page
        if self.my_map1:
            self.my_map1.refresh()
        if self.layout:
            self.layout.refresh()
    
    def niveau_zoom(self):
        """
        Ajuste l'échelle de la carte en fonction de la valeur du slider
        """
        if not self.my_map1 or not hasattr(self, 'echelle'):
            return
            
        if self.dlg.horizontalSlider.value() == 2:
            self.my_map1.setScale(self.echelle/1.8)
        elif self.dlg.horizontalSlider.value() == 1:
            self.my_map1.setScale(self.echelle/1.4)
        elif self.dlg.horizontalSlider.value() == 0:
            self.my_map1.setScale(self.echelle)
        elif self.dlg.horizontalSlider.value() == -1:
            self.my_map1.setScale(self.echelle*1.4)
        else:
            self.my_map1.setScale(self.echelle*1.8)

        self.my_map1.refresh()

        # Rafraîchir la mise en page
        if self.layout:
            self.layout.refresh()

        # Ajuster l'échelle automatiquement
        self.bar_echelle_auto(self.my_map1, self.scalebar)
    
    def bar_echelle_auto(self, echelle, bar_echelle):
        """
        Ajuste automatiquement l'échelle en fonction de l'échelle de la carte
        
        Args:
            echelle: L'échelle de la carte
            bar_echelle: La barre d'échelle à ajuster
        """
        if not bar_echelle:
            return
            
        if echelle.scale() >= 45000:
            bar_echelle.setUnits(QgsUnitTypes.DistanceKilometers)
            bar_echelle.setUnitLabel("km")
            bar_echelle.setUnitsPerSegment(1.5)
        elif echelle.scale() >= 30000:
            bar_echelle.setUnits(QgsUnitTypes.DistanceKilometers)
            bar_echelle.setUnitLabel("km")
            bar_echelle.setUnitsPerSegment(1)
        elif echelle.scale() >= 20000:
            bar_echelle.setUnits(QgsUnitTypes.DistanceKilometers)
            bar_echelle.setUnitLabel("km")
            bar_echelle.setUnitsPerSegment(0.5)
        elif echelle.scale() >= 9000:
            bar_echelle.setUnits(QgsUnitTypes.DistanceMeters)
            bar_echelle.setUnitLabel("m")
            bar_echelle.setUnitsPerSegment(250)
        elif echelle.scale() >= 5000:
            bar_echelle.setUnits(QgsUnitTypes.DistanceMeters)
            bar_echelle.setUnitLabel("m")
            bar_echelle.setUnitsPerSegment(100)
        else:
            bar_echelle.setUnits(QgsUnitTypes.DistanceMeters)
            bar_echelle.setUnitLabel("m")
            bar_echelle.setUnitsPerSegment(50)

        bar_echelle.update()
    
    def mise_en_page(self):
        """
        Génère la mise en page MFU
        """
        # Récupérer la couche sélectionnée
        layer = QgsProject.instance().mapLayersByName("Parcelles CEN NA en MFU")[0]
        
        # Créer une nouvelle mise en page
        manager = QgsProject.instance().layoutManager()
        layout_name = 'Mise en page automatique MapCEN (MFU)'
        
        # Supprimer la mise en page si elle existe déjà
        if manager.layoutByName(layout_name):
            manager.removeLayout(manager.layoutByName(layout_name))
        
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
        
        # Initialiser les paramètres de mise en page
        self.update_page_settings()
        
        # Positionner et dimensionner la carte
        self.my_map1.attemptMove(self.template_parameters['map_position'])
        self.my_map1.attemptResize(self.template_parameters['map_size'])
        
        # Enregistrer l'échelle actuelle
        self.echelle = self.my_map1.scale()
        
        # Ajouter un titre à la mise en page
        title = QgsLayoutItemLabel(self.layout)
        self.layout.addLayoutItem(title)
        titre = self.dlg.lineEdit.text() if self.dlg.lineEdit.text() else "Titre par défaut"
        title.setText(titre)
        title.setFont(QFont("Calibri", 16, QFont.Bold))
        title.attemptMove(self.template_parameters['title_position'])
        title.attemptResize(self.template_parameters['title_size'])
        title.setHAlign(Qt.AlignHCenter)
        title.setVAlign(Qt.AlignVCenter)
        
        # Ajouter un sous-titre à la mise en page
        subtitle = QgsLayoutItemLabel(self.layout)
        self.layout.addLayoutItem(subtitle)
        date_du_jour = date.today().strftime("%d/%m/%Y")
        titre = f"Mise en Forme Unifiée ({date_du_jour})"
        subtitle.setText(titre)
        subtitle.setFont(QFont("Calibri", 14))
        subtitle.attemptMove(self.template_parameters['subtitle_position'])
        subtitle.attemptResize(self.template_parameters['subtitle_size'])
        subtitle.setHAlign(Qt.AlignHCenter)
        subtitle.setVAlign(Qt.AlignVCenter)
        
        # Ajouter la légende
        legend = QgsLayoutItemLegend(self.layout)
        legend.setTitle("Légende")
        legend.setLinkedMap(self.my_map1)
        legend.setLegendFilterByMapEnabled(True)
        
        # Configurer le style de la légende
        legend.setStyleFont(QgsLegendStyle.Title, QFont("Calibri", 12, QFont.Bold))
        legend.setStyleFont(QgsLegendStyle.Group, QFont("Calibri", 10, QFont.Bold))
        legend.setStyleFont(QgsLegendStyle.Subgroup, QFont("Calibri", 9, QFont.Bold))
        legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Calibri", 8))
        
        self.layout.addLayoutItem(legend)
        legend.attemptMove(self.template_parameters['legend_position'])
        legend.attemptResize(self.template_parameters['legend_size'])
        
        # Ajouter le logo
        logo = QgsLayoutItemPicture(self.layout)
        logo.setResizeMode(QgsLayoutItemPicture.Zoom)
        logo.setMode(QgsLayoutItemPicture.FormatRaster)
        logo.setPicturePath(os.path.dirname(os.path.dirname(__file__)) + '/logo.jpg')
        
        logo.attemptMove(self.template_parameters['logo_position'])
        logo.attemptResize(self.template_parameters['logo_size'])
        
        self.layout.addLayoutItem(logo)
        
        # Ajouter l'échelle
        self.scalebar = QgsLayoutItemScaleBar(self.layout)
        self.scalebar.setStyle('Single Box')
        self.scalebar.setLinkedMap(self.my_map1)
        
        self.scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
        self.scalebar.setUnitLabel("km")
        self.scalebar.setNumberOfSegments(2)
        self.scalebar.setNumberOfSegmentsLeft(0)
        self.scalebar.setUnitsPerSegment(1)
        
        self.scalebar.attemptMove(self.template_parameters['scalebar_position'])
        self.scalebar.attemptResize(self.template_parameters['scalebar_size'])
        
        self.scalebar.update()
        
        self.layout.addLayoutItem(self.scalebar)
        
        # Ajuster l'échelle automatiquement
        self.bar_echelle_auto(self.my_map1, self.scalebar)
        
        # Ajouter la flèche du Nord
        north = QgsLayoutItemPicture(self.layout)
        north.setPicturePath(os.path.dirname(os.path.dirname(__file__)) + "/NorthArrow_02.svg")
        self.layout.addLayoutItem(north)
        north.attemptResize(self.template_parameters['north_size'])
        north.attemptMove(self.template_parameters['north_position'])
        
        # Ajouter les crédits
        date_du_jour = date.today().strftime("%d/%m/%Y")
        credit_text = QgsLayoutItemLabel(self.layout)
        credit_text.setText(f"Réalisation : CEN Nouvelle-Aquitaine ({date_du_jour})")
        credit_text.setFont(QFont("Arial", 8))
        self.layout.addLayoutItem(credit_text)
        credit_text.attemptMove(self.template_parameters['credit_text_position'])
        credit_text.adjustSizeToText()
        
        credit_text2 = QgsLayoutItemLabel(self.layout)
        credit_text2.setText("Source: Google (fond satellite), IGN (fond SCAN25)")
        credit_text2.setFont(QFont("Arial", 8))
        self.layout.addLayoutItem(credit_text2)
        credit_text2.attemptMove(self.template_parameters['credit_text2_position'])
        credit_text2.adjustSizeToText()
        
        # Rafraîchir le layout
        self.layout.refresh()
        
        # Ajouter la mise en page au projet via son gestionnaire
        manager.addLayout(self.layout)
        
        # Afficher dans la vue
        self.dlg.graphicsView.setScene(self.layout)
    
    def export_layout(self):
        """
        Exporte la mise en page au format PDF ou image
        """
        if not self.layout:
            QMessageBox.warning(self.dlg, "Avertissement", "Veuillez d'abord générer une mise en page.")
            return
        
        # Demander à l'utilisateur où enregistrer le fichier
        file_dialog = QFileDialog()
        file_dialog.setWindowTitle("Enregistrer la mise en page")
        file_dialog.setNameFilter("PDF (*.pdf);;Images (*.png *.jpg *.tif)")
        file_dialog.setDefaultSuffix("pdf")
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        
        if not file_dialog.exec_():
            return
        
        selected_files = file_dialog.selectedFiles()
        if not selected_files:
            return
        
        output_file = selected_files[0]
        
        # Récupérer la résolution depuis le parent (plugin principal)
        resolution = 200  # Valeur par défaut
        if hasattr(self.parent, 'resolution'):
            resolution = self.parent.resolution
        
        # Exporter la mise en page
        exporter = QgsLayoutExporter(self.layout)
        
        if output_file.lower().endswith('.pdf'):
            result = exporter.exportToPdf(output_file, QgsLayoutExporter.PdfExportSettings())
        else:
            result = exporter.exportToImage(output_file, QgsLayoutExporter.ImageExportSettings(resolution=resolution))
        
        if result == QgsLayoutExporter.Success:
            QMessageBox.information(self.dlg, "Succès", f"Mise en page exportée avec succès vers {output_file}")
        else:
            QMessageBox.warning(self.dlg, "Erreur", "Erreur lors de l'exportation de la mise en page.")
