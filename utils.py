from qgis.core import (QgsMessageLog, Qgis,
                       QgsProject, QgsVectorLayer)
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
        QgsMessageLog.logMessage(name+msg+f" ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    return

def time_decorator(function):

    def wrapper(*args, **kwargs):

        print_debug_info(f"Début de {function.__name__}")
        rv = function(*args, **kwargs)
        print_debug_info(f"Fin de {function.__name__}")

        return rv
    
    return wrapper

def list_layers_from_gpkg(filepath: str):

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

def load_layer_as_dataframe(filepath: str, layer_name: str):
    uri = f"{filepath}|layername={layer_name}"
    layer = QgsVectorLayer(uri.lower(), layer_name, "ogr")
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
                   path: str,
                   layer: str)->None:
    
    # Conversion en GeoDataFrame avant sauvegarde
    gdf = gpd.GeoDataFrame(df)

    # Sauvegarde dans le fichier GeoPackage sous la couche {layer}
    gdf.to_file(path, layer=layer)

    return
