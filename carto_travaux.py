import urllib
import csv
import io

from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from PyQt5 import *
from PyQt5.QtCore import Qt
from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsDataSourceUri,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsRasterLayer,
    QgsRectangle,
    QgsSymbol,
    QgsSimpleFillSymbolLayer,
    QgsWkbTypes,
    QgsLegendStyle,
    QgsLegendRenderer,
    QgsRuleBasedRenderer,
    QgsGeometryGeneratorSymbolLayer,
    QgsFeatureRequest,
    QgsLayoutItemShape,
    QgsFillSymbol
)
from qgis.PyQt.QtCore import QVariant, QDate
from qgis.PyQt.QtGui import QFont
import os
from qgis.gui import *
from qgis.utils import *
from qgis.PyQt.QtXml import QDomDocument
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .map_cen_dialog import MapCENDialog
import os.path


from datetime import date

class module_travaux():

    def __init__(self):
        self.dlg = None
        self.layout_carto_travaux = None
        self.checkbox_2 = None


    def initialisation(self):

        # Create checkbox_2 if it doesn't exist yet
        if self.checkbox_2 is None:
            self.checkbox_2 = QCheckBox(self.dlg)
            self.checkbox_2.setText("Générer une carto générale d'un marché")
            self.checkbox_2.setGeometry(72, 442, 300, 20)
            # Set font size to 7
            font = self.checkbox_2.font()
            font.setPointSize(7)
            self.checkbox_2.setFont(font)
            # Connect checkbox state change to handler function
            self.checkbox_2.stateChanged.connect(self.on_checkbox_2_changed)
        
        # Connect comboBox_3 text changed signal to handler function
        self.dlg.comboBox_3.currentTextChanged.connect(self.on_combobox_changed)
        
        # Connect mComboBox_3 text changed signal to handler function
        self.dlg.mComboBox_3.currentTextChanged.connect(self.on_mComboBox_3_changed)
        
        # Connect mComboBox_4 changed signal to handler function
        self.dlg.mComboBox_4.checkedItemsChanged.connect(self.on_mComboBox_4_changed)
        
        # Show checkbox only when "Travaux" is selected in comboBox_3
        if self.dlg.comboBox_3.currentText() == "Travaux":
            self.checkbox_2.show()
        else:
            self.checkbox_2.hide()
            

        uri2 = QgsDataSourceUri()
        uri2.setParam("url", "https://opendata.cen-nouvelle-aquitaine.org/geoserver/fonciercen/wfs")
        uri2.setParam("typename", "fonciercen:site_gere_poly")
        from qgis.utils import plugins
        map_cen_instance = plugins['map_cen']
        if not map_cen_instance.apply_authentication_if_needed(uri2):
            return  # Exit if authentication fails

        # Step 4: Load the protected layer
        self.sites_gere_poly_layer = QgsVectorLayer(uri2.uri(), "Sites gérés CEN-NA (polygone)", "WFS")
        if not self.sites_gere_poly_layer.isValid():
            QMessageBox.warning(self.dlg, "Erreur de chargement", "Impossible de charger la couche 'Sites gérés CEN-NA (polygone)'.")
            return
        else:
            QgsProject.instance().addMapLayer(self.sites_gere_poly_layer)


        uri3 = QgsDataSourceUri()
        uri3.setParam("url", "https://opendata.cen-nouvelle-aquitaine.org/geoserver/fonciercen/wfs")
        uri3.setParam("typename", "fonciercen:site_gere_point")
        from qgis.utils import plugins
        map_cen_instance = plugins['map_cen']
        if not map_cen_instance.apply_authentication_if_needed(uri3):
            return  # Exit if authentication fails

        # Step 4: Load the protected layer
        self.sites_gere_centroid_layer = QgsVectorLayer(uri3.uri(), "Sites gérés CEN-NA", "WFS")
        if not self.sites_gere_centroid_layer.isValid():
            QMessageBox.warning(self.dlg, "Erreur de chargement", "Impossible de charger la couche 'Sites gérés CEN-NA'.")
            return
        else:
            QgsProject.instance().addMapLayer(self.sites_gere_centroid_layer)

        
        # Chargement ou récupération de la couche 'Département'
        depts_existe = QgsProject.instance().mapLayersByName("Département")

        if depts_existe:
            self.depts_NA = depts_existe[0]
            iface.messageBar().pushMessage("Couche 'Département'", "La couche 'Département' est déjà chargée dans le canevas QGIS.", level=Qgis.Success, duration=5)
        else:
            self.depts_NA = iface.addVectorLayer(
                "https://opendata.cen-nouvelle-aquitaine.org/administratif/wfs?VERSION=1.0.0&TYPENAME=administratif:departement&SRSNAME=EPSG:4326&request=GetFeature",
                "Département", "WFS")
            if not self.depts_NA or not self.depts_NA.isValid():
                QMessageBox.critical(iface.mainWindow(), "Erreur de chargement", "Impossible de charger la couche 'Département'. Veuillez contacter le pôle DSI !", QMessageBox.Ok)
                return

        
    def selection_couche_travaux(self):      
        
        # Récupérer les départements sélectionnés dans mComboBox_4
        departements_selection = []
        for item in self.dlg.mComboBox_4.checkedItems():
            # Prendre les deux premiers chiffres pour obtenir le numéro du département
            dept_num = item[:2]
            departements_selection.append(dept_num)
        
        # Si aucun département n'est sélectionné, on ne fait rien
        if not departements_selection:
            QMessageBox.warning(self.dlg, "Attention", 
                              "Veuillez sélectionner au moins un département dans la liste déroulante !")
            return
        
        # Si plusieurs départements sont sélectionnés, on prend le premier
        dept_num = departements_selection[0]
        
        # Supprimer l'ancienne couche de travaux si elle existe
        if hasattr(self, 'travaux_layer') and self.travaux_layer:
            QgsProject.instance().removeMapLayer(self.travaux_layer)
        
        uri = QgsDataSourceUri()
        # Configuration de la connexion PostGIS
        uri.setConnection("51.210.28.153", "5432", "collab_travaux", "r.montillet", "PMnMwaNWS8Sho4S6uYhhWVJLK")
        # Définition de la table et des champs à utiliser en fonction du département sélectionné
        table_name = f"Travaux_{dept_num}"
        uri.setDataSource("travaux_79", table_name, "geom", "", "id")

        # Charger la couche PostGIS
        self.travaux_layer = QgsVectorLayer(uri.uri(), table_name, "postgres")
        if not self.travaux_layer.isValid():
            QMessageBox.warning(self.dlg, "Erreur de chargement", f"Impossible de charger la couche '{table_name}' depuis PostGIS.")
            return
        else:
            QgsProject.instance().addMapLayer(self.travaux_layer)

        # Récupérer la liste des noms de marché
        list_nom_marche = set()
        try:
            for code_proj in self.travaux_layer.getFeatures():
                code_proj_index = code_proj.fields().indexFromName('nom_marche')    
                if code_proj_index >= 0:  # Vérifier que le champ existe
                    value = code_proj[code_proj_index]
                    if value:  # Vérifier que la valeur n'est pas nulle
                        list_nom_marche.add(str(value))
        except Exception as e:
            QMessageBox.warning(self.dlg, "Erreur", f"Erreur lors de la récupération des noms de marché: {str(e)}")
            return

        list_nom_marche = list(list_nom_marche)

        # Préparer la comboBox
        self.dlg.mComboBox_3.clear()
        self.dlg.mComboBox_3.setDefaultText("Sélectionnez un code projet")
        self.dlg.mComboBox_3.setCurrentIndex(-1)
        self.dlg.mComboBox_3.addItems(list_nom_marche)
        
        # Si la checkbox_2 est cochée, on montre la comboBox_3
        if self.checkbox_2 and self.checkbox_2.isChecked():
            self.dlg.mComboBox_3.show()
        else:
            self.dlg.mComboBox_3.hide()


    def get_dept_extent(self):
        """
        Applique le style, filtre la couche des départements selon la sélection,
        calcule et retourne l'étendue des départements sélectionnés (transformée en EPSG:2154 si besoin).
        Retourne None si aucun département n'est sélectionné (et affiche un message).
        """
        myRenderer = self.depts_NA.renderer()

        if self.depts_NA.geometryType() == QgsWkbTypes.PolygonGeometry:
            mySymbol1 = QgsSymbol.defaultSymbol(self.depts_NA.geometryType())
            fill_layer = QgsSimpleFillSymbolLayer.create({
                'color': '255,255,255,0',         # fond transparent (alpha = 0)
                'outline_color': '184,18,120,255',  # contours blancs
                'outline_width': '1'
            })
            mySymbol1.changeSymbolLayer(0, fill_layer)
            myRenderer.setSymbol(mySymbol1)

        self.depts_NA.triggerRepaint()

        # Récupérer les départements sélectionnés dans mComboBox_4
        departements_selection = []
        for item in self.dlg.mComboBox_4.checkedItems():
            # Prendre les deux premiers chiffres pour obtenir le numéro du département
            dept_num = item[:2]
            departements_selection.append(dept_num)
        
        # Créer une expression de filtre pour les départements sélectionnés
        if departements_selection:
            # Filtrer la couche des départements pour n'afficher que ceux sélectionnés
            if len(departements_selection) == 1:
                # Si un seul département est sélectionné
                dept_expression = f"insee_dep = {departements_selection[0]}"
            else:
                # Si plusieurs départements sont sélectionnés
                dept_list = ", ".join(departements_selection)
                dept_expression = f"insee_dep IN ({dept_list})"
                        
            # Appliquer le filtre
            self.depts_NA.setSubsetString(dept_expression)
            
            # Forcer le rafraîchissement de la couche pour que le filtre soit appliqué immédiatement
            self.depts_NA.triggerRepaint()

            # Attendre un court instant pour s'assurer que le filtre est appliqué
            QApplication.processEvents()
            
            # Calculer manuellement l'étendue en parcourant les entités filtrées
            manual_extent = None
            request = QgsFeatureRequest()
            for feature in self.depts_NA.getFeatures(request):
                if manual_extent is None:
                    manual_extent = QgsRectangle(feature.geometry().boundingBox())
                else:
                    manual_extent.combineExtentWith(feature.geometry().boundingBox())
            
            # Utiliser cette étendue calculée manuellement si elle existe
            if manual_extent and not manual_extent.isNull():
                dept_extent = manual_extent
            else:
                # Sinon, utiliser l'étendue de la couche (fallback)
                dept_extent = self.depts_NA.extent()
            
            # Transformer l'étendue si nécessaire
            if self.depts_NA.crs().authid() != "EPSG:2154":
                crsSrc = self.depts_NA.crs()  # Utilisez le CRS réel de la couche
                crsDest = QgsCoordinateReferenceSystem("EPSG:2154")
                transformContext = QgsProject.instance().transformContext()
                xform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)
                dept_extent = xform.transform(dept_extent)
            return dept_extent
        else:
            QMessageBox.information(iface.mainWindow(), "Attention", 
                                "Veuillez sélectionner un département dans la liste déroulante !", QMessageBox.Ok)
            return None



    def filtrer_et_zoomer_sur_marche(self, nom_marche):
        """
        Filtre la couche travaux_layer en fonction du marché sélectionné
        et zoome sur l'étendue des entités filtrées.
        En parallèle, filtre également la couche sites_gere_centroid_layer
        pour ne conserver que les centroïdes correspondant aux 'site_gere' sélectionnés.
        
        Args:
            nom_marche (str): Nom du marché à filtrer
        """

        self.travaux_layer.removeSelection()
        self.sites_gere_centroid_layer.removeSelection()

        if not nom_marche:
            return

        # === Étape 1 : Filtrer la couche Travaux_79 ===
        filter_expression = f""" "nom_marche" = '{nom_marche.replace("'", "''")}' """
        self.travaux_layer.setSubsetString(filter_expression)

        # Rafraîchir la carte
        from qgis.utils import iface
        iface.mapCanvas().refresh()

        # === Étape 2 : Calculer l'étendue combinée ===
        combined_extent = None
        site_geres = set()

        for feature in self.travaux_layer.getFeatures():
            geom = feature.geometry()
            if geom and not geom.isEmpty():
                if combined_extent is None:
                    combined_extent = geom.boundingBox()
                else:
                    combined_extent.combineExtentWith(geom.boundingBox())
            
            # Collecter les noms de sites pour filtrer la couche de centroïdes
            val = feature['site_gere']
            if val:
                site_geres.add(val)

        # === Étape 3 : Zoom sur les entités filtrées ===
        if combined_extent and not combined_extent.isNull():
            combined_extent.scale(1.2)  # marge de 20%
            iface.mapCanvas().setExtent(combined_extent)
            iface.mapCanvas().refresh()

        # === Étape 4 : Filtrer la couche des centroïdes ===
        if site_geres:
            valeurs_filtrees = []
            for v in site_geres:
                v_safe = v.replace("'", "''")  
                valeurs_filtrees.append(f"'{v_safe}'")
            expression_filtre_centroid = f'"nom_site" IN ({", ".join(valeurs_filtrees)})'

            self.sites_gere_centroid_layer.setSubsetString(expression_filtre_centroid)

    
    def on_checkbox_2_changed(self, state):
        # If checkbox is checked, show mComboBox_3 and position it below checkbox_2
        if state == Qt.Checked:
            # Vérifier si les couches nécessaires sont présentes
            couches_manquantes = []
            
            # Vérifier si travaux_layer est valide
            if not hasattr(self, 'travaux_layer') or not self.travaux_layer.isValid():
                couches_manquantes.append("Travaux_79")
            
            # Vérifier si la couche Département est présente
            if not QgsProject.instance().mapLayersByName("Département"):
                couches_manquantes.append("Département")

            # Si des couches sont manquantes, afficher un message d'erreur et recréer la checkbox
            if couches_manquantes:
                # Afficher le message d'erreur
                QMessageBox.warning(self.dlg, "Couches manquantes", 
                                  f"Impossible de générer la mise en page marché car les couches suivantes sont manquantes : \n{', '.join(couches_manquantes)}")
                
                # Supprimer l'ancienne checkbox
                if self.checkbox_2:
                    self.checkbox_2.deleteLater()
                
                # Recréer une nouvelle checkbox
                self.checkbox_2 = QCheckBox(self.dlg)
                self.checkbox_2.setText("Générer une carto générale d'un marché")
                self.checkbox_2.setGeometry(72, 442, 300, 20)
                # Set font size to 7
                font = self.checkbox_2.font()
                font.setPointSize(7)
                self.checkbox_2.setFont(font)
                # Connect checkbox state change to handler function
                self.checkbox_2.stateChanged.connect(self.on_checkbox_2_changed)
                
                # Afficher la checkbox si nécessaire
                if self.dlg.comboBox_3.currentText() == "Travaux":
                    self.checkbox_2.show()
                else:
                    self.checkbox_2.hide()
                
                return
                
            # Vérifier si au moins un département est sélectionné dans mComboBox_4
            if not self.dlg.mComboBox_4.checkedItems():
                # Afficher le message d'erreur
                QMessageBox.warning(self.dlg, "Département non sélectionné", 
                                  "Veuillez sélectionner au moins un département dans la liste avant de générer une carte de marché.")
                
                # Supprimer l'ancienne checkbox
                if self.checkbox_2:
                    self.checkbox_2.deleteLater()
                
                # Recréer une nouvelle checkbox
                self.checkbox_2 = QCheckBox(self.dlg)
                self.checkbox_2.setText("Générer une carto générale d'un marché")
                self.checkbox_2.setGeometry(72, 442, 300, 20)
                # Set font size to 7
                font = self.checkbox_2.font()
                font.setPointSize(7)
                self.checkbox_2.setFont(font)
                # Connect checkbox state change to handler function
                self.checkbox_2.stateChanged.connect(self.on_checkbox_2_changed)
                
                # Afficher la checkbox si nécessaire
                if self.dlg.comboBox_3.currentText() == "Travaux":
                    self.checkbox_2.show()
                else:
                    self.checkbox_2.hide()
                
                return
            
            # Position mComboBox_3 10 pixels below checkbox_2
            checkbox_x = self.checkbox_2.x()
            checkbox_y = self.checkbox_2.y()
            self.dlg.mComboBox_3.setGeometry(20, 370, 290, 20)
            self.dlg.mComboBox_3.show()
            # Disable the comboBox when checkbox is checked
            self.dlg.mComboBox.setEnabled(False)
            
            # Filtrer et zoomer sur le marché sélectionné
            if self.dlg.mComboBox_3.currentText():
                self.filtrer_et_zoomer_sur_marche(self.dlg.mComboBox_3.currentText())
        else:
            self.dlg.mComboBox_3.hide()
            # Enable the comboBox when checkbox is unchecked (for next time it's shown)
            self.dlg.mComboBox.setEnabled(True)
            
            # Réinitialiser le filtre sur la couche Travaux_79
            self.travaux_layer.setSubsetString("")
                
    def on_combobox_changed(self, text):
        # Show checkbox only when "Travaux" is selected
        if text == "Travaux":
            self.checkbox_2.show()
        else:
            self.checkbox_2.hide()
            self.dlg.mComboBox_3.hide()
            if self.checkbox_2 is not None:
                self.checkbox_2.setChecked(False)
                # Réinitialiser le filtre sur la couche Travaux_79
                self.travaux_layer.setSubsetString("")
                
    def on_mComboBox_3_changed(self, text):
        # Mettre à jour le filtre sur la couche Travaux_79 si la checkbox_2 est cochée
        if self.checkbox_2 is not None and self.checkbox_2.isChecked() and text:
            self.filtrer_et_zoomer_sur_marche(text)
            
    def on_mComboBox_4_changed(self):
        """
        Appelé lorsque les éléments cochés de mComboBox_4 changent
        """
        # Si au moins un élément est sélectionné, on met à jour la couche de travaux
        if self.dlg.mComboBox_4.checkedItems():
            self.selection_couche_travaux()


    def choix_mise_en_page(self):
        """
        Si la checkbox "Générer une carto générale d'un marché" est cochée, lance la mise en page marché
        Sinon, lance la mise en page standard
        """
        if self.checkbox_2 and self.checkbox_2.isChecked():
            # Vérifier si un marché est sélectionné
            if not self.dlg.mComboBox_3.currentText():
                QMessageBox.warning(self.dlg, "Attention", "Veuillez sélectionner un marché dans la liste déroulante.")
                return
                
            # Lancer la mise en page marché
            self.mise_en_page_marche()
        else:
            # Sinon, on lance la mise en page standard
            self.mise_en_page()

    def charger_fond_carte_secondaire(self):
        """
        Charge le fond de carte SCAN25 et retourne une référence fraîche
        """
        scan25_url = 'contextualWMSLegend=0&crs=EPSG:2154&dpiMode=7&featureCount=10&format=image/jpeg&http-header:apikey=ign_scan_ws&layers=SCAN25TOUR_PYR-JPEG_WLD_WM&styles&tilePixelRatio=0&url=https://data.geopf.fr/private/wms-r?VERSION%3D1.3.0'
        scan25_layer = QgsRasterLayer(scan25_url, 'SCAN25', 'wms')
        
        if not scan25_layer.isValid():
            print("ERREUR: Impossible de charger le fond de carte SCAN25")
            return None
        
        # Ajouter au projet si aucune couche avec le même nom n'existe déjà
        project = QgsProject.instance()
        if not project.mapLayersByName("SCAN25"):
            project.addMapLayer(scan25_layer)
        else:
            # Supprimer les anciennes références et ajouter la nouvelle
            for old_layer in project.mapLayersByName("SCAN25"):
                project.removeMapLayer(old_layer)
            project.addMapLayer(scan25_layer)
        
        return scan25_layer


    def mise_en_page(self):

        # Utiliser la méthode charger_fond_carte de la classe MapCEN pour charger le fond de carte
        self.fond_carte = None
        try:
            from qgis.utils import plugins
            map_cen_instance = plugins['map_cen']
            self.fond_carte = map_cen_instance.charger_fond_carte()
            
            if not self.fond_carte or not self.fond_carte.isValid():
                print("Impossible de charger le fond de carte. La mise en page sera générée sans fond de carte.")
        except Exception as e:
            print(f"Erreur lors du chargement du fond de carte: {e}")
            self.fond_carte = None

        # Sélection des entités selon le nom_site choisi
        site_selected = self.dlg.mComboBox.currentText()
        self.travaux_layer.selectByExpression(f"site_gere = '{site_selected}'")

        # Vérifier si la sélection a trouvé un site correspondant
        if self.travaux_layer.selectedFeatureCount() == 0:
            QMessageBox.information(self.dlg, "Aucun site trouvé", f"Le site sélectionné ('{site_selected}') n'existe pas dans le champ 'site_gere' de la couche travaux. Vérifiez que le nom de ce site est exactement le même que dans FoncierCEN !")

        for sites in self.dlg.mComboBox.checkedItems():
            self.travaux_layer.selectByExpression('"site_gere"= \'{0}\''.format(sites.replace("'", "''")),
                                           QgsVectorLayer.AddToSelection)

        # Zoom sur la sélection
        iface.mapCanvas().zoomToSelected(self.travaux_layer)
        extent = iface.mapCanvas().extent()

        self.sites_gere_centroid_layer.removeSelection()

        for sites in self.dlg.mComboBox.checkedItems():
            self.sites_gere_centroid_layer.selectByExpression('"nom_site"= \'{0}\''.format(sites.replace("'", "''")),
                                           QgsVectorLayer.AddToSelection)

        # Appliquer un style de centroïde à la couche des sites sélectionnés
        self.appliquer_style_centroide(
            self.sites_gere_centroid_layer,
            couleur='red',
            taille=3,
            filter_expression="is_selected()"
        )
        
        # Rafraîchir la couche sur le canevas de la carte
        self.sites_gere_centroid_layer.triggerRepaint()

        # Création du layout
        project = QgsProject.instance()
        manager = project.layoutManager()
        layout_name = 'Mise en page automatique MapCEN (Travaux)'
        
        # Suppression des layouts existants avec le même nom
        layouts_list = manager.printLayouts()
        for layout in layouts_list:
            if layout.name() == layout_name:
                manager.removeLayout(layout)

        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName(layout_name)
        manager.addLayout(layout)


        myRenderer_site = self.sites_gere_poly_layer.renderer()

        mySymbol2 = QgsSymbol.defaultSymbol(self.sites_gere_poly_layer.geometryType())
        fill_layer = QgsSimpleFillSymbolLayer.create(
            {'color': '255,255,255,0', 'outline_color': '255,0,0,255', 'outline_width': '0.4'}
        )
        mySymbol2.changeSymbolLayer(0, fill_layer)
        myRenderer_site.setSymbol(mySymbol2)

        self.sites_gere_poly_layer.triggerRepaint()

        # Carte principale
        main_map = QgsLayoutItemMap(layout)
        main_map.setRect(20, 20, 20, 20)
        
        # Définir les bornes du buffer autour de l'emprise du site
        min_buffer = 70    # Marge minimale en mètres à appliquer (même pour les très petits sites)
        max_buffer = 350   # Marge maximale en mètres à ne pas dépasser (même pour les très grands sites)

        # Calcul du buffer horizontal (x) et vertical (y) en fonction de la taille du site
        # On prend 50% de la largeur/hauteur de l'emprise, mais on le contraint dans les bornes min et max
        buffer_x = max(min(extent.width() * 0.5, max_buffer), min_buffer)
        buffer_y = max(min(extent.height() * 0.5, max_buffer), min_buffer)

        # Création d'une nouvelle emprise (QgsRectangle) étendue de part et d'autre
        buffered_extent = QgsRectangle(extent)

        # On applique le buffer horizontal (gauche et droite)
        buffered_extent.setXMinimum(extent.xMinimum() - buffer_x)
        buffered_extent.setXMaximum(extent.xMaximum() + buffer_x)

        # On applique le buffer vertical (haut et bas)
        buffered_extent.setYMinimum(extent.yMinimum() - buffer_y)
        buffered_extent.setYMaximum(extent.yMaximum() + buffer_y)

        # On définit cette nouvelle emprise tamponnée comme l'étendue de la carte principale
        main_map.setExtent(buffered_extent)


        if self.fond_carte and self.fond_carte.isValid():
            main_map.setLayers([self.sites_gere_poly_layer, self.travaux_layer, self.fond_carte])
        else:
            main_map.setLayers([self.sites_gere_poly_layer, self.travaux_layer])


        # Position et taille de la carte principale
        main_map.attemptMove(QgsLayoutPoint(5, 23, QgsUnitTypes.LayoutMillimeters))
        main_map.attemptResize(QgsLayoutSize(185, 182, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(main_map)

        ## Ajout du logo CEN NA en bas à droite de la carte principale
        logo = QgsLayoutItemPicture(layout)
        logo.setResizeMode(QgsLayoutItemPicture.Zoom)
        logo.setMode(QgsLayoutItemPicture.FormatRaster)
        logo.setPicturePath(os.path.dirname(__file__) + '/icons/logo.jpg')
        
        # Positionnement en bas à droite de la carte principale
        logo.attemptMove(QgsLayoutPoint(147, 190, QgsUnitTypes.LayoutMillimeters))
        
        # Taille réduite de 30%
        original_width = 720
        original_height = 249
        reduced_width = original_width * 0.7  # Réduction de 30%
        reduced_height = original_height * 0.7  # Réduction de 30%
        logo.attemptResize(QgsLayoutSize(reduced_width, reduced_height, QgsUnitTypes.LayoutPixels))
        
        layout.addLayoutItem(logo)

        # Carte de localisation (en haut à droite)
        loc_map = QgsLayoutItemMap(layout)
        loc_map.setRect(20, 20, 20, 20)

        min_buffer = 200
        max_buffer = 400

        buffer_x = max(min(extent.width() * 0.5, max_buffer), min_buffer)
        buffer_y = max(min(extent.height() * 0.5, max_buffer), min_buffer)

        buffered_extent = QgsRectangle(extent)
        buffered_extent.setXMinimum(extent.xMinimum() - buffer_x)
        buffered_extent.setXMaximum(extent.xMaximum() + buffer_x)
        buffered_extent.setYMinimum(extent.yMinimum() - buffer_y)
        buffered_extent.setYMaximum(extent.yMaximum() + buffer_y)
        
        loc_map.setExtent(buffered_extent)

        # Charger le fond de carte SCAN25 pour la carte de localisation
        fond_carte_secondaire = self.charger_fond_carte_secondaire()
        if fond_carte_secondaire:
            loc_map.setLayers([self.sites_gere_poly_layer, self.travaux_layer, fond_carte_secondaire])
        else:
            loc_map.setLayers([self.sites_gere_poly_layer, self.travaux_layer])


        # Position et taille de la carte de localisation
        loc_map.setFrameEnabled(True)  # Activer le cadre pour mieux voir la carte
        loc_map.attemptMove(QgsLayoutPoint(203, 24, QgsUnitTypes.LayoutMillimeters))
        loc_map.attemptResize(QgsLayoutSize(82, 82, QgsUnitTypes.LayoutMillimeters))
        loc_map.setZValue(1)  # au-dessus de l'ellipse
        layout.addLayoutItem(loc_map)


        # Carte des centroïdes (petite carte en haut à droite de loc_map)
        centroid_map = QgsLayoutItemMap(layout)
        centroid_map.setFrameEnabled(False)
        centroid_map.setBackgroundColor(Qt.transparent)
        centroid_map.attemptMove(QgsLayoutPoint(265, 11, QgsUnitTypes.LayoutMillimeters))
        centroid_map.attemptResize(QgsLayoutSize(22, 22, QgsUnitTypes.LayoutMillimeters))
        centroid_map.setZValue(20)  # au-dessus de l'ellipse

        extent = self.get_dept_extent()
        centroid_map.setExtent(extent)
        centroid_map.setLayers([self.sites_gere_centroid_layer, self.depts_NA])

        # === Ellipse de fond pour la mini-carte des centroïdes ===
        ellipse = QgsLayoutItemShape(layout)
        ellipse.setShapeType(QgsLayoutItemShape.Ellipse)
        ellipse.attemptMove(QgsLayoutPoint(261, 8, QgsUnitTypes.LayoutMillimeters))
        ellipse.attemptResize(QgsLayoutSize(30, 30, QgsUnitTypes.LayoutMillimeters))

        # Apparence
        symbol = QgsFillSymbol.createSimple({
            'color': '255,255,255,255',  
            'outline_color': '0,0,0,200',
            'outline_width': '0.3'
        })
        ellipse.setSymbol(symbol)

        ellipse.setZValue(10)  # s'assurer qu'elle est sous la carte

        layout.addLayoutItem(ellipse)


        myRenderer = self.depts_NA.renderer()

        if self.depts_NA.geometryType() == QgsWkbTypes.PolygonGeometry:
            mySymbol1 = QgsSymbol.defaultSymbol(self.depts_NA.geometryType())
            fill_layer = QgsSimpleFillSymbolLayer.create(
                {'color': '255,255,255,255', 'outline_color': '0,0,0,255', 'outline_width': '0.1'}
            )
            mySymbol1.changeSymbolLayer(0, fill_layer)
            myRenderer.setSymbol(mySymbol1)

        self.depts_NA.triggerRepaint()

        # Créer un rectangle légèrement plus grand pour avoir une marge
        center = extent.center()
        # Prendre la plus grande dimension pour créer un carré
        max_dim = max(extent.width(), extent.height()) * 1.6
        new_extent = QgsRectangle(
            center.x() - max_dim / 2,
            center.y() - max_dim / 2,
            center.x() + max_dim / 2,
            center.y() + max_dim / 2
        )
        centroid_map.setExtent(new_extent)
            

        # S'assurer que la carte est visible et au-dessus des autres éléments
        centroid_map.refresh()
        layout.addLayoutItem(centroid_map)


        # Get the values from the selected feature(s)
        selected_features = self.travaux_layer.selectedFeatures()
        if selected_features:
            # Use the first selected feature (you could also handle multiple selections differently)
            selected_feature = selected_features[0]
            commune = selected_feature['commune(s)']
            code_proj = selected_feature['code_proj']
            site_gere = selected_feature['site_gere']
        else:
            # Fallback values if no features are selected
            commune = "N/A"
            code_proj = "N/A"
            site_gere = self.dlg.mComboBox.currentText()  # Use the selected site from the combo box

        # Ajouter les éléments de mise en page
        # Titre principal
        titre = QgsLayoutItemLabel(layout)
        titre.setText(f"{site_gere}")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        titre.adjustSizeToText()
        # Augmenter la largeur du titre pour éviter la coupure
        titre.setFixedSize(QgsLayoutSize(250, 10, QgsUnitTypes.LayoutMillimeters))
        titre.attemptMove(QgsLayoutPoint(5, 5, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(titre)

        # Sous-titre
        sous_titre = QgsLayoutItemLabel(layout)
        sous_titre.setText(f"{commune} - {self.dlg.mComboBox_4.currentText()} - {code_proj}")
        sous_titre.setFont(QFont("Arial", 12))
        sous_titre.adjustSizeToText()
        # Augmenter la largeur du sous-titre
        sous_titre.setFixedSize(QgsLayoutSize(200, 10, QgsUnitTypes.LayoutMillimeters))
        sous_titre.attemptMove(QgsLayoutPoint(5, 15, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(sous_titre)

        # Légende
        legend_cen = QgsLayoutItemLegend(layout)
        legend_cen.setLinkedMap(main_map)
        legend_cen.setAutoUpdateModel(False)
        legend_cen.model().rootGroup().clear()
        legend_cen.model().rootGroup().addLayer(self.sites_gere_poly_layer)

        legend_cen.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 11, QFont.Bold))
        legend_cen.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 9))

        legend_cen.setLegendFilterByMapEnabled(True)
        legend_cen.setFrameEnabled(False)
        legend_cen.adjustBoxSize()

        # Positionner plus bas que la première légende (ex: 145 au lieu de 99)
        legend_cen.attemptMove(QgsLayoutPoint(197, 108, QgsUnitTypes.LayoutMillimeters))
        legend_cen.attemptResize(QgsLayoutSize(60, 25, QgsUnitTypes.LayoutMillimeters))

        layout.addLayoutItem(legend_cen)

        # === Légende 2 : Travaux ===
        legend_travaux = QgsLayoutItemLegend(layout)
        legend_travaux.setTitle("Type d'intervention")
        legend_travaux.setLinkedMap(main_map)
        legend_travaux.setAutoUpdateModel(False)
        legend_travaux.model().rootGroup().clear()
        legend_travaux.model().rootGroup().addLayer(self.travaux_layer)
        # Masquer le nom de la couche ("Travaux_site_xxx") dans la légende
        for node in legend_travaux.model().rootGroup().findLayers():
            QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Hidden)
        
        # Style police
        legend_travaux.setStyleFont(QgsLegendStyle.Title, QFont("Arial", 11, QFont.Bold))
        legend_travaux.setStyleFont(QgsLegendStyle.SymbolLabel, QFont("Arial", 9))

        legend_travaux.setLegendFilterByMapEnabled(True)
        legend_travaux.setFrameEnabled(False)
        legend_travaux.adjustBoxSize()
        legend_travaux.attemptMove(QgsLayoutPoint(197, 123, QgsUnitTypes.LayoutMillimeters))
        legend_travaux.attemptResize(QgsLayoutSize(30, 40, QgsUnitTypes.LayoutMillimeters))

        layout.addLayoutItem(legend_travaux)

        # Échelle
        scalebar = QgsLayoutItemScaleBar(layout)
        scalebar.setStyle('Single Box')
        scalebar.setLinkedMap(main_map)
        scalebar.applyDefaultSize()
        scalebar.applyDefaultSettings()
        
        scalebar.setNumberOfSegments(2)
        scalebar.setNumberOfSegmentsLeft(0)
        
        layout.addLayoutItem(scalebar)
        scalebar.attemptMove(QgsLayoutPoint(222, 178, QgsUnitTypes.LayoutMillimeters))
        scalebar.setFixedSize(QgsLayoutSize(50, 15))

        # Flèche du Nord
        north = QgsLayoutItemPicture(layout)
        north.setPicturePath(os.path.dirname(__file__) + "/NorthArrow_02.svg")
        layout.addLayoutItem(north)
        north.attemptResize(QgsLayoutSize(8.4, 12.5, QgsUnitTypes.LayoutMillimeters))
        north.attemptMove(QgsLayoutPoint(205, 178, QgsUnitTypes.LayoutMillimeters))


        # Crédits
        date_du_jour = date.today().strftime("%d/%m/%Y")
        credit_text = QgsLayoutItemLabel(layout)
        credit_text.setText(f"Réalisation : CEN Nouvelle-Aquitaine ({date_du_jour})")
        credit_text.setFont(QFont("Arial", 8))
        layout.addLayoutItem(credit_text)
        credit_text.attemptMove(QgsLayoutPoint(210, 198, QgsUnitTypes.LayoutMillimeters))
        credit_text.adjustSizeToText()
        
        credit_text2 = QgsLayoutItemLabel(layout)
        credit_text2.setText("Source: Google (fond satellite), IGN (fond SCAN25)")
        credit_text2.setFont(QFont("Arial", 8))
        layout.addLayoutItem(credit_text2)
        credit_text2.attemptMove(QgsLayoutPoint(210, 203, QgsUnitTypes.LayoutMillimeters))
        credit_text2.adjustSizeToText()

        # Rafraîchir le layout
        layout.refresh()

        # Afficher dans la vue
        self.layout_carto_travaux = layout
        self.dlg.graphicsView.setScene(layout)


        # Réinitialiser le filtre sur la couche des départements
        self.depts_NA.setSubsetString("")
    

    def appliquer_style_centroide(self, layer, couleur='red', taille=3, etiquette_champ=None, filter_expression="TRUE"):
        """
        Applique un style de centroïde à une couche vectorielle
        
        Args:
            layer (QgsVectorLayer): La couche à laquelle appliquer le style
            couleur (str): Couleur du centroïde (nom de couleur ou code hex)
            taille (float): Taille du marqueur en mm
            etiquette_champ (str, optional): Nom du champ à utiliser pour les étiquettes
            filter_expression (str, optional): Expression de filtre pour les règles
        """
        # Définir les règles de style (similaire au code existant lignes 338-373)
        rules = (
            ('Centroïde', filter_expression, couleur),
        )

        # Créer un nouveau renderer basé sur des règles
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        renderer = QgsRuleBasedRenderer(symbol)

        # Obtenir la règle racine
        root_rule = renderer.rootRule()

        for label, expression, color_name in rules:
            # Créer un clone de la règle par défaut
            rule = root_rule.children()[0].clone()
            # Configurer la règle
            rule.setLabel(label)
            rule.setFilterExpression(expression)
            symbol_layer = rule.symbol().symbolLayer(0)
            
            # Configurer le générateur de géométrie pour les centroïdes
            generator = QgsGeometryGeneratorSymbolLayer.create({})
            generator.setSymbolType(QgsSymbol.Marker)
            generator.setGeometryExpression("centroid($geometry)")
            
            # Personnaliser le marqueur
            marker_symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.PointGeometry)
            marker_symbol.setColor(QColor(color_name))
            marker_symbol.setSize(taille)
            generator.setSubSymbol(marker_symbol)
            
            # Appliquer le générateur au symbole de la règle
            rule.symbol().changeSymbolLayer(0, generator)
            root_rule.appendChild(rule)

        # Supprimer la règle par défaut
        root_rule.removeChildAt(0)

        # Appliquer le renderer à la couche
        layer.setRenderer(renderer)
        
        # Configurer les étiquettes si un champ est spécifié
        if etiquette_champ and etiquette_champ in [field.name() for field in layer.fields()]:
            # Créer les paramètres d'étiquetage
            from qgis.core import QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling
            
            label_settings = QgsPalLayerSettings()
            label_settings.fieldName = etiquette_champ
            
            # Configurer le style de texte
            text_format = QgsTextFormat()
            text_format.setFont(QFont("Arial"))
            text_format.setSize(9)
            text_format.setColor(QColor("black"))
            
            # Ajouter un buffer blanc autour du texte pour améliorer la lisibilité
            buffer_settings = QgsTextBufferSettings()
            buffer_settings.setEnabled(True)
            buffer_settings.setSize(1)
            buffer_settings.setColor(QColor("white"))
            text_format.setBuffer(buffer_settings)
            
            label_settings.setFormat(text_format)
            
            # Configurer le placement des étiquettes
            label_settings.placement = QgsPalLayerSettings.AroundPoint

            # Forcer l'affichage de toutes les étiquettes
            label_settings.displayAll = True
            label_settings.obstacle = False
            label_settings.avoidIntersections = False
            
            # Appliquer les paramètres d'étiquetage
            layer_settings = QgsVectorLayerSimpleLabeling(label_settings)
            layer.setLabelsEnabled(True)
            layer.setLabeling(layer_settings)
        
        layer.triggerRepaint()


    def mise_en_page_marche(self):
        """
        Génère une mise en page spécifique pour un marché
        Cette fonction est appelée uniquement lors du clic sur le bouton commandLinkButton_4
        et si la checkbox "Générer une carto générale d'un marché" est cochée
        """

        # Récupérer le nom du marché sélectionné
        nom_marche = self.dlg.mComboBox_3.currentText()
        if not nom_marche:
            return
            
        # # Copie de la couche pour la carte secondaire (sans étiquettes)
        # sites_gere_centroid_layer_sans_labels = self.sites_gere_centroid_layer.clone()
        # # Récupérer les IDs sélectionnés dans la couche originale
        # selected_ids = self.sites_gere_centroid_layer.selectedFeatureIds()
        # # Appliquer cette sélection à la couche clonée
        # sites_gere_centroid_layer_sans_labels.selectByIds(selected_ids)

        # sites_gere_centroid_layer_sans_labels.setName("Sites gérés sans étiquettes")

        # # Désactiver les étiquettes sur cette copie
        # sites_gere_centroid_layer_sans_labels.setLabelsEnabled(False)

        # # Ajouter la couche au projet sans l'afficher dans le panneau de couches
        # QgsProject.instance().addMapLayer(sites_gere_centroid_layer_sans_labels, False)

        
        # Appliquer un style de centroïde à la couche sites_gere_centroid_layer avec étiquettes
        self.appliquer_style_centroide(self.sites_gere_centroid_layer, couleur='red', taille=2, etiquette_champ='nom_site')
        # # Appliquer le même style de centroïde à la couche sans étiquettes
        # self.appliquer_style_centroide(sites_gere_centroid_layer_sans_labels, couleur='red', taille=2)
        
        # Créer un nouveau layout
        project = QgsProject.instance()
        manager = project.layoutManager()
        
        # Vérifier si un layout avec ce nom existe déjà et le supprimer
        layout_name = f"Marché - {nom_marche}"
        existing_layouts = manager.layouts()
        for layout in existing_layouts:
            if layout.name() == layout_name:
                manager.removeLayout(layout)
        
        # Créer un nouveau layout
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName(layout_name)
        
        # Ajouter le layout au gestionnaire de layouts
        manager.addLayout(layout)


        extent = self.get_dept_extent()
        if extent is None:
            # L'utilisateur a été prévenu dans la méthode, on arrête la génération
            return

        
       # === Carte principale ===
        main_map = QgsLayoutItemMap(layout)
        main_map.setRect(20, 20, 20, 20)
        
        # Au lieu d'appliquer un buffer basé sur un pourcentage de la taille,
        # nous allons simplement utiliser l'étendue complète du département avec une petite marge fixe
        # pour garantir que l'intégralité du département est visible
        
        # Marge fixe en mètres pour s'assurer que les bords du département ne sont pas coupés
        fixed_margin = 90000  # 4 km de marge
        
        # Création d'une nouvelle emprise (QgsRectangle) avec la marge fixe
        buffered_extent = QgsRectangle(extent)
        
        # On applique la marge fixe sur tous les côtés
        buffered_extent.setXMinimum(extent.xMinimum() - fixed_margin)
        buffered_extent.setXMaximum(extent.xMaximum() + fixed_margin)
        buffered_extent.setYMinimum(extent.yMinimum() - fixed_margin)
        buffered_extent.setYMaximum(extent.yMaximum() + fixed_margin)
        
        # On définit cette nouvelle emprise comme l'étendue de la carte principale
        main_map.setExtent(buffered_extent)

        self.fond_carte = None
        try:
            from qgis.utils import plugins
            map_cen_instance = plugins['map_cen']
            self.fond_carte = map_cen_instance.charger_fond_carte()
            
            if not self.fond_carte or not self.fond_carte.isValid():
                print("Impossible de charger le fond de carte. La mise en page sera générée sans fond de carte.")
        except Exception as e:
            print(f"Erreur lors du chargement du fond de carte: {e}")
            self.fond_carte = None

        if self.fond_carte and self.fond_carte.isValid():
            main_map.setLayers([self.sites_gere_centroid_layer, self.depts_NA, self.fond_carte])
        else:
            main_map.setLayers([self.sites_gere_centroid_layer, self.depts_NA])

        # Position et taille de la carte principale (identique à mise_en_page)
        main_map.attemptMove(QgsLayoutPoint(5, 23, QgsUnitTypes.LayoutMillimeters))
        main_map.attemptResize(QgsLayoutSize(287, 158, QgsUnitTypes.LayoutMillimeters))
        layout.addLayoutItem(main_map)
        
        
        # === Titre ===
        titre = QgsLayoutItemLabel(layout)
        titre.setText(f"Marché : {nom_marche}")
        titre.setFont(QFont("Arial", 16, QFont.Bold))
        titre.adjustSizeToText()
        layout.addLayoutItem(titre)
        titre.attemptMove(QgsLayoutPoint(5, 5, QgsUnitTypes.LayoutMillimeters))
        
        # === Sous-titre ===
        sous_titre = QgsLayoutItemLabel(layout)
        sous_titre.setText("Carte générale des sites concernés par les travaux")
        sous_titre.setFont(QFont("Arial", 12))
        layout.addLayoutItem(sous_titre)
        sous_titre.attemptMove(QgsLayoutPoint(5, 12, QgsUnitTypes.LayoutMillimeters))

        # Ajout du logo CEN NA en bas à droite de la carte principale
        logo = QgsLayoutItemPicture(layout)
        logo.setResizeMode(QgsLayoutItemPicture.Zoom)
        logo.setMode(QgsLayoutItemPicture.FormatRaster)
        logo.setPicturePath(os.path.dirname(__file__) + '/icons/logo.jpg')
        
        # Positionnement en bas à droite de la carte principale
        logo.attemptMove(QgsLayoutPoint(248, 5, QgsUnitTypes.LayoutMillimeters))
        
        # Taille réduite de 30%
        original_width = 720
        original_height = 249
        reduced_width = original_width * 0.7  # Réduction de 30%
        reduced_height = original_height * 0.7  # Réduction de 30%
        logo.attemptResize(QgsLayoutSize(reduced_width, reduced_height, QgsUnitTypes.LayoutPixels))
        
        layout.addLayoutItem(logo)
        
        # === Échelle ===
        scalebar = QgsLayoutItemScaleBar(layout)
        scalebar.setStyle('Single Box')
        scalebar.setLinkedMap(main_map)

        scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
        scalebar.setUnitLabel("km")
        scalebar.setNumberOfSegments(2)
        scalebar.setNumberOfSegmentsLeft(0)
        scalebar.setUnitsPerSegment(25)  # chaque segment = 25 km

        scalebar.attemptMove(QgsLayoutPoint(223, 184, QgsUnitTypes.LayoutMillimeters))

        scalebar.update()

        layout.addLayoutItem(scalebar)
        
        
        # === Flèche du Nord ===
        north = QgsLayoutItemPicture(layout)
        north.setPicturePath(os.path.dirname(__file__) + "/NorthArrow_02.svg")
        layout.addLayoutItem(north)
        north.attemptResize(QgsLayoutSize(8.4, 12.5, QgsUnitTypes.LayoutMillimeters))
        north.attemptMove(QgsLayoutPoint(205, 183, QgsUnitTypes.LayoutMillimeters))
        
        # === Crédits ===
        date_du_jour = date.today().strftime("%d/%m/%Y")
        credit_text = QgsLayoutItemLabel(layout)
        credit_text.setText(f"Réalisation : CEN Nouvelle-Aquitaine ({date_du_jour})")
        credit_text.setFont(QFont("Arial", 8))
        layout.addLayoutItem(credit_text)
        credit_text.attemptMove(QgsLayoutPoint(218, 199, QgsUnitTypes.LayoutMillimeters))
        credit_text.adjustSizeToText()
        
        credit_text2 = QgsLayoutItemLabel(layout)
        credit_text2.setText("Source: Google (fond satellite), IGN (fond SCAN25)")
        credit_text2.setFont(QFont("Arial", 8))
        layout.addLayoutItem(credit_text2)
        credit_text2.attemptMove(QgsLayoutPoint(218, 203, QgsUnitTypes.LayoutMillimeters))
        credit_text2.adjustSizeToText()
        
        # Rafraîchir le layout
        layout.refresh()
        
        # Afficher dans la vue
        self.layout_carto_travaux = layout
        self.dlg.graphicsView.setScene(layout)
        

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
