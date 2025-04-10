import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np

from urllib.request import urlopen, urlretrieve


# Récupérer la version actuelle du fichier local
def recup_my_version(path: str):

    taxonTitles = ["Flore", "Amphibiens", "Reptiles", "Oiseaux", "Mammifères", "Lépidoptères", "Odonates", "Coléoptères", "Orthoptères"]
    
    all_versions = []
    for title in taxonTitles:
        if title == "Flore":
            file_path = os.path.join(path, f"{title}.gpkg")
        else :
            file_path = os.path.join(path, f"Faune.gpkg")
        if not os.path.isfile(file_path):
            all_versions.append(-1)
        else :
            data = gpd.read_file(file_path, layer=f"Liste {title}")
            all_versions.append(np.min(data["VERSION"].values) if "VERSION" in data.columns else -1)
            
    return np.min(all_versions)

# Récupérer la version actuelle du TAXREF depuis l'API
def recup_current_version():
    url = "https://taxref.mnhn.fr/api/taxrefVersions/current"
    response = urlopen(url)
    data_json = json.loads(response.read()) # Lire les données JSON

    my_curent_ver = data_json["id"] # Extraire la version actuelle
    return my_curent_ver
