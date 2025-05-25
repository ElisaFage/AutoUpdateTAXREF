import os
import requests
import pandas as pd

from .utils import (print_debug_info, save_dataframe, save_to_gpkg_via_qgs,
                    list_layers_from_gpkg, list_layers_from_qgis, load_layer_as_dataframe,
                    save_decorator, parse_layer_to_dataframe, load_layer)

from datetime import date


class SourcesManager():

    required_columns = ["id", "fullCitation"]

    def __init__(self, path: str, new_version: bool=False, year:int=None, debug: int=0):
        """
        Initialisation de l'instance de SourceManager
        
        :param:
        path (str): chemin absolu du fichier Données.gpkg dans le dossier du projet en question
        new_version (bool): booléen indiquant si une nouvelle version de taxref est disponible
        year (int): année pour chercher les sources
        debug (int): niveau de debug  
        """


        self.path = path
        self.new_version = new_version

        self.current_year = year if year != None else date.today().year
        self.last_year = self.current_year - 1
        
        self.debug = debug

        self.data_sources = pd.DataFrame(columns = self.required_columns)
        self.new_sources = pd.DataFrame(columns = self.required_columns)
        self.layer_name = "Sources"

    def set_data_sources(self):
        """
        Récupère les sources associées aux fichier Données.gpkg
        """

        # Si le fichier existe, lire les sources existantes
        if os.path.isfile(self.path):
            print_debug_info(self.debug, 1, f"{self.check_update_status.__name__} : cherche available_layer")

            layer = load_layer(self.path, self.layer_name)
            if layer.isValid():
                # Si la couche "Sources" existe, lire les données dans un DataFrame
                self.data_sources = parse_layer_to_dataframe(layer=layer) 
        else :
            self.data_sources = pd.DataFrame(columns=self.required_columns)

        return

    def get_new_sources_list(self)->list:
        """"
        Renvoie une liste de toutes les fullCitation des nouvelles sources
        """

        text_lines = self.new_sources["fullCitation"].to_list()
        return text_lines

    # Récupère les source de l'année {year}
    def get_sources_from_year(self, year:int)->pd.DataFrame:
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
        # Conversion du json en pd.DataFrame
        df_sources = pd.json_normalize(sources_list, sep = '_')

        # Filtrage des sources contenant des termes spécifiques dans la citation
        listDiscriminant = ["Liste Rouge", "Arrêté", "Directive", "Plan national", "Règlement d'exécution", "ZNIEFF", "ZNIEFFS"]
        df_sources = df_sources[df_sources["fullCitation"].apply(
            lambda fullCitation: any(substring.lower() in fullCitation.lower() for substring in listDiscriminant) if isinstance(fullCitation, str) else False)]
        
        return df_sources

    # Compare les listes de sources
    def check_new_sources(self, my_sources: pd.DataFrame, current_sources: pd.DataFrame)->pd.DataFrame:
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
        ids_absents = current_sources[~current_sources['id'].astype(str).isin(my_sources['id'].astype(str).values)]

        # Retourner les sources absentes sous forme de DataFrame
        return ids_absents

    # Cherche s'il y a des nouvelles sources pour faire une mise à jour
    def check_update_status(self)->pd.DataFrame:
        """
        Vérifie s'il y a des nouvelles sources pour effectuer une mise à jour.

        Cette fonction recherche les nouvelles sources dans un fichier géospatial "Donnees.gpkg"
        et compare les sources existantes avec celles des deux dernières années (l'année en cours et l'année précédente).
        Si de nouvelles sources sont trouvées, elles sont retournées sous forme de DataFrame.

        Args:
            path (str): Le chemin vers le répertoire contenant le fichier "Donnees.gpkg".
            debug (int, optional): Niveau de débogage pour l'affichage des logs (par défaut 0, 1 ou 2).

        Returns:
            pd.DataFrame: Un DataFrame contenant les nouvelles sources à ajouter.
        """

        # Si le fichier existe, lire les sources existantes dans le fichier "Donnees.gpkg"
        self.set_data_sources()
            
        # Récupérer les sources de l'année en cours et de l'année précédente
        currentSources = pd.concat([self.get_sources_from_year(self.current_year),
                                    self.get_sources_from_year(self.last_year)], ignore_index=True)

        # Vérifier les nouvelles sources
        ids_absents = self.check_new_sources(self.data_sources, currentSources)

        # Filtrer les sources absentes
        new_sources = currentSources[currentSources["id"].astype(str).isin(ids_absents["id"].astype(str).values)][self.required_columns].copy()

        print_debug_info(self.debug, 1, f"Les id presents sont : {currentSources["id"].values}")
        print_debug_info(self.debug, 1, f"Les id absents sont : {ids_absents["id"].values}")

        self.new_sources = new_sources

        return

    def set_new_version(self, new_version: bool):
        self.new_version=new_version
        return

    def save_new_sources(self)->None:
        """
        Met à jour et sauvegarde les sources bibliographiques dans un fichier GeoPackage.

        Cette fonction permet d'enregistrer des sources de références associées aux taxons dans une couche nommée "Source" 
        au sein du fichier `Autre.gpkg`. Selon le paramètre `new_version`, elle peut :
            - soit récupérer les sources des deux dernières années,
            - soit fusionner de nouvelles sources fournies en argument avec les sources existantes.

        Parameters
        ----------
        path : str
            Le chemin du dossier contenant (ou devant contenir) le fichier `Autre.gpkg`.
        new_version : bool, optional
            Si `True`, recharge uniquement les sources des deux dernières années et écrase les anciennes.
            Si `False`, ajoute les `newSources` passées en argument aux sources existantes. (par défaut False)
        newSources : pd.DataFrame, optional
            DataFrame contenant les nouvelles sources à ajouter. Doit avoir deux colonnes : ["id", "fullCitation"].
            Ignoré si `new_version=True`. (par défaut un DataFrame vide)

        Returns
        -------
        None
        """


        if self.new_version :
            # Si new_version est activé, on charge uniquement les sources des deux dernières années
            self.data_sources = pd.concat([self.get_sources_from_year(self.current_year),
                                 self.get_sources_from_year(self.last_year)], ignore_index=True)[self.required_columns]

        else :
            # Sinon, on tente de charger les sources déjà présentes dans "Données.gpkg"
            self.set_data_sources()

            # Ajout des nouvelles sources passées en paramètre
            self.data_sources = pd.concat([self.data_sources, self.new_sources], ignore_index=True)
        
        save_to_gpkg_via_qgs(self.data_sources, self.path, self.layer_name)

        return 
    
    def is_new_sources(self):
        """
        Verifie s'il y a des nouvelles sources dans new_sources

        :return:
        bool : True si new_sources n'est pas vide
               False si new_sources est vide
        """

        return not self.new_sources.empty