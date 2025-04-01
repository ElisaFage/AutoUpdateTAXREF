import os
import sys
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
from .UpdateStatus import DownloadStatus, SaveStatus, SaveNewSources

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
    new_length = pyqtSignal(int)
    download_finish = pyqtSignal()

    def __init__(self, path: str, taxonTitles: list, statusIds: list, save_excel, folder_excel, max_threads: int=4):
        super().__init__()
        self.path = path
        self.listStatusId = statusIds
        self.save_excel = save_excel
        self.folder_excel = folder_excel
        self.taxonTitles = taxonTitles

        self.length_status = []#{title: 0 for title in self.taxonTitles}
        self.listStatusUpdated = []#{title: [] for title in self.taxonTitles}
        #self.download_threads = {}
        self.global_progress = 0

        self.new_length.connect(self.on_new_length)

    def run(self):
        # Charger le fichier GeoPackage dans un DataFrame
        self.step = 0
        statusId = self.listStatusId[self.step]
        # Liste pour stocker les DataFrames mis à jour pour chaque statut
        #for statusId in self.listStatusId :
        self.subrun(statusId)

    def subrun(self, statusId):
        self.download_thread = DownloadStatus(statusId, self.path, self.taxonTitles, self.save_excel, self.folder_excel)
        #self.download_threads[statusId].download_finished_progress.connect(self.on_download_finished)
        self.download_thread.progress.connect(self.on_percent_progress) # Met a jour la barre de progression
        self.download_thread.download_finished.connect(self.on_make_array_finished)
        self.download_thread.run() # Lance le téléchargement

    """def on_download_finished(self):
        # Code à exécuter lorsque le signal 'download_finished_progress' est émis
        self.download_finish.emit()"""

    def on_percent_progress(self, progress):
        self.global_progress += progress / len(self.listStatusId)
        self.progress.emit(int(round(self.global_progress)))

    def on_make_array_finished(self): #, statusArrayOut: pd.DataFrame):

        self.step+=1
    
        #self.listStatusUpdated.append(statusArrayOut)
        #self.length_status = len(self.listStatusUpdated)
        #self.new_length.emit(self.step)
        
        if self.step < len(self.listStatusId):
            statusId = self.listStatusId[self.step]
            self.subrun(statusId)
        elif self.step == len(self.listStatusId):
            self.new_length.emit(self.step)

    def on_new_length(self, new_length):

        QgsMessageLog.logMessage(f"on_new_length is True : new_length is {new_length} and list length id {len(self.listStatusId)}",
                                    "AutoUpdateTAXREF", level=Qgis.Info)
        # Fusionner tous les DataFrames sur les colonnes "Région" et "CD_REF"
        reversed_dict = {}
        for title in self.taxonTitles:
            """df_to_reduce = []
            for statusId in self.listStatusId:
                file_path = os.path.join(self.path, f"{title}_{statusId}.gpkg")
                with gpd.read_file(file_path) as gdf:  # Lecture avec gestion explicite des ressources
                    df_to_reduce.append(pd.DataFrame(gdf))"""

            df_to_reduce = [pd.DataFrame(
                gpd.read_file(os.path.join(self.path, f"{title}_{statusId}.gpkg")))
                for statusId in self.listStatusId]
            
            #reversed_dict[title] = [d[title] for d in self.listStatusUpdated if not d[title].empty]
            statusUpdatedArray = reduce(
                lambda left, right: pd.merge(left, right, on=["Région", "CD_REF"], how="outer"), df_to_reduce)
                #reversed_dict[title])
            QgsMessageLog.logMessage(f"End of reduce on {title}", "AutoUpdateTAXREF", level=Qgis.Info)

            SaveStatus(statusUpdatedArray, self.path, title)

            QgsMessageLog.logMessage(f"End of saving on {title}", "AutoUpdateTAXREF", level=Qgis.Info)            

            for statusId in self.listStatusId :
                os.remove(os.path.join(self.path, f"{title}_{statusId}.gpkg"))

        self.finished.emit()

class SaveSourcesThread(QThread):
    finished = pyqtSignal()

    def __init__(self, path, newVer, newSources):
        super().__init__()
        self.path = path
        self.newVer = newVer
        self.newSources = newSources

    def run(self):
        SaveNewSources(self.path, self.newVer, self.newSources)
        self.finished.emit()
