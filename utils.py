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
    QgsWkbTypes,
    QgsGeometry)

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

    target_path = os.path.normcase(os.path.normpath(filepath))
    #str(filepath).lower().replace("\\", "/")

    layers = QgsProject.instance().mapLayers().values()
    layer_names = []

    for layer in layers:
        
        uri = layer.dataProvider().dataSourceUri().split("|")[0]
        uri_norm = os.path.normcase(os.path.normpath(uri))
        #print_debug_info(1, 0, uri)
        if uri_norm == target_path :
            layer_name = layer.source().split("layername=")[1]
            layer_names.append(layer_name)

    #print_debug_info(1, 0, filepath)

    return layer_names

def list_layers_from_gpkg(filepath: str):

    filepath = os.path.normcase(os.path.normpath(filepath))
    #str(filepath).replace("\\", "/")
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

def parse_layer_to_dataframe(layer)->pd.DataFrame:

    data = []
    for feature in layer.getFeatures():
        attrs = feature.attributes()
        data.append(attrs)

    # Récupérer les noms de champs
    fields = [field.name() for field in layer.fields()]

    df = pd.DataFrame(data, columns=fields)

    return df

def load_layer(filepath: str, layer_name: str):

    uri = f"{filepath}|layername={layer_name}".lower()
    layer = QgsVectorLayer(uri, layer_name, "ogr")

    return layer

def load_layer_as_dataframe(filepath: str, layer_name: str):

    layer = load_layer(filepath, layer_name)
    if not layer.isValid():
        raise ValueError(f"La couche '{layer_name}' n'a pas pu être chargée depuis {filepath}")

    df = parse_layer_to_dataframe(layer)

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

"""def get_features_to_add(df: pd.DataFrame, layer)->list:
    
    print_debug_info(1,0,"get_features_to_add")

    features = []  # Liste des entités à ajouter
    for _, row in df.iterrows():  # Pour chaque ligne du DataFrame
        feat = QgsFeature(layer.fields())  # Créer une nouvelle entité avec les champs de la couche
        for col in df.columns:  # Remplir les valeurs de l'entité avec celles du DataFrame
            if pd.isna(row[col]):  
                pass
            else:
                feat[col] = row[col]  # Assigner la valeur non-NaN  # Remplir les valeurs de l'entité avec celles du DataFrame
        features.append(feat)  # Ajouter l'entité à la liste

    return features"""

def get_features_to_add(df: pd.DataFrame, layer, debug: int=0) -> list:
    print_debug_info(debug, 0, "get_features_to_add")

    features = []
    for _, row in df.iterrows():
        feat = QgsFeature(layer.fields())

        # Ajoute une géométrie vide si la couche en nécessite une
        if layer.geometryType() != QgsWkbTypes.NoGeometry:
            feat.setGeometry(QgsGeometry())  # ou une vraie géométrie si disponible

        for col in df.columns:
            if not pd.isna(row[col]):
                feat.setAttribute(col, row[col])  # plus explicite

        features.append(feat)

    return features

def add_layer_to_map(file_path, uri, layer_name, new: bool=False, debug: int=0)->None:
    print_debug_info(1,0,"add_layer_to_map")

    # Ne pas ajouter de couche nommée "Source"
    if layer_name.strip().lower() == "sources":
        print_debug_info(debug, 0, f"Couche nommée 'Sources' ignorée.")
        return
    
    # Normaliser le chemin et l'URI pour éviter les duplications dues à des encodages différents
    normalized_uri = os.path.abspath(file_path).replace("\\", "/") + f"|layername={layer_name}"

    for lyr in QgsProject.instance().mapLayers().values():
        if isinstance(lyr, QgsVectorLayer):
            lyr_uri = lyr.dataProvider().dataSourceUri()
            # Comparer les chemins absolus, sans encodage spécial
            if lyr_uri == normalized_uri or lyr_uri.replace('%20', ' ') == normalized_uri:
                print_debug_info(debug, 0, f"Couche {layer_name} déjà présente (URI match), ajout ignoré.")
                return
 
    # Recharger la couche depuis le GeoPackage
    layer = QgsVectorLayer(normalized_uri, layer_name, "ogr")
    if not layer.isValid():
        raise Exception(f"Échec de chargement de la couche {layer_name} depuis {file_path}")
    
    # Ajouter au projet
    added = QgsProject.instance().addMapLayer(layer)
    if added is None:
        print_debug_info(1, 0, f"Échec de l’ajout de la couche {layer_name} au projet.")

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

    # Supprimer la colonne 'fid' si elle existe pour éviter les conflits
    if "fid" in df.columns:
        df = df.drop(columns=["fid"])
        print_debug_info(debug, 3, "Colonne 'fid' supprimée du DataFrame.")
    
    # Créer les champs depuis le DataFrame
    fields = QgsFields()
    for col in df.columns:
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
        if isinstance(sample, (int, float)):
            field_type = QVariant.Double if isinstance(sample, float) else QVariant.Int
        else:
            field_type = QVariant.String
        fields.append(QgsField(col, field_type))

    uri = f"{file_path}|layername={layer_name}"

    # Vérifie si la couche est déjà chargée dans QGIS
    layers = QgsProject.instance().mapLayersByName(layer_name)
    if layers:
        print_debug_info(debug, 3, f"Couche {layer_name} déjà dans le projet : mise à jour en mémoire.")
        layer = layers[0]
        provider = layer.dataProvider()

        if not provider.truncate():
            raise Exception("provider.truncate failed")

        existing_names = [f.name() for f in provider.fields()]
        new_fields = [QgsField(f.name(), f.type()) for f in fields if f.name() not in existing_names]

        if new_fields:
            if not provider.addAttributes(new_fields):
                raise Exception("addAttributes failed")
            layer.updateFields()

        features = get_features_to_add(df, layer, debug=debug)
        if not provider.addFeatures(features):
            raise Exception("addFeatures failed")

        layer.updateFields()
        layer.triggerRepaint()
        layer.updateExtents()
        return True

    # Sinon, vérifier si elle existe dans le GPKG
    existing_layer = QgsVectorLayer(uri, layer_name, "ogr")
    if existing_layer.isValid():
        print_debug_info(debug, 3, f"Couche {layer_name} existe sur disque mais pas dans le projet : mise à jour sur disque.")
        provider = existing_layer.dataProvider()

        if not provider.truncate():
            raise Exception("provider.truncate failed")

        existing_names = [f.name() for f in provider.fields()]
        for field in fields:
            if field.name() not in existing_names:
                if not provider.addAttributes([field]):
                    raise Exception(f"provider.addAttributes failed for {field.name()}")
        existing_layer.updateFields()

        features = get_features_to_add(df, existing_layer, debug=debug)
        if not provider.addFeatures(features):
            raise Exception("provider.addFeatures failed")

        existing_layer.updateFields()
        existing_layer.triggerRepaint()
        existing_layer.updateExtents()

        # On l’ajoute au projet
        add_layer_to_map(file_path, uri, layer_name, new=False, debug=debug)
        return True

    # Sinon : création complète
    print_debug_info(debug, 3, f"Couche {layer_name} inexistante, création.")
    new_layer = QgsVectorLayer("None", layer_name, "memory")
    new_layer_data = new_layer.dataProvider()
    new_layer_data.addAttributes(fields)
    new_layer.updateFields()

    features = get_features_to_add(df, new_layer, debug=debug)
    new_layer_data.addFeatures(features)

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "utf-8"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    transform_context = QgsProject.instance().transformContext()
    result_tuple = QgsVectorFileWriter.writeAsVectorFormatV3(
        new_layer, file_path, transform_context, options
    )
    result = result_tuple[0]
    error = result_tuple[1]

    # Recharger la couche depuis le disque après écriture
    uri = f"{file_path}|layername={layer_name}"
    new_layer_uri = f"{file_path}|layername={layer_name}"

    # L'ajouter au projet pour qu'elle soit disponible
    add_layer_to_map(file_path, new_layer_uri, layer_name, new=True, debug=debug)

    print_debug_info(debug, 3, f"save_to_gpkg_via_qgs : couche {layer_name} créée.")
    return result

def save_decorator(savior) :

    def inner(function) :

        def wrapper(*args, **kwargs)->None:

            df, file_path, layername = function(*args, **kwargs)
            savior(df, file_path, layername=layername)

            return
        
        return wrapper
    
    return inner

