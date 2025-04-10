import os
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

from qgis.core import QgsMessageLog, Qgis

from datetime import date

# Récupère les source de l'année {year}
def get_sources_from_year(year: int)->pd.DataFrame:
    """
    Récupère les sources bibliographiques pour un certain année à partir de l'API TAXREF.

    Cette fonction interroge l'API TAXREF pour obtenir les sources bibliographiques
    associées à une année spécifique. Elle filtre ensuite les sources en fonction
    de termes discriminants dans la citation complète de la source.

    Args:
        year (int): L'année pour laquelle les sources doivent être récupérées.

    Returns:
        pd.DataFrame: Un DataFrame contenant les sources filtrées associées à l'année spécifiée.
    """

    # URL de l'API TAXREF pour récupérer les sources par année
    url = f"https://taxref.mnhn.fr/api/sources/findByTerm/{year}"

    # Envoi de la requête GET à l'API et récupération des données JSON
    response = requests.get(url)
    data_json = response.json()

    # Extraire et normaliser les données des sources bibliographiques
    sources_list = data_json.get('_embedded', {}).get('bibliography', [])
    df_sources = pd.json_normalize(sources_list, sep = '_')

    # Filtrage des sources contenant des termes spécifiques dans la citation
    listDiscriminant = ["Liste Rouge", "Arrêté", "Directive", "Plan national", "Règlement d'exécution", "ZNIEFF", "ZNIEFFS"]
    df_sources = df_sources[df_sources["fullCitation"].apply(
        lambda x: any(substring.lower() in x.lower() for substring in listDiscriminant) if isinstance(x, str) else False)]
    
    return df_sources

# Compare les listes de sources
def check_new_sources(mySources: pd.DataFrame, currentSources: pd.DataFrame, file_path: str)->pd.DataFrame:
    """
    Vérifie les nouvelles sources en comparant deux DataFrames de sources bibliographiques.

    Cette fonction compare deux DataFrames (mySources et currentSources) pour identifier
    les sources présentes dans `currentSources` mais absentes dans `mySources` en utilisant l'ID.
    Si des sources sont identifiées, elles sont retournées sous forme d'un DataFrame.

    Args:
        mySources (pd.DataFrame): DataFrame contenant les sources de l'utilisateur.
        currentSources (pd.DataFrame): DataFrame contenant les sources actuelles.
        file_path (str): Chemin de fichier où les nouvelles sources seront sauvegardées (actuellement non utilisé).

    Returns:
        pd.DataFrame: Un DataFrame contenant les sources présentes dans `currentSources` mais absentes de `mySources`.
    """

    # Trouver les éléments de `currentSources` dont l'ID est absent de `mySources`
    ids_absents = currentSources[~currentSources['id'].astype(str).isin(mySources['id'].astype(str).values)]

    # Retourner les sources absentes sous forme de DataFrame
    return ids_absents

# Chreche s'il y a de nouvelles source pour faire une mise à jour
def check_update_status(path: str, debug: int=0)->pd.DataFrame:
    """
    Vérifie s'il y a des nouvelles sources pour effectuer une mise à jour.

    Cette fonction recherche les nouvelles sources dans un fichier géospatial "Autre.gpkg"
    et compare les sources existantes avec celles des deux dernières années (l'année en cours et l'année précédente).
    Si de nouvelles sources sont trouvées, elles sont retournées sous forme de DataFrame.

    Args:
        path (str): Le chemin vers le répertoire contenant le fichier "Autre.gpkg".
        debug (int, optional): Niveau de débogage pour l'affichage des logs (par défaut 0, 1 ou 2).

    Returns:
        pd.DataFrame: Un DataFrame contenant les nouvelles sources à ajouter.
    """

    # Obtenir l'année en cours
    current_year = date.today().year

    # Définir le chemin du fichier contenant les sources
    file_path = os.path.join(path, "Autre.gpkg")

    # Si le fichier existe, lire les sources existantes
    if os.path.isfile(file_path):
        if debug > 1 :
            QgsMessageLog.logMessage(f"SaveRegionStatus : cherche available_layer", "AutoUpdateTAXREF", level=Qgis.Info)

        # Liste des couches disponibles dans le fichier GPKG
        available_layers = gpd.list_layers(file_path)

        # Si la couche "Source" existe, lire les données dans un DataFrame
        if "Source" in available_layers["name"].values :
            mySources = pd.DataFrame(gpd.read_file(file_path, layer="Source"))
        else :
            # Si la couche "Source" n'existe pas, créer un DataFrame vide avec les colonnes appropriées
            mySources = pd.DataFrame(columns = ["id", "fullCitation"])
    else :
        # Si le fichier n'existe pas, créer un DataFrame vide
        mySources = pd.DataFrame(columns=["id", "fullCitation"])
        
    # Récupérer les sources de l'année en cours et de l'année précédente
    currentSources = pd.concat([get_sources_from_year(current_year),
                                get_sources_from_year(current_year-1)], ignore_index=True)

    # Vérifier les nouvelles sources
    ids_absents = check_new_sources(mySources, currentSources, file_path)

    # Filtrer les sources absentes
    newSources = currentSources[currentSources["id"].astype(str).isin(ids_absents["id"].astype(str).values)][["id", "fullCitation"]].copy()

    if debug > 1 :
        QgsMessageLog.logMessage(f"Les id absent sont : {ids_absents["id"].values}", "AutoUpdateTAXREF", level=Qgis.Info)

    return newSources