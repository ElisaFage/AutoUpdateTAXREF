import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np

from urllib.request import urlopen
from .utils import print_debug_info, get_file_save_path


class VersionManager():

    def __init__(self, path:str, taxon_titles: list[str], debug: int=0):
        
        self.taxon_titles = taxon_titles
        self.path = path
        self.debug = debug
        self.data_version = -1
        self.current_version = -1

        self.url = "https://taxref.mnhn.fr/api/taxrefVersions/current"

    # Récupérer la version actuelle du fichier local
    def set_data_version(self):
        """
        Récupère la version minimale d'un ensemble de fichiers de données géospatiales pour différentes catégories de taxons.

        Cette fonction parcourt une liste de catégories de taxons et vérifie pour chaque catégorie si le fichier correspondant
        existe dans le répertoire spécifié. Si un fichier est trouvé, la version minimale est extraite de la colonne "VERSION".
        Si le fichier est absent ou si la colonne "VERSION" est manquante, une valeur de -1 est ajoutée.
        """
        
        # Liste pour stocker les versions extraites
        all_versions = []

        # Parcours de chaque catégorie de taxon
        for title in self.taxon_titles:

            # Définir le chemin du fichier en fonction du titre du taxon
            file_path = get_file_save_path(self.path, title)

            # Si le fichier n'existe pas, ajouter -1 à la liste des versions
            if os.path.isfile(file_path) :
                layer_name = f"Liste {title}"
                available_layers = gpd.list_layers(self.path)
                # Lire le fichier géospatial et vérifier la colonne "VERSION"
                if layer_name in available_layers["name"].values:
                    data = gpd.read_file(file_path, layer=layer_name)
                    # Ajouter la version minimale ou -1 si la colonne "VERSION" est absente
                    all_versions.append(np.min(data["VERSION"].values) if "VERSION" in data.columns else -1)
                
        # Retourner la version minimale parmi toutes celles extraites
        self.data_version = np.min(all_versions)

        print_debug_info(self.debug, 0, f"Ma version: {self.data_version}")

        return

    # Récupérer la version actuelle du TAXREF depuis l'API
    def set_current_version(self):
        """
        Récupère l'identifiant de la version actuelle de TAXREF via l'API officielle.
        """

        # Effectue une requête HTTP vers l'API pour obtenir les métadonnées de la version courante
        response = urlopen(self.url)
        # Lit et décode la réponse JSON
        data_json = json.loads(response.read()) # Lire les données JSON

        # Extrait l'identifiant de la version actuelle depuis le champ "id"
        self.current_version = data_json["id"]
        print_debug_info(self.debug, 0, f"Dernière version: {self.current_version}")

        return
