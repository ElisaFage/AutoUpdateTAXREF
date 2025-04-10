import os
from datetime import datetime
import requests
import tempfile
from functools import reduce

import pandas as pd
import geopandas as gpd

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsMessageLog, Qgis

from .UpdateTAXREF import get_download_url, on_DownloadComplete
from .UpdateStatus import run_download, save_regional_status, save_national_status, save_new_sources

class GetURLThread(QThread):
    """
    Classe qui récupère l'URL de téléchargement d'une version spécifique en arrière-plan.

    Attributs :
        finished (pyqtSignal): Signal émis une fois que l'URL de téléchargement est obtenue.
        version (str): Version pour laquelle l'URL de téléchargement est récupérée.
    """
    # Signal pour indiquer la fin du processus de récupération de l'URL
    finished = pyqtSignal(str) # Signal pour indiquer la fin du téléchargement

    def __init__(self, version):
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

class DownloadThread(QThread):
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

    def __init__(self, url):
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
    A QThread class that handles the asynchronous saving of taxon data 
    after a download is completed.

    Attributes:
        finished (pyqtSignal): Signal emitted when the thread finishes its execution.
        version (str): The version of the data to be saved.
        temp_zip_path (str): The path to the temporary ZIP file containing the taxon data.
        taxonTitle (str): The title of the taxon data (e.g., 'Flora', 'Fauna').
        taxon_regne (str): The kingdom classification of the taxon data (e.g., 'Plantae', 'Animalia').
        taxon_groupe_1 (str): The first group of the taxon data classification.
        taxon_groupe_2 (str): The second group of the taxon data classification.
        taxon_groupe_3 (str): The third group of the taxon data classification.
        taxon_famille (str): The family classification of the taxon data.
        save_path (str): The path where the processed data will be saved.
        synonyme (bool): Whether to include synonyms in the data processing. Default is False.
    """

    finished = pyqtSignal()
    
    def __init__(self, temp_zip_path, version, 
                 taxon_title, taxon_regne,
                 taxon_groupe_1, taxon_groupe_2,
                 taxon_groupe_3, taxon_famille,
                 save_path, synonyme:bool=False):
        """
        Initializes the SaveTaxrefThread with the provided parameters.

        Args:
            temp_zip_path (str): Path to the temporary ZIP file containing the taxon data.
            version (str): Version of the data to be saved.
            taxon_title (str): Title of the taxon data (e.g., 'Flora', 'Fauna').
            taxon_regne (str): Kingdom classification of the taxon data (e.g., 'Plantae', 'Animalia').
            taxon_groupe_1 (str): First group of the taxon data classification.
            taxon_groupe_2 (str): Second group of the taxon data classification.
            taxon_groupe_3 (str): Third group of the taxon data classification.
            taxon_famille (str): Family classification of the taxon data.
            save_path (str): Path where the processed data will be saved.
            synonyme (bool): Whether to include synonyms in the data processing (default is False).
        """

        super().__init__()
        self.version = version
        self.temp_zip_path = temp_zip_path
        self.taxonTitle = taxon_title
        self.taxon_regne = taxon_regne
        self.taxon_groupe_1 = taxon_groupe_1
        self.taxon_groupe_2 = taxon_groupe_2
        self.taxon_groupe_3 = taxon_groupe_3
        self.taxon_famille = taxon_famille
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
        on_DownloadComplete(self.temp_zip_path, self.version,
                            self.taxonTitle, self.taxon_regne,
                            self.taxon_groupe_1, self.taxon_groupe_2,
                            self.taxon_groupe_3, self.taxon_famille,
                            self.save_path, self.synonyme)
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

    def __init__(self, path: str, taxonTitles: list, status_ids: list, save_excel, folder_excel, debug: int=0):
        """
        Initialise le thread pour récupérer les statuts et effectuer le téléchargement et la sauvegarde.

        Args:
            path (str): Le chemin où les fichiers doivent être sauvegardés.
            taxonTitles (list): Liste des titres des taxons à traiter.
            status_ids (list): Liste des identifiants de statuts à récupérer.
            save_excel (bool): Si vrai, les résultats sont sauvegardés dans un fichier Excel.
            folder_excel (str): Le dossier où enregistrer le fichier Excel.
            debug (int, optional): Niveau de débogage (par défaut à 0).
        """

        super().__init__()
        self.path = path
        self.list_status_id = status_ids
        self.save_excel = save_excel
        self.folder_excel = folder_excel
        self.taxonTitles = taxonTitles
        
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
        self.step = 0
        status_id = self.list_status_id[self.step]

        self.pathes_temp_file = []

        for status_id in self.list_status_id:
            if self.debug > 0 :
                now = datetime.now()
                QgsMessageLog.logMessage(f"Pour {status_id}, début de run_doawnload ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

            # Exécute le téléchargement des fichiers pour chaque status_id
            self.pathes_temp_file += run_download(status_id, self.taxonTitles,
                                                  self.path,
                                                  self.save_excel, self.folder_excel,
                                                  debug=self.debug)
            
            if self.debug > 0 :
                now = datetime.now()
                QgsMessageLog.logMessage(f"Pour {status_id}, fin de run_doawnload ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

            # Met à jour l'avancement global
            self.global_progress += 100* 1/len(self.list_status_id)
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

        if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of savings", "AutoUpdateTAXREF", level=Qgis.Info)  

        # Fusionner tous les DataFrames sur les colonnes "Région" et "CD_REF"
        national_status = ("DH", "DO", "LRN", "PN", "PNA", "PAPNAT")
        for title in self.taxonTitles:
            # Traitement des statuts non nationaux
            if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of saving {title} on regional", "AutoUpdateTAXREF", level=Qgis.Info)
            # Verifier que des statuts non-nationaux sont mis à jour
            if set(self.list_status_id) - (set(self.list_status_id) & set(national_status)) :
                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{title}_{status_id}.gpkg")))
                    for status_id in self.list_status_id if not (status_id in national_status)]
                
                # Fusionner les DataFrames sur les colonnes "Région" et "CD_REF"
                statusUpdatedArray = reduce(
                    lambda left, right: pd.merge(left, right, on=["Région", "CD_REF"], how="outer"), df_to_reduce)

                # Sauvegarder les résultats fusionnés
                save_regional_status(statusUpdatedArray, self.path, title)

            if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of saving {title} on national", "AutoUpdateTAXREF", level=Qgis.Info)

            # Traitement des statuts nationaux
            if set(self.list_status_id) & set(national_status):
                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{title}_{status_id}.gpkg")))
                    for status_id in self.list_status_id if status_id in national_status]
            
                # Fusionner les DataFrames sur la colonne "CD_REF"
                statusUpdatedArray = reduce(
                    lambda left, right: pd.merge(left, right, on=["CD_REF"], how="outer"), df_to_reduce)
            
                # Sauvegarde les nouvelles colonnes
                save_national_status(statusUpdatedArray, self.path, title, debug=self.debug)

            if self.debug > 0 :
                QgsMessageLog.logMessage(f"End of saving on {title}", "AutoUpdateTAXREF", level=Qgis.Info)            

            # Supprimer les fichiers temporaires pour chaque status_id
            for status_id in self.list_status_id :
                # Supprime les fichiers temporaires
                os.remove(os.path.join(self.path, f"{title}_{status_id}.gpkg"))
        
        if self.debug > 0 :
                QgsMessageLog.logMessage(f"End of savings", "AutoUpdateTAXREF", level=Qgis.Info)

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

class SaveSourcesThread(QThread):
    """
    Thread pour sauvegarder les nouvelles sources dans un fichier.

    Cette classe étend `QThread` et est utilisée pour effectuer la sauvegarde des nouvelles sources
    dans un fichier spécifique en arrière-plan, sans bloquer l'interface utilisateur. Une fois la sauvegarde
    terminée, le signal `finished` est émis.

    Attributes:
        finished (pyqtSignal): Signal émis lorsque la sauvegarde est terminée.
        path (str): Le chemin où les nouvelles sources doivent être sauvegardées.
        newVer (str): La nouvelle version à associer aux sources.
        newSources (pd.DataFrame): Le DataFrame contenant les nouvelles sources à sauvegarder.
    """

    finished = pyqtSignal()

    def __init__(self, path, new_version, new_sources):
        """
        Initialise un thread pour la sauvegarde des nouvelles sources.

        Args:
            path (str): Le chemin où les nouvelles sources doivent être sauvegardées.
            newVer (str): La nouvelle version à associer aux sources.
            newSources (pd.DataFrame): Le DataFrame contenant les nouvelles sources à sauvegarder.
        """

        super().__init__()
        self.path = path
        self.new_version = new_version
        self.new_sources = new_sources

    def run(self):
        """
        Exécute la sauvegarde des nouvelles sources dans un fichier.

        Cette méthode est exécutée dans un thread séparé et appelle la fonction `save_new_sources` 
        pour effectuer la sauvegarde. Une fois terminée, le signal `finished` est émis pour signaler 
        la fin du processus.
        """

        # Sauvegarde les nouvelles sources dans le fichier spécifié
        save_new_sources(self.path, self.new_version, self.new_sources)
        # Émet le signal lorsque la sauvegarde est terminée
        self.finished.emit()
