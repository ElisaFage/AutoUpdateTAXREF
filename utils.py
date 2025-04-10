from qgis.core import QgsMessageLog, Qgis
from datetime import datetime
import os

def print_debug_info(debug_level, debug_threshold, msg):

    if debug_level > debug_threshold :
        now = datetime.now()
        QgsMessageLog.logMessage(msg+f" ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    return

def get_file_save_path(path, taxon_title):
    
    if taxon_title == "Flore":
        file_save_path = os.path.join(path, f"{taxon_title}.gpkg")
    else : 
        file_save_path = os.path.join(path, f"Faune.gpkg")

    return file_save_path