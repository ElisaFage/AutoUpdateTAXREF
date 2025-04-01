import os
import sys
from datetime import datetime
import requests
import tempfile
from collections import deque
from functools import reduce

import pandas as pd
import geopandas as gpd

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSemaphore
from qgis.core import QgsMessageLog, Qgis

from .UpdateTAXREF import GetDownloadURL, on_DownloadComplete
from .UpdateStatus2 import run_download, SaveRegionalStatus, SaveNationalStatus, SaveNewSources

class GetURLThread(QThread):
    finished = pyqtSignal(str) # Signal pour indiquer la fin du téléchargement

    def __init__(self, version):
        super().__init__()
        self.version = version

    def run(self):
        url = GetDownloadURL(self.version)
        self.finished.emit(url)

class DownloadThread(QThread):
    progress = pyqtSignal(int)  # Signal pour transmettre la progression
    finished = pyqtSignal(str)  # Signal pour indiquer la fin du téléchargement

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        response = requests.get(self.url, stream=True)
        total_length = int(response.headers.get('content-length', 0))
        
        response.raise_for_status()
        # Créer un fichier temporaire pour stocker le ZIP
        with tempfile.NamedTemporaryFile(delete=False) as temp_zip:
            downloaded_size = 0
            for data in response.iter_content(chunk_size=4096):
                temp_zip.write(data)
                downloaded_size += len(data)
                progress_percentage = int(downloaded_size * 100 / total_length)
                self.progress.emit(progress_percentage)  # Émet le signal de progression
            temp_zip_path = temp_zip.name

        self.finished.emit(temp_zip_path)  # Émet le signal de fin

class MajTaxrefThread(QThread):
    finished = pyqtSignal()
    
    def __init__(self, temp_zip_path, version, 
                 taxonTile, taxonRegne,
                 taxonGroupe1, taxonGroupe2,
                 taxonGroupe3, taxonFamille,
                 save_path, synonyme:bool=False):
        super().__init__()
        self.version = version
        self.temp_zip_path = temp_zip_path
        self.taxonTitle = taxonTile
        self.taxonRegne = taxonRegne
        self.taxonGroupe1 = taxonGroupe1
        self.taxonGroupe2 = taxonGroupe2
        self.taxonGroupe3 = taxonGroupe3
        self.taxonFamille = taxonFamille
        self.save_path = save_path
        self.synonyme = synonyme

    def run(self):
        on_DownloadComplete(self.temp_zip_path, self.version,
                            self.taxonTitle, self.taxonRegne,
                            self.taxonGroupe1, self.taxonGroupe2,
                            self.taxonGroupe3, self.taxonFamille,
                            self.save_path, self.synonyme)
        self.finished.emit()

class GetStatusThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, path: str, taxonTitles: list, statusIds: list, save_excel, folder_excel, max_threads: int=4, debug: int=0):
        super().__init__()
        self.path = path
        self.listStatusId = statusIds
        self.save_excel = save_excel
        self.folder_excel = folder_excel
        self.taxonTitles = taxonTitles
        
        self.debug = debug

        self.length_status = []#{title: 0 for title in self.taxonTitles}
        self.listStatusUpdated = []#{title: [] for title in self.taxonTitles}
        #self.download_threads = {}
        self.global_progress = 0

    def run(self):
        # Charger le fichier GeoPackage dans un DataFrame
        self.step = 0
        statusId = self.listStatusId[self.step]

        self.pathes_temp_file = []

        for statusId in self.listStatusId:
            if self.debug > 0 :
                now = datetime.now()
                QgsMessageLog.logMessage(f"Pour {statusId}, début de run_doawnload ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

            self.pathes_temp_file += run_download(statusId, self.taxonTitles,
                                                  self.path,
                                                  self.save_excel, self.folder_excel,
                                                  debug=self.debug)
            
            if self.debug > 0 :
                now = datetime.now()
                QgsMessageLog.logMessage(f"Pour {statusId}, fin de run_doawnload ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

            self.global_progress += 100* 1/len(self.listStatusId)
            self.progress.emit(int(round(self.global_progress)))
        
        self.Concat_and_Save()
        self.finished.emit()

    def Concat_and_Save(self):

        if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of savings", "AutoUpdateTAXREF", level=Qgis.Info)  

        # Fusionner tous les DataFrames sur les colonnes "Région" et "CD_REF"
        national_status = ("DH", "DO", "LRN", "PN", "PNA", "PAPNAT")
        for title in self.taxonTitles:

            if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of saving {title} on regional", "AutoUpdateTAXREF", level=Qgis.Info)
            # Verifier que des statuts non-nationaux sont mis à jour
            if set(self.listStatusId) - (set(self.listStatusId) & set(national_status)) :
                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{title}_{statusId}.gpkg")))
                    for statusId in self.listStatusId if not (statusId in national_status)]
                
                statusUpdatedArray = reduce(
                    lambda left, right: pd.merge(left, right, on=["Région", "CD_REF"], how="outer"), df_to_reduce)

                # Sauvegarde les nouvelles colonnes
                SaveRegionalStatus(statusUpdatedArray, self.path, title)

            if self.debug > 0 :
                QgsMessageLog.logMessage(f"Start of saving {title} on national", "AutoUpdateTAXREF", level=Qgis.Info)
            # Vérifier que des statuts nationaux sont mis à jour
            if set(self.listStatusId) & set(national_status):
                # Rassemble les différents tableau en 1 pour chaque taxon
                df_to_reduce = [pd.DataFrame(
                    gpd.read_file(os.path.join(self.path, f"{title}_{statusId}.gpkg")))
                    for statusId in self.listStatusId if statusId in national_status]
            
                statusUpdatedArray = reduce(
                    lambda left, right: pd.merge(left, right, on=["CD_REF"], how="outer"), df_to_reduce)
            
                # Sauvegarde les nouvelles colonnes
                SaveNationalStatus(statusUpdatedArray, self.path, title, debug=self.debug)

            if self.debug > 0 :
                QgsMessageLog.logMessage(f"End of saving on {title}", "AutoUpdateTAXREF", level=Qgis.Info)            

            for statusId in self.listStatusId :
                # Supprime les fichiers temporaires
                os.remove(os.path.join(self.path, f"{title}_{statusId}.gpkg"))
        
        if self.debug > 0 :
                QgsMessageLog.logMessage(f"End of savings", "AutoUpdateTAXREF", level=Qgis.Info)

        return

    def termination_process(self):

        # Supprime les fichier temporaire
        if self.pathes_temp_file :
            for path in self.pathes_temp_file:
                os.remove(path)
        
        # Termine le thread de force
        self.terminate()

class SaveSourcesThread(QThread):
    finished = pyqtSignal()

    def __init__(self, path, newVer, newSources):
        super().__init__()
        self.path = path
        self.newVer = newVer
        self.newSources = newSources

    def run(self):
        # Sauvegarde les nouvelles sources
        SaveNewSources(self.path, self.newVer, self.newSources)
        self.finished.emit()
