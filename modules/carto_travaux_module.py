# -*- coding: utf-8 -*-
"""
Module de cartographie des travaux pour le plugin MapCEN
"""
from qgis.PyQt.QtCore import Qt, QVariant, QDate
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtWidgets import QCheckBox, QMessageBox
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemPicture, QgsLayoutItemScaleBar,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsVectorLayer,
    QgsDataSourceUri, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsRasterLayer, QgsRectangle, QgsSymbol, QgsSimpleFillSymbolLayer,
    QgsWkbTypes, QgsLegendStyle, QgsLegendRenderer, QgsRuleBasedRenderer,
    QgsGeometryGeneratorSymbolLayer, QgsFeatureRequest, QgsLayoutItemShape,
    QgsFillSymbol
)
from qgis.utils import iface
import os
from datetime import date

from .base_module import BaseModule


class CartoTravauxModule(BaseModule):
    """
    Module pour la cartographie des travaux
    """
    
    def __init__(self, parent=None):
        """
        Initialisation du module
        """
        super(CartoTravauxModule, self).__init__(parent)
        self.layout_carto_travaux = None
        self.checkbox_2 = None
        self.horizontalSlider = None
        self.echelle = None
        self.my_map1 = None
        self.aires_intervention = None
        self.sites_gere_centroid_layer = None
    
    def init(self):
        """
        Initialise le module (connexions des signaux, etc.)
        """
        # Créer la checkbox si elle n'existe pas encore
        if self.checkbox_2 is None:
            self.checkbox_2 = QCheckBox(self.dlg)
            self.checkbox_2.setText("Générer une carto générale d'un marché")
            self.checkbox_2.setGeometry(72, 442, 300, 20)
            # Définir la taille de la police à 7
            font = self.checkbox_2.font()
            font.setPointSize(7)
            self.checkbox_2.setFont(font)
            # Connecter le changement d'état de la checkbox à la fonction de gestion
            self.checkbox_2.stateChanged.connect(self.on_checkbox_2_changed)
        
        # Ajouter le slider de zoom s'il n'existe pas encore
        if self.horizontalSlider is None and hasattr(self.dlg, 'horizontalSlider'):
            self.horizontalSlider = self.dlg.horizontalSlider
            # Connecter le changement de valeur du slider à la fonction de gestion
            self.horizontalSlider.valueChanged.connect(self.niveau_zoom)
        
        # Connecter les signaux des combobox
        self.dlg.comboBox_3.currentTextChanged.connect(self.on_combobox_changed)
        self.dlg.mComboBox_3.currentTextChanged.connect(self.on_mComboBox_3_changed)
        self.dlg.mComboBox_4.checkedItemsChanged.connect(self.on_mComboBox_4_changed)
        
        # Afficher la checkbox uniquement lorsque "Travaux" est sélectionné dans comboBox_3
        if self.dlg.comboBox_3.currentText() == "Travaux":
            self.checkbox_2.show()
        else:
            self.checkbox_2.hide()
    
    def cleanup(self):
        """
        Nettoie les ressources utilisées par le module
        """
        # Nettoyer les couches temporaires
        self.nettoyer_couches_temporaires()
        
        # Déconnecter les signaux
        if self.checkbox_2 is not None:
            self.checkbox_2.stateChanged.disconnect(self.on_checkbox_2_changed)
        
        if self.horizontalSlider is not None:
            self.horizontalSlider.valueChanged.disconnect(self.niveau_zoom)
        
        self.dlg.comboBox_3.currentTextChanged.disconnect(self.on_combobox_changed)
        self.dlg.mComboBox_3.currentTextChanged.disconnect(self.on_mComboBox_3_changed)
        self.dlg.mComboBox_4.checkedItemsChanged.disconnect(self.on_mComboBox_4_changed)
    
    def selection_couche_travaux(self):
        """
        Sélectionne et charge les couches nécessaires pour la cartographie des travaux
        """
        # Charger les couches WFS
        uri2 = QgsDataSourceUri()
        uri2.setParam("url", "https://opendata.cen-nouvelle-aquitaine.org/geoserver/fonciercen/wfs")
        uri2.setParam("typename", "fonciercen:aig_cenna")
        
        # Appliquer l'authentification si nécessaire
        from qgis.utils import plugins
        map_cen_instance = plugins['map_cen']
        if not map_cen_instance.apply_authentication_if_needed(uri2):
            return  # Sortir si l'authentification échoue

        # Charger la couche protégée
        self.aires_intervention = QgsVectorLayer(uri2.uri(), "Aires d'intervention globale CEN NA", "WFS")
        if not self.aires_intervention.isValid():
            QMessageBox.warning(self.dlg, "Erreur de chargement", "Impossible de charger la couche 'Aires d'intervention globale CEN NA'.")
            return
        else:
            QgsProject.instance().addMapLayer(self.aires_intervention)

        # Charger les autres couches nécessaires
        uri3 = QgsDataSourceUri()
        uri3.setParam("url", "https://opendata.cen-nouvelle-aquitaine.org/geoserver/fonciercen/wfs")
        uri3.setParam("typename", "fonciercen:travaux_79")
        
        if not map_cen_instance.apply_authentication_if_needed(uri3):
            return  # Sortir si l'authentification échoue
        
        travaux_layer = QgsVectorLayer(uri3.uri(), "Travaux_79", "WFS")
        if not travaux_layer.isValid():
            QMessageBox.warning(self.dlg, "Erreur de chargement", "Impossible de charger la couche 'Travaux_79'.")
            return
        else:
            QgsProject.instance().addMapLayer(travaux_layer)
        
        # Récupérer les codes de projet uniques
        list_code_proj = set()  # Utiliser un set pour garantir l'unicité
        for feature in travaux_layer.getFeatures():
            code_proj = feature['code_proj']
            if code_proj:
                list_code_proj.add(code_proj)
        
        # Ajouter les codes de projet à la combobox
        self.dlg.mComboBox_3.clear()
        self.dlg.mComboBox_3.addItems(sorted(list_code_proj))
    
    def get_dept_extent(self):
        """
        Applique le style, filtre la couche des départements selon la sélection,
        calcule et retourne l'étendue des départements sélectionnés (transformée en EPSG:2154 si besoin).
        Retourne None si aucun département n'est sélectionné (et affiche un message).
        """
        # Récupérer la couche des départements
        depts_layer = QgsProject.instance().mapLayersByName("Département")[0]
        
        # Appliquer le style aux départements
        myRenderer = depts_layer.renderer()
        if depts_layer.geometryType() == QgsWkbTypes.PolygonGeometry:
            mySymbol1 = QgsSymbol.defaultSymbol(depts_layer.geometryType())
            fill_layer = QgsSimpleFillSymbolLayer.create(
                {'color': '255,255,255,0', 'outline_color': '0,0,0,255', 'outline_width': '0.1'}
            )
            mySymbol1.changeSymbolLayer(0, fill_layer)
            myRenderer.setSymbol(mySymbol1)
        
        depts_layer.triggerRepaint()
        
        # Récupérer les départements sélectionnés
        selected_depts = []
        for dept in self.dlg.mComboBox_4.checkedItems():
            selected_depts.append(dept[0:2])
        
        if not selected_depts:
            QMessageBox.warning(self.dlg, "Avertissement", "Veuillez sélectionner au moins un département.")
            return None
        
        # Construire l'expression de filtre
        filter_expr = ' OR '.join([f"\"insee_dep\" = '{dept}'" for dept in selected_depts])
        
        # Sélectionner les départements
        depts_layer.selectByExpression(filter_expr, QgsVectorLayer.SetSelection)
        
        # Obtenir l'étendue des entités sélectionnées
        extent = depts_layer.boundingBoxOfSelected()
        
        # Transformer l'étendue en EPSG:2154 si nécessaire
        if depts_layer.crs().authid() != 'EPSG:2154':
            source_crs = depts_layer.crs()
            dest_crs = QgsCoordinateReferenceSystem('EPSG:2154')
            transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
            extent = transform.transformBoundingBox(extent)
        
        return extent
    
    def filtrer_et_zoomer_sur_marche(self, nom_marche):
        """
        Filtre la couche travaux_layer en fonction du marché sélectionné
        et zoome sur l'étendue des entités filtrées.
        En parallèle, filtre également la couche sites_gere_centroid_layer
        pour ne conserver que les centroïdes correspondant aux 'site_gere' sélectionnés.
        
        Args:
            nom_marche (str): Nom du marché à filtrer
        """
        # Récupérer la couche des travaux
        travaux_layer = QgsProject.instance().mapLayersByName("Travaux_79")[0]
        
        # Appliquer le filtre sur la couche des travaux
        travaux_layer.setSubsetString(f"code_proj = '{nom_marche}'")
        
        # Récupérer les noms des sites concernés par ce marché
        site_names = set()
        for feature in travaux_layer.getFeatures():
            site_name = feature['site_gere']
            if site_name:
                site_names.add(site_name)
        
        # Récupérer la couche des centroïdes des sites
        sites_centroid_layer = QgsProject.instance().mapLayersByName("Sites gérés CEN-NA")[0]
        
        # Construire l'expression de filtre pour les sites
        if site_names:
            sites_filter_expr = ' OR '.join([
                f'"nom_site" = \'{site.replace("\'", "''")}\''
                for site in site_names
            ])
            sites_centroid_layer.selectByExpression(sites_filter_expr, QgsVectorLayer.SetSelection)
            
            # Zoomer sur l'étendue des entités sélectionnées
            iface.mapCanvas().zoomToSelected(sites_centroid_layer)
        else:
            # Si aucun site n'est trouvé, afficher un message
            QMessageBox.warning(self.dlg, "Information", "Aucun site associé à ce marché n'a été trouvé.")
    
    def on_checkbox_2_changed(self, state):
        """
        Gère le changement d'état de la checkbox "Générer une carto générale d'un marché"
        
        Args:
            state: État de la checkbox (Qt.Checked ou Qt.Unchecked)
        """
        # Afficher ou masquer la combobox mComboBox_3 en fonction de l'état de la checkbox
        if state == Qt.Checked:
            self.dlg.mComboBox_3.show()
            self.dlg.label_15.setText("Sélectionnez un marché :")
            self.dlg.label_15.show()
            
            # Charger les données des travaux si ce n'est pas déjà fait
            if not QgsProject.instance().mapLayersByName("Travaux_79"):
                self.selection_couche_travaux()
            
            # Récupérer la couche des travaux
            travaux_layers = QgsProject.instance().mapLayersByName("Travaux_79")
            if not travaux_layers:
                QMessageBox.warning(self.dlg, "Erreur", "La couche 'Travaux_79' n'est pas disponible.")
                return
            
            travaux_layer = travaux_layers[0]
            
            # Récupérer les codes de projet uniques
            list_code_proj = set()
            for feature in travaux_layer.getFeatures():
                code_proj = feature['code_proj']
                if code_proj:
                    list_code_proj.add(code_proj)
            
            # Mettre à jour la combobox avec les codes de projet
            self.dlg.mComboBox_3.clear()
            self.dlg.mComboBox_3.addItems(sorted(list_code_proj))
        else:
            self.dlg.mComboBox_3.hide()
            self.dlg.label_15.hide()
            
            # Réinitialiser les filtres sur les couches
            travaux_layers = QgsProject.instance().mapLayersByName("Travaux_79")
            if travaux_layers:
                travaux_layers[0].setSubsetString("")
    
    def on_combobox_changed(self, text):
        """
        Gère le changement de texte dans comboBox_3
        
        Args:
            text: Texte sélectionné
        """
        # Afficher la checkbox uniquement lorsque "Travaux" est sélectionné
        if text == "Travaux":
            self.checkbox_2.show()
        else:
            self.checkbox_2.hide()
    
    def on_mComboBox_3_changed(self, text):
        """
        Gère le changement de texte dans mComboBox_3
        
        Args:
            text: Texte sélectionné
        """
        if text and self.checkbox_2.isChecked():
            self.filtrer_et_zoomer_sur_marche(text)
    
    def on_mComboBox_4_changed(self):
        """
        Appelé lorsque les éléments cochés de mComboBox_4 changent
        """
        # Mettre à jour l'interface en fonction des départements sélectionnés
        pass
    
    def choix_mise_en_page(self):
        """
        Si la checkbox "Générer une carto générale d'un marché" est cochée, lance la mise en page marché
        Sinon, lance la mise en page standard
        """
        if self.checkbox_2.isChecked():
            # Vérifier qu'un marché est sélectionné
            if self.dlg.mComboBox_3.currentText():
                self.mise_en_page_marche()
            else:
                QMessageBox.warning(self.dlg, "Avertissement", "Veuillez sélectionner un marché.")
        else:
            self.mise_en_page()
    
    def charger_fond_carte_secondaire(self):
        """
        Charge le fond de carte SCAN25 et retourne une référence fraîche
        """
        # Charger le fond de carte SCAN25
        scan25_layer = QgsRasterLayer(
            "contextualWMSLegend=0&crs=EPSG:3857&dpiMode=7&featureCount=10&format=image/png&layers=SCAN25TOUR_PYR-JPEG_WLD_WM&styles=&url=https://wxs.ign.fr/essentiels/geoportail/r/wms",
            "Fond SCAN25",
            "wms"
        )
        
        if not scan25_layer.isValid():
            QMessageBox.warning(self.dlg, "Erreur", "Impossible de charger le fond de carte SCAN25.")
            return None
        
        QgsProject.instance().addMapLayer(scan25_layer)
        return scan25_layer
    
    def mise_en_page(self):
        """
        Génère la mise en page standard pour les travaux
        """
        # Implémentation de la mise en page standard
        # (Code adapté de la fonction mise_en_page originale)
        pass
    
    def appliquer_style_centroide(self, layer, couleur='red', taille=3, etiquette_champ=None, filter_expression="TRUE"):
        """
        Applique un style de centroïde à une couche vectorielle
        
        Args:
            layer (QgsVectorLayer): La couche à laquelle appliquer le style
            couleur (str): Couleur du centroïde (nom de couleur ou code hex)
            taille (int): Taille du centroïde
            etiquette_champ (str, optional): Champ à utiliser pour l'étiquetage
            filter_expression (str, optional): Expression de filtre pour les règles
        """
        # Implémentation du style de centroïde
        # (Code adapté de la fonction appliquer_style_centroide originale)
        pass
    
    def mise_en_page_marche(self):
        """
        Génère une mise en page spécifique pour un marché
        Cette fonction est appelée uniquement lors du clic sur le bouton commandLinkButton_4
        et si la checkbox "Générer une carto générale d'un marché" est cochée
        """
        # Implémentation de la mise en page pour un marché
        # (Code adapté de la fonction mise_en_page_marche originale)
        pass
    
    def nettoyer_couches_temporaires(self):
        """
        Supprime toutes les couches clonées temporaires (par exemple, les versions sans étiquettes)
        basées sur un nom ou une propriété spécifique.
        """
        layers_to_remove = []

        for layer in QgsProject.instance().mapLayers().values():
            if layer.name().startswith("Sites gérés sans étiquettes"):
                layers_to_remove.append(layer)

        for layer in layers_to_remove:
            QgsProject.instance().removeMapLayer(layer)
            print(f"✔ Couche temporaire supprimée : {layer.name()}")
    
    def niveau_zoom(self):
        """
        Ajuste l'échelle de la carte en fonction de la valeur du slider
        """
        # Vérifier que my_map1 et horizontalSlider existent
        if not self.my_map1 or not self.horizontalSlider:
            return
            
        # Ajuster l'échelle en fonction de la valeur du slider
        slider_value = self.horizontalSlider.value()
        
        if slider_value == 2:
            self.my_map1.setScale(self.echelle/1.8)
        elif slider_value == 1:
            self.my_map1.setScale(self.echelle/1.4)
        elif slider_value == 0:
            self.my_map1.setScale(self.echelle)
        elif slider_value == -1:
            self.my_map1.setScale(self.echelle*1.4)
        else:  # -2
            self.my_map1.setScale(self.echelle*1.8)

        # Rafraîchir la carte
        self.my_map1.refresh()
        
        # Rafraîchir la mise en page si elle existe
        if self.layout_carto_travaux:
            self.layout_carto_travaux.refresh()
