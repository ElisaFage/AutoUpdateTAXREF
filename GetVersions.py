import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np

from urllib.request import urlopen
from .utils import (print_debug_info, get_file_save_path,
                    list_layers_from_gpkg, list_layers_from_qgis, 
                    load_layer_as_dataframe)
from .taxongroupe import TaxonGroupe


class VersionManager():

    def __init__(self, path:str, taxons: list[TaxonGroupe], debug: int=0):
        
        self.taxons = taxons
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

        # Définir le chemin du fichier en fonction du titre du taxon
        file_path = get_file_save_path(self.path)
        
        if os.path.isfile(file_path) :
            available_layers = list_layers_from_qgis(file_path)
            print_debug_info(self.debug, 1, f"Les couches sont : {available_layers}")

            # Parcours de chaque catégorie de taxon
            for taxon in self.taxons:
                layer_name = f"Liste {taxon.title}"
                #gpd.list_layers(self.path)
                
                if layer_name in available_layers: #["name"].values:
                    data = load_layer_as_dataframe(file_path, layer_name=layer_name)
                    #gpd.read_file(file_path, layer=layer_name)
                    # Ajouter la version minimale ou -1 si la colonne "VERSION" est absente
                    if "VERSION" in data.columns and not data["VERSION"].empty:
                        # Nettoyer les valeurs potentiellement invalides (ex : QVariant)
                        cleaned = data["VERSION"].apply(lambda x: str(x) if x is not None else None)
                        # Convertir en numérique avec gestion des erreurs
                        version_series = pd.to_numeric(cleaned, errors="coerce")
                        # Remplacer les NaN par -1 (ou une autre valeur selon votre logique)
                        version_series = version_series.fillna(-1)
                        # Convertir vers un type entier tolérant les NaN
                        version_series = version_series.astype("Int64")  # type nullable de pandas
                        all_versions.append(version_series.min() if not version_series.empty else -1)
                    else:
                        all_versions.append(-1)
            
        # Retourner la version minimale parmi toutes celles extraites
        if all_versions != []:
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
