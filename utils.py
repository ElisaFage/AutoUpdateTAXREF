from qgis.core import QgsMessageLog, Qgis
from datetime import datetime
import os

import pandas as pd
import geopandas as gpd

def print_debug_info(debug_level: int,
                     debug_threshold: int,
                     msg: str,
                     name: str="")->None:

    if debug_level > debug_threshold :
        now = datetime.now()
        QgsMessageLog.logMessage(name+msg+f" ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    return

def get_file_save_path(path: str,
                       taxon_title: str)->str:
    
    file_save_path = os.path.join(path, "Statuts.gpkg")

    return file_save_path

def save_dataframe(df: pd.DataFrame,
                   path: str,
                   layer: str)->None:
    
    # Conversion en GeoDataFrame avant sauvegarde
    gdf = gpd.GeoDataFrame(df)
    
    # Sauvegarde dans le fichier GeoPackage sous la couche {layer}
    gdf.to_file(path, layer=layer)

    return
