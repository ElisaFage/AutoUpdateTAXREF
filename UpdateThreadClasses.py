import os
import requests
import tempfile
from functools import reduce
from typing import List

import pandas as pd
import geopandas as gpd

from PyQt5.QtCore import QThread, pyqtSignal

from .UpdateTAXREF import get_download_url, tri_taxon_taxref
from .UpdateStatus import run_download_status, save_global_status
from .utils import print_debug_info
from .taxongroupe import TaxonGroupe
from .statustype import StatusType, STATUS_TYPES

class GetURLThread(QThread):
    """
    Classe qui récupère l'URL de téléchargement d'une version spécifique en arrière-plan.

    Attributs :
        finished (pyqtSignal): Signal émis une fois que l'URL de téléchargement est obtenue.
        version (str): Version pour laquelle l'URL de téléchargement est récupérée.
    """
    # Signal pour indiquer la fin du processus de récupération de l'URL
    finished = pyqtSignal(str) # Signal pour indiquer la fin du téléchargement

    def __init__(self, version: int):
        """
        Initialise le thread pour récupérer l'URL de téléchargement pour la version spécifiée.

        Args:
            version (str): La version pour laquelle l'URL doit être récupérée.
        """
        super().__init__()
        self.version = version

    def run(self):
        """
        Lance le processus pour obtenir l'URL de téléchargement pour la version donnée.

        Cette méthode est exécutée dans un thread séparé. Elle appelle la fonction
        `get_download_url` pour récupérer l'URL de téléchargement, puis émet un signal 
        avec l'URL obtenue.
        """
        # Récupérer l'URL de téléchargement pour la version spécifiée
        url = get_download_url(self.version)
        
        # Émettre le signal 'finished' avec l'URL obtenue
        self.finished.emit(url)

class DownloadTaxrefThread(QThread):
    """
    Classe qui gère le téléchargement d'un fichier à partir d'une URL en arrière-plan.

    Attributs :
        progress (pyqtSignal): Signal émis pour transmettre la progression du téléchargement.
        finished (pyqtSignal): Signal émis une fois que le téléchargement est terminé.
        url (str): URL du fichier à télécharger.
    """
    
    # Signal pour transmettre la progression
    progress = pyqtSignal(int) 
    # Signal pour indiquer la fin du téléchargement
    finished = pyqtSignal(str)  

    def __init__(self, url: str):
        """
        Initialise le thread de téléchargement avec l'URL du fichier à télécharger.

        Args:
            url (str): L'URL du fichier à télécharger.
        """
        super().__init__()
        self.url = url

    def run(self):
        """
        Lance le téléchargement du fichier depuis l'URL spécifiée.

        Cette méthode est exécutée dans un thread séparé. Elle télécharge le fichier par morceaux
        et émet des signaux pour informer de la progression et de la fin du téléchargement.
        Un fichier temporaire est créé pour stocker les données téléchargées.
        """
        # Envoi d'une requête GET pour télécharger le fichier
        response = requests.get(self.url, stream=True)
        # Récupérer la taille totale du fichier à partir de l'en-tête 'content-length'
        total_length = int(response.headers.get('content-length', 0))
        
        # Vérifier si la requête a été réalisée avec succès
        response.raise_for_status()

        # Créer un fichier temporaire pour stocker le fichier ZIP téléchargé
        with tempfile.NamedTemporaryFile(delete=False) as temp_zip:
            downloaded_size = 0
            # Télécharger le fichier par morceaux de 4096 octets
            for data in response.iter_content(chunk_size=4096):
                # Écrire les données dans le fichier temporaire
                temp_zip.write(data)
                # Mettre à jour la taille téléchargée
                downloaded_size += len(data)

                # Calculer le pourcentage de progression
                progress_percentage = int(downloaded_size * 100 / total_length)
                self.progress.emit(progress_percentage)  # Émet le signal de progression

            # Obtenir le chemin du fichier temporaire
            temp_zip_path = temp_zip.name

        # Émettre le signal 'finished' avec le chemin du fichier temporaire
        self.finished.emit(temp_zip_path)  # Émet le signal de fin

class SaveTaxrefThread(QThread):
    """
    Une classe QThread pour trier les taxon de TAXREF après leur téléchargement

    Attributes:
        finished (pyqtSignal): Signal emis quand le thread fini son execution
        temp_zip_path (str): Chemin du fichier ZIP temporaire contenant les données de TAXREF
        version (str): Version de TAXREF
        taxons (list): Liste d'objet TaxonGroupe.
        save_path (str): Chemin de sauvegarde des données après les tris.
        synonyme (bool): Pour garder les taxon avec CD_NOM != CD_REF
    """

    finished = pyqtSignal()
    
    def __init__(self, temp_zip_path, version, 
                 taxons: List[TaxonGroupe],
                 save_path, synonyme:bool=False):
        """
        Initialise le SaveTaxrefThread avec les paramètres donnés.

        Args:
            temp_zip_path (str): Chemin du fichier ZIP temporaire contenant les données de TAXREF
            version (str): Version de TAXREF
            taxons (list): Liste d'objet TaxonGroupe.
            save_path (str): Chemin de sauvegarde des données après les tris.
            synonyme (bool): Pour garder les taxon avec CD_NOM != CD_REF
        """

        super().__init__()
        self.version = version
        self.temp_zip_path = temp_zip_path
        self.taxons = taxons
        self.save_path = save_path
        self.synonyme = synonyme

    def run(self):
        """
        Runs the process to save the taxon data after downloading.

        This method is executed in a separate thread. It calls the 
        on_DownloadComplete function with the parameters passed to the 
        thread, processes the data, and saves it to the specified path.

        The `finished` signal is emitted once the saving process is complete.
        """
        # Process the downloaded data and save it to the specified path
        tri_taxon_taxref(self.temp_zip_path,
                         self.version,
                         self.taxons,
                         self.save_path,
                         self.synonyme)
        # Emit the 'finished' signal to notify that the process is complete
        self.finished.emit()

class GetStatusThread(QThread):
    """
    Thread pour télécharger, fusionner et sauvegarder les statuts régionaux et nationaux.

    Cette classe étend `QThread` et est utilisée pour effectuer en arrière-plan des opérations 
    de téléchargement de fichiers GeoPackage, fusionner les données sur les statuts, 
    puis sauvegarder les résultats en différents fichiers de sortie.

    Attributes:
        progress (pyqtSignal): Signal émis pour indiquer l'avancement du processus de téléchargement.
        finished (pyqtSignal): Signal émis lorsque le thread a terminé son exécution.
        path (str): Le chemin où les fichiers GeoPackage doivent être sauvegardés.
        list_status_id (list): Liste des identifiants de statuts à traiter.
        save_excel (bool): Si vrai, les résultats sont sauvegardés dans un fichier Excel.
        folder_excel (str): Dossier de destination pour le fichier Excel.
        taxonTitles (list): Liste des titres des taxons à traiter.
        debug (int): Niveau de débogage (0: pas de débogage, 1: débogage faible, 2: débogage élevé).
    """

    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, path: str,
                 taxons:List[TaxonGroupe],
                 status_types: List[StatusType],
                 save_excel: bool,
                 folder_excel: str,
                 debug: int=0):
        """
        Initialise le thread pour récupérer les statuts et effectuer le téléchargement et la sauvegarde.

        Args:
            path (str): Le chemin où les fichiers doivent être sauvegardés.
            taxons (list[TaxonGroupe]): Liste des titres des taxons à traiter.
            status_types (list[StatusType]): Liste des identifiants de statuts à récupérer.
            save_excel (bool): Si vrai, les résultats sont sauvegardés dans un fichier Excel.
            folder_excel (str): Le dossier où enregistrer le fichier Excel.
            debug (int, optional): Niveau de débogage (par défaut à 0).
        """

        super().__init__()
        self.path = path
        self.status_types = status_types
        self.save_excel = save_excel
        self.folder_excel = folder_excel
        self.taxons = taxons
        
        self.debug = debug

        self.length_status = []
        self.listStatusUpdated = []
        self.global_progress = 0

    def run(self):
        """
        Exécute le téléchargement des données, la fusion des statuts et la sauvegarde des résultats.

        Cette méthode est exécutée dans un thread séparé. Elle télécharge les fichiers, les fusionne, 
        puis les sauvegarde dans les formats appropriés (GeoPackage et/ou Excel).
        Un signal `progress` est émis pour indiquer l'avancement global du processus.
        """

        # Initialiser les chemins de fichiers temporaires
        self.pathes_temp_file = []
        for status_type in self.status_types:
            
            print_debug_info(self.debug, 0, f"Pour {status_type.type_id}, début de run_doawnload")

            # Exécute le téléchargement des fichiers pour chaque status_id
            self.pathes_temp_file += run_download_status(status_type, self.taxons,
                                                  self.path,
                                                  self.save_excel, self.folder_excel,
                                                  debug=self.debug)

            print_debug_info(self.debug, 0, f"Pour {status_type.type_id}, fin de run_doawnload")

            # Met à jour l'avancement global
            self.global_progress += 100* 1/len(self.status_types)
            self.progress.emit(int(round(self.global_progress)))
        
        # Fusionner et sauvegarder les résultats
        self.concat_and_save()

        # Émet le signal de fin de processus
        self.finished.emit()

    def concat_and_save(self):
        """
        Fusionne les DataFrames pour chaque taxon et sauvegarde les résultats.

        Cette méthode fusionne les données par région et CD_REF pour les statuts régionaux, 
        puis par CD_REF pour les statuts nationaux. Les résultats sont sauvegardés dans des fichiers 
        GeoPackage ou Excel, selon les paramètres de la classe.
        """

        print_debug_info(self.debug, 0, f"Start of savings")

        # Fusionner tous les DataFrames sur les colonnes "Région" et "CD_REF"
        national_status = [status for status in STATUS_TYPES if status.is_national()]
        #("DH", "DO", "LRN", "PN", "PNA", "PAPNAT")
        for taxon in self.taxons:
            
            print_debug_info(self.debug, 0, f"Start of saving {taxon.title} on regional")
            # Traitement des statuts non nationaux
            # # Verifier que des statuts non-nationaux sont mis à jour
            if set(self.status_types) - (set(self.status_types) & set(national_status)) :

                col_to_merge = ["Région", "CD_REF"]

                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{taxon.title}_{status.type_id}.gpkg")))
                    for status in self.status_types if not status.is_national()]

                # status.type_id for status in self.statuses if status.is_regional()
                # Fusionner les DataFrames sur la colonne "CD_REF"
                status_updated_array = reduce(
                    lambda left, right: pd.merge(left, right, on=col_to_merge, how="outer"), df_to_reduce)
                
                print_debug_info(self.debug, 0, f"Start of saving {taxon.title} on regional")
                # Sauvegarde les nouvelles colonnes
                save_global_status(status_updated_array,
                                self.path,
                                taxon.title,
                                save_type="regional",
                                debug=self.debug)
            

            # Traitement des statuts nationaux
            if set(self.status_types) & set(national_status):

                col_to_merge = ["CD_REF"]

                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{taxon.title}_{status.type_id}.gpkg")))
                    for status in self.status_types if status.is_national()]
            
                # Fusionner les DataFrames sur la colonne "CD_REF"
                status_updated_array = reduce(
                    lambda left, right: pd.merge(left, right, on=col_to_merge, how="outer"), df_to_reduce)
                
                print_debug_info(self.debug, 0, f"Start of saving {taxon.title} on national")
                # Sauvegarde les nouvelles colonnes
                save_global_status(status_updated_array,
                                self.path,
                                taxon.title,
                                save_type="national",
                                debug=self.debug)

            print_debug_info(self.debug, 0, f"End of saving {taxon.title}")
            
            # Supprimer les fichiers temporaires pour chaque status_id
            for status in self.status_types :
                # Supprime les fichiers temporaires
                os.remove(os.path.join(self.path, f"{taxon.title}_{status.type_id}.gpkg"))

        print_debug_info(self.debug, 0, f"End of savings")

        return

    def termination_process(self):
        """
        Supprime les fichiers temporaires et termine le thread.

        Cette méthode est appelée lorsque le thread doit être arrêté avant son terme normal. 
        Elle supprime les fichiers temporaires générés pendant le processus.
        """

        # Supprime les fichier temporaire
        if self.pathes_temp_file :
            for path in self.pathes_temp_file:
                os.remove(path)
        
        # Termine le thread de force
        self.terminate()