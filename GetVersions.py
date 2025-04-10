import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np

from urllib.request import urlopen


# Récupérer la version actuelle du fichier local
def recup_my_version(path: str):
    """
    Récupère la version minimale d'un ensemble de fichiers de données géospatiales pour différentes catégories de taxons.

    Cette fonction parcourt une liste de catégories de taxons et vérifie pour chaque catégorie si le fichier correspondant
    existe dans le répertoire spécifié. Si un fichier est trouvé, la version minimale est extraite de la colonne "VERSION".
    Si le fichier est absent ou si la colonne "VERSION" est manquante, une valeur de -1 est ajoutée.

    Args:
        path (str): Le chemin vers le répertoire contenant les fichiers .gpkg.

    Returns:
        int: La version minimale parmi toutes les versions extraites des fichiers.
    """

    # Liste des titres des taxons à vérifier
    taxonTitles = ["Flore", "Amphibiens", "Reptiles", "Oiseaux", "Mammifères", "Lépidoptères", "Odonates", "Coléoptères", "Orthoptères"]
    
    # Liste pour stocker les versions extraites
    all_versions = []

    # Parcours de chaque catégorie de taxon
    for title in taxonTitles:

        # Définir le chemin du fichier en fonction du titre du taxon
        if title == "Flore":
            file_path = os.path.join(path, f"{title}.gpkg")
        else :
            file_path = os.path.join(path, f"Faune.gpkg")

        # Si le fichier n'existe pas, ajouter -1 à la liste des versions
        if not os.path.isfile(file_path):
            all_versions.append(-1)
        else :
            # Lire le fichier géospatial et vérifier la colonne "VERSION"
            data = gpd.read_file(file_path, layer=f"Liste {title}")
            # Ajouter la version minimale ou -1 si la colonne "VERSION" est absente
            all_versions.append(np.min(data["VERSION"].values) if "VERSION" in data.columns else -1)
            
    # Retourner la version minimale parmi toutes celles extraites
    return np.min(all_versions)

# Récupérer la version actuelle du TAXREF depuis l'API
def recup_current_version():
    """
    Récupère l'identifiant de la version actuelle de TAXREF via l'API officielle.

    Returns:
        str: Identifiant de la version actuelle de TAXREF.
    """
    
    url = "https://taxref.mnhn.fr/api/taxrefVersions/current"

    # Effectue une requête HTTP vers l'API pour obtenir les métadonnées de la version courante
    response = urlopen(url)
    # Lit et décode la réponse JSON
    data_json = json.loads(response.read()) # Lire les données JSON

    # Extrait l'identifiant de la version actuelle depuis le champ "id"
    my_curent_ver = data_json["id"]

    return my_curent_ver
