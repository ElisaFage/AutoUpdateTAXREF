import os
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

from qgis.core import QgsMessageLog, Qgis

from datetime import date

# Récupère les source de l'année {year}
def GetSourcesFromYear(year: int)->pd.DataFrame:

    url = f"https://taxref.mnhn.fr/api/sources/findByTerm/{year}"

    response = requests.get(url)
    data_json = response.json()

    # Extraire et normaliser les données des sources
    sources_list = data_json.get('_embedded', {}).get('bibliography', [])
    df_sources = pd.json_normalize(sources_list, sep = '_')
    #df_sources = df_sources[df_sources["year"] == year]

    # Fonction de filtrage
    listDiscriminant = ["Liste Rouge", "Arrêté", "Directive", "Plan national", "Règlement d'exécution", "ZNIEFF", "ZNIEFFS"]
    df_sources = df_sources[df_sources["fullCitation"].apply(
        lambda x: any(substring.lower() in x.lower() for substring in listDiscriminant) if isinstance(x, str) else False)]
    
    return df_sources

# Compare les listes de sources
def CheckNewSources(mySources: pd.DataFrame, currentSources: pd.DataFrame, file_path: str)->pd.DataFrame:

    # Trouver les éléments absents
    ids_absents = currentSources[~currentSources['id'].astype(str).isin(mySources['id'].astype(str).values)]

    """if not ids_absents.empty :
        # Ajouter les ids absents à mySourcesId
        newSourcesId = pd.concat([mySourcesId, ids_absents], ignore_index=True)
        newSources_gdf = gpd.GeoDataFrame(newSourcesId)
        newSources_gdf.to_file(file_path)
        return True"""

    return ids_absents

# Chreche s'il y a de nouvelles source pour faire une mise à jour
def CheckUpdateStatus(path: str, debug: int=0)->pd.DataFrame:

    current_year = date.today().year

    file_path = os.path.join(path, "Autre.gpkg")
    if os.path.isfile(file_path):
        if debug > 1 :
            QgsMessageLog.logMessage(f"SaveRegionStatus : cherche available_layer", "AutoUpdateTAXREF", level=Qgis.Info)
        available_layers = gpd.list_layers(file_path)
        if "Source" in available_layers["name"].values :
            mySources = pd.DataFrame(gpd.read_file(file_path, layer="Source"))
        else :
            mySources = pd.DataFrame(columns = ["id", "fullCitation"])
    else : 
        mySources = pd.DataFrame(columns=["id", "fullCitation"])
        
    currentSources = pd.concat([GetSourcesFromYear(current_year),
                                GetSourcesFromYear(current_year-1)], ignore_index=True)

    ids_absents = CheckNewSources(mySources, currentSources, file_path)

    newSources = currentSources[currentSources["id"].astype(str).isin(ids_absents["id"].astype(str).values)][["id", "fullCitation"]].copy()

    if debug > 1 :
        QgsMessageLog.logMessage(f"Les id absent sont : {ids_absents["id"].values}", "AutoUpdateTAXREF", level=Qgis.Info)

    return newSources