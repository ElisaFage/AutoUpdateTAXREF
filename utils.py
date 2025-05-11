from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsProject,          # Pour manipuler le projet QGIS (pas utilisé directement ici mais peut être utile pour enregistrer la couche dans le projet)
    QgsVectorLayer,      # Pour charger et manipuler une couche vectorielle
    QgsVectorFileWriter, # Pour écrire la couche vectorielle dans un fichier (GeoPackage)
    QgsField,            # Pour définir un champ (une colonne) dans la couche
    QgsFields,           # Pour stocker les champs (colonnes)
    QgsFeature,          # Représente une entité (ligne) dans la couche
    QgsCoordinateReferenceSystem, # Pour définir le CRS (référence spatiale)
    QgsVectorDataProvider, # Pour accéder et modifier les données de la couche
    QgsProviderRegistry,
    Qgis,
    QgsWkbTypes)

from PyQt5.QtCore import QVariant  # Pour spécifier les types de données des colonnes

from datetime import datetime
import os
import re
import unicodedata

import pandas as pd
import geopandas as gpd

def retirer_accents(texte):
    # Normalisation unicode (décomposition des caractères accentués)
    texte_normalise = unicodedata.normalize('NFD', texte)
    # Filtre les caractères combinants (accents)
    texte_sans_accents = ''.join(
        c for c in texte_normalise
        if unicodedata.category(c) != 'Mn'
    )
    return texte_sans_accents

def print_debug_info(debug_level: int,
                     debug_threshold: int,
                     msg: str,
                     name: str="")->None:

    if debug_level > debug_threshold :
        now = datetime.now()
        full_message = name+msg+f" ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})"
        QgsMessageLog.logMessage(full_message, "AutoUpdateTAXREF", level=Qgis.Info)

    return

def log_features(features: list, title="Features") -> None:
    QgsMessageLog.logMessage(f"\t{title} ({len(features)} entités) :", "AutoUpdateTAXREF")
    for i, feat in enumerate(features):
        QgsMessageLog.logMessage(f"\t{i}: ID={feat.id()}, Attributs={feat.attributes()}", "AutoUpdateTAXREF")
        if feat.hasGeometry():
            QgsMessageLog.logMessage(f"\t{i}: Géométrie={feat.geometry().asWkt()}", "AutoUpdateTAXREF")
        if i >= 9:
            QgsMessageLog.logMessage("\t… (affichage limité à 10 entités)", "AutoUpdateTAXREF")
            break

def log_layer(layer: QgsVectorLayer, title="Layer") -> None:
    QgsMessageLog.logMessage(f"\t{title} :", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  Nom : {layer.name()}", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  Source : {layer.source()}", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  CRS : {layer.crs().authid()}", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  Géométrie : {layer.wkbType()}", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  Champs ({layer.fields().count()}) : {[field.name() for field in layer.fields()]}", "AutoUpdateTAXREF")
    QgsMessageLog.logMessage(f"\t  Nombre d'entités : {layer.featureCount()}", "AutoUpdateTAXREF")
    
    for i, feat in enumerate(layer.getFeatures()):
        QgsMessageLog.logMessage(f"\t  Feature {i} : ID={feat.id()}, Attributs={feat.attributes()}", "AutoUpdateTAXREF")
        if feat.hasGeometry():
            QgsMessageLog.logMessage(f"\t  Feature {i} : Géométrie={feat.geometry().asWkt()}", "AutoUpdateTAXREF")
        if i >= 4:
            QgsMessageLog.logMessage("\t  … (affichage limité à 5 entités)", "AutoUpdateTAXREF")
            break

def time_decorator(function):

    def wrapper(*args, **kwargs):

        print_debug_info(1, 0, f"Début de {function.__name__}")
        rv = function(*args, **kwargs)
        print_debug_info(1, 0, f"Fin de {function.__name__}")

        return rv
    
    return wrapper

def is_gpkg_open(filepath: str):
    filepath = filepath.replace('\\', '/')  # Normaliser les chemins Windows
    for layer in QgsProject.instance().mapLayers().values():
        # layer.source() donne le chemin source, parfois avec des paramètres supplémentaires
        if layer.source().startswith(filepath):
            return True
    return False

def list_layers_from_qgis(filepath: str):

    filepath = str(filepath).lower().replace("\\", "/")

    layers = QgsProject.instance().mapLayers().values()
    layer_names = []

    for layer in layers:
        
        uri = layer.dataProvider().dataSourceUri().lower()
        #print_debug_info(1, 0, uri)
        if filepath in uri:
            layer_names.append(layer.source().split("layername=")[1])

    #print_debug_info(1, 0, filepath)

    return layer_names

def list_layers_from_gpkg(filepath: str):

    filepath = str(filepath).replace("\\", "/")
    layers = []
    
    metadata = QgsProviderRegistry.instance().providerMetadata('ogr')
    
    try:
        sublayers = metadata.querySublayers(filepath)
        print_debug_info(1, 0, f"{sublayers}")
        for sublayer in sublayers:
            if sublayer.name :
                layers.append(sublayer.name)
    except AttributeError:
        # Si querySublayers n'existe pas (ex: QGIS 3.34), fallback
        layer_list = metadata.listLayers(filepath, 'GPKG')
        print_debug_info(1, 0, f"{layer_list}")
        for layer_info in layer_list:
            if layer_info.name :
                layers.append(layer_info.name)
    
    return layers

def list_layer_from_gpd(filepath: str):

    filepath = str(filepath).replace("\\", "/")
    layers = gpd.io.file.fiona.listlayers(filepath)

    return layers

def load_layer_as_dataframe(filepath: str, layer_name: str):

    uri = f"{filepath}|layername={layer_name}".lower()
    layer = QgsVectorLayer(uri, layer_name, "ogr")
    if not layer.isValid():
        raise ValueError(f"La couche '{layer_name}' n'a pas pu être chargée depuis {filepath}")

    data = []
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        data.append(attrs)

    # Récupérer les noms de champs
    fields = [field.name() for field in layer.fields()]

    df = pd.DataFrame(data, columns=fields)
    return df

def get_file_save_path(path: str,
                       taxon_title: str="")->str:
    
    file_save_path = os.path.join(path, "Statuts.gpkg")

    return file_save_path

@time_decorator
def save_dataframe(df: pd.DataFrame,
                   filepath: str,
                   layername: str)->None:
    
    # Conversion en GeoDataFrame avant sauvegarde
    gdf = gpd.GeoDataFrame(df)
    print_debug_info(1,0, f"{layername} : {gdf.columns}")

    """# Étape 1 : vérifier si une couche utilise ce fichier + layername
    layers_to_remove = []
    for layer in QgsProject.instance().mapLayers().values():
        if layer.source().startswith(filepath) and f"layername={layername}" in layer.source():
            layers_to_remove.append(layer)

    # Étape 2 : si oui, la retirer du projet
    if layers_to_remove:
        for layer in layers_to_remove:
            QgsProject.instance().removeMapLayer(layer.id())"""
    
    if "fid" in gdf.columns:
        gdf = gdf.drop(columns=["fid"])

    # Étape 3 : sauver le GeoDataFrame
    gdf.to_file(filepath, layer=layername, driver="GPKG", index=False)
    
    return

def gpkg_file_in_project(file_path: str) -> bool:
    """Vérifie si un fichier .gpkg est déjà utilisé par une couche du projet."""
    for layer in QgsProject.instance().mapLayers().values():
        if layer.providerType() == "ogr" and layer.dataProvider().dataSourceUri().startswith(file_path):
            return True
    return False

def get_features_to_add(df: pd.DataFrame, layer)->list:
    
    print_debug_info(1,0,"get_features_to_add")

    features = []  # Liste des entités à ajouter
    for _, row in df.iterrows():  # Pour chaque ligne du DataFrame
        feat = QgsFeature(layer.fields())  # Créer une nouvelle entité avec les champs de la couche
        for col in df.columns:  # Remplir les valeurs de l'entité avec celles du DataFrame
            if pd.isna(row[col]):  # Si la valeur est NaN, on laisse la case vide
                pass
                #feat[col] = None
                #feat.setNull(feat.fieldNameIndex(col))  # Marquer l'attribut comme étant nul
            else:
                feat[col] = row[col]  # Assigner la valeur non-NaN  # Remplir les valeurs de l'entité avec celles du DataFrame
        features.append(feat)  # Ajouter l'entité à la liste

    return features

def add_layer_to_map(file_path, uri, layer_name)->None:
    print_debug_info(1,0,"add_layer_to_map")
    if gpkg_file_in_project(file_path):
            reloaded_layer = QgsVectorLayer(uri, layer_name, "ogr")
            if reloaded_layer.isValid():
                if QgsProject.instance().addMapLayer(reloaded_layer) == None:
                    raise Exception(f"QgsProject.instance().addMapLayer(reloaded_layer) failed for {layer_name}")

    return

@time_decorator
def save_to_gpkg_via_qgs(df: pd.DataFrame,
                         file_path: str,
                         layer_name: str,
                         debug: int=0)->None:
    """
    Cette fonction enregistre un DataFrame Pandas dans un fichier GeoPackage (.gpkg),
    dans une couche spécifiée. Si la couche existe déjà, elle sera mise à jour. Sinon, elle sera créée.
    """

    print_debug_info(debug , 3, f"Save étape 0 : colonne {df.columns} et nombre de lignes {df.shape[0]}")

    # Étape 1 : Créer les champs à partir des colonnes du DataFrame
    fields = QgsFields()  # Crée un objet contenant tous les champs (colonnes)
    for col in df.columns:  # Pour chaque colonne dans le DataFrame
        # On extrait une valeur de la colonne pour déterminer son type de données
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
        
        # Déterminer le type de données en fonction de la valeur de l'exemple
        if isinstance(sample, (int, float)):  # Si c'est un nombre entier ou flottant
            field_type = QVariant.Double if isinstance(sample, float) else QVariant.Int
        else:  # Sinon, on considère que c'est une chaîne de caractères
            field_type = QVariant.String
        
        # Ajouter le champ (colonne) à la liste des champs
        fields.append(QgsField(col, field_type))

    print_debug_info(debug, 3, "save_to_gpkg_via_qgs Etape 1 fin")

    # Étape 2 : Vérifier si la couche existe déjà dans le fichier GeoPackage
    uri = f"{file_path}|layername={layer_name}"  # Création de l'URI pour accéder à la couche
    existing_layer = QgsVectorLayer(uri, layer_name, "ogr")  # Chargement de la couche avec le fournisseur "ogr" (pour GeoPackage)

    print_debug_info(debug, 3, "save_to_gpkg_via_qgs Etape 2 fin")

    if existing_layer.isValid():  # Si la couche existe et est valide
        # Étape 3 : La couche existe - On met à jour la couche avec les nouvelles données
        
        # Accéder au fournisseur de données de la couche existante
        provider = existing_layer.dataProvider()

        # Supprimer toutes les entités (lignes) existantes dans la couche
        if not provider.truncate() :
            raise Exception("provider.truncate failed")

        # Ajouter les nouveaux champs (colonnes) si nécessaire
        existing_names = [f.name() for f in provider.fields()]  # Récupère les noms des champs existants
        for field in fields:
            if field.name() not in existing_names:  # Si le champ n'existe pas déjà
                if not provider.addAttributes([field]):
                    raise Exception(f"provider.addAttributes failed for {field.name()}")  # Ajouter le champ à la couche
        existing_layer.updateFields()  # Mettre à jour les champs de la couche

        # Ajouter les nouvelles entités (lignes) au fournisseur
        features =  get_features_to_add(df, existing_layer)

        print_debug_info(debug, 0, "save_to_gpkg_via_qgs Etape 3 fin")

        # Ajouter toutes les entités à la couche
        if not provider.addFeatures(features):
            raise Exception("provider.addFeatures failed")

        log_features(features)
        log_layer(existing_layer, title=layer_name)

        # Mettre à jour les étendues (bornes géographiques) de la couche
        if existing_layer.geometryType() != QgsWkbTypes.NoGeometry:
            existing_layer.updateExtents()
            #    raise Exception("existing_layer.updateExtents failed")

        add_layer_to_map(file_path, uri, layer_name)

        print_debug_info(debug, 3, "save_to_gpkg_via_qgs Etape 4 fin")

        result = True

    else:
        # Étape 4 : La couche n'existe pas - On la crée et on ajoute les données
        
        # Créer une nouvelle couche mémoire (sans géométrie)
        new_layer = QgsVectorLayer("None", layer_name, "memory")
        new_layer_data = new_layer.dataProvider()  # Accéder au fournisseur de données de la nouvelle couche

        # Ajouter les champs (colonnes) à la couche
        new_layer_data.addAttributes(fields)
        new_layer.updateFields()  # Mettre à jour les champs de la nouvelle couche

        # Ajouter les entités (lignes) du DataFrame à la nouvelle couche
        features = get_features_to_add(df, new_layer)

        print_debug_info(debug, 3, "save_to_gpkg_via_qgs Etape 3 bis fin")

        # Ajouter toutes les entités à la couche
        new_layer_data.addFeatures(features)

        # Sauver la couche dans un fichier GeoPackage
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer_name
        options.fileEncoding = "utf-8"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        transform_context = QgsProject.instance().transformContext()

        out_writer = QgsVectorFileWriter.writeAsVectorFormatV3(
            new_layer,
            file_path,
            transform_context,
            options)
        
        result = out_writer[0]
        error = out_writer[1]

        if error != QgsVectorFileWriter.NoError:
            raise RuntimeError(f"Erreur lors de la sauvegarde de la couche : {error}")
            
        """error, context = QgsVectorFileWriter.writeAsVectorFormatV2(
            new_layer,
            file_path,
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsVectorFileWriter.SaveVectorOptions(
                actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteLayer,
                layerName=layer_name,
                driverName="GPKG",
                fileEncoding="utf-8"))"""

        # Recharger et ajouter la couche au projet
        new_layer_uri = f"{file_path}|layername={layer_name}"
        add_layer_to_map(file_path, new_layer_uri, layer_name)

        print_debug_info(debug, 3, "save_to_gpkg_via_qgs Etape 4 bis fin")

    return result

def save_decorator(savior) :

    def inner(function) :

        def wrapper(*args, **kwargs)->None:

            df, file_path, layername = function(*args, **kwargs)
            savior(df, file_path, layername=layername)

            return
        
        return wrapper
    
    return inner

