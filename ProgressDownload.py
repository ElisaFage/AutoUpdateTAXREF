import os
import sys
import requests
import tempfile
from collections import deque
from functools import reduce

import pandas as pd
import geopandas as gpd

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QProgressBar, QPushButton, QLabel
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsMessageLog, Qgis

from .UpdateThreadClasses2 import GetURLThread, DownloadThread, MajTaxrefThread, GetStatusThread, SaveSourcesThread


class DownloadWindow(QWidget):

    cancel_requested = pyqtSignal()  # Signal pour annuler les threads

    download_finished = pyqtSignal()
    version=None
    taxonTitles = ["Flore", "Amphibiens", "Reptiles", "Oiseaux", "Mammifères", "Lépidoptères", "Odonates", "Coléoptères", "Orthoptères"]
    taxonRegnes = ["Plantae", "Animalia", "Animalia", "Animalia", "Animalia", "Animalia", "Animalia", "Animalia", "Animalia"]
    taxonGroupes1 = [["Algues", "Trachéophytes", "Bryophytes"],
                ["Chordés"], ["Chordés"], ["Chordés"], ["Chordés"],
                ["Arthropodes"], ["Arthropodes"], ["Arthropodes"], ["Arthropodes"]]
    taxonGroupes2 = [[""],
                     ["Amphibiens"], ["Reptiles"], ["Oiseaux"], ["Mammifères"],
                     ["Insectes"], ["Insectes"], ["Insectes"], ["Insectes"]]
    taxonGroupes3 = [[""],
                     [""], [""], [""], [""],
                     ["Lépidoptères"], ["Odonates"], ["Coléoptères"], ["Orthoptères"]]
    taxonFamille = [[""],
                    [""], [""], [""], [""],
                    ["Papilionidae", "Pieridae", "Nymphalidae", "Satyrinae", "Lycaenidae", "Hesperiidae", "Zygaenidae"], [""], ["Carabidae", "Hydrophilidae", "Sphaeritidae", "Histeridae", "Ptiliidae", "Agyrtidae", "Leiodidae", "Staphylinidae", "Lucanidae", "Trogidae", "Scarabaeidae", "Eucinetidae", "Clambidae", "Scirtidae", "Buprestidae", "Elmidae", "Dryopidae", "Cerophytidae", "Eucnemidae", "Throscidae", "Elateridae", "Lycidae", "Cantharidae", "Derodontidae", "Nosodendridae", "Dermestidae", "Endecatomidae", "Bostrichidae", "Ptinidae", "Lymexylidae", "Phloiophilidae", "Trogossitidae", "Thanerocleridae", "Cleridae", "Acanthocnemidae", "Melyridae", "Malachiidae", "Sphindidae", "Nitidulidae", "Monotomidae", "Phloeostichidae", "Silvanidae", "Cucujidae", "Laemophloeidae", "Cryptophagidae", "Erotylidae", "Biphyllidae", "Bothrideridae", "Cerylonidae", "Alexiidae", "Endomychidae", "Corylophidae", "Latridiidae", "Mycetophagidae", "Ciidae", "Tetratomidae", "Melandryidae", "Zopheridae", "Mordellidae", "Tenebrionidae", "Prostomidae", "Oedemeridae", "Pythidae", "Pyrochroidae", "Salpingidae", "Aderidae", "Scraptiidae", "Cerambycidae", "Chrysomelidae", "Anthribidae", "Brentidae", "Dryophthoridae", "Curculionidae"], ["Acrididae", "Gryllidae", "Gryllotalpidae", "Mogoplistida", "Myrmecophilidae", "Pamphagidae", "Phalangopsidae", "Pyrgomorphidae", "Rhaphidophoridae", "Tetrigidae", "Tettigoniidae", "Tridactylidae", "Trigonidiidae"]]
    
    #statusIds = ["DH", "DO", "PN", "PR", "PD", "LRN", "LRR", "PNA", "PAPNAT", "ZDET", "REGLLUTTE"]

    def __init__(self,
                 path: str, statusIds: list,
                 version: int=None,
                 synonyme:bool=False,
                 new_version: bool=False,
                 new_status: bool=False,
                 new_sources: pd.DataFrame=pd.DataFrame(columns=["id", "fullCitation"]),
                 save_excel: bool=False,
                 folder: str="",
                 faune: bool=True,
                 flore: bool=True,
                 debug: int=0):
        
        super().__init__()
        self.version = version
        self.save_path = path
        self.statusIds = statusIds
        self.synonyme = synonyme

        self.new_version = new_version
        self.new_status = new_status
        self.new_sources = new_sources
        self.save_excel = save_excel
        self.folder_excel = folder

        if not faune :
            indices = [i for i, regne in enumerate(self.taxonRegnes) if regne == "Animalia"]
            self.taxonTitles = [val for i, val in enumerate(self.taxonTitles) if i not in indices]
            self.taxonRegnes = [val for i, val in enumerate(self.taxonRegnes) if i not in indices]
            self.taxonGroupes1 = [val for i, val in enumerate(self.taxonGroupes1) if i not in indices]
            self.taxonGroupes2 = [val for i, val in enumerate(self.taxonGroupes2) if i not in indices]
            self.taxonGroupes3 = [val for i, val in enumerate(self.taxonGroupes3) if i not in indices]
            self.taxonFamille = [val for i, val in enumerate(self.taxonFamille) if i not in indices]
            

        if not flore :
            indices = [i for i, regne in enumerate(self.taxonRegnes) if regne == "Plantae"]
            self.taxonTitles = [val for i, val in enumerate(self.taxonTitles) if i not in indices]
            self.taxonRegnes = [val for i, val in enumerate(self.taxonRegnes) if i not in indices]
            self.taxonGroupes1 = [val for i, val in enumerate(self.taxonGroupes1) if i not in indices]
            self.taxonGroupes2 = [val for i, val in enumerate(self.taxonGroupes2) if i not in indices]
            self.taxonGroupes3 = [val for i, val in enumerate(self.taxonGroupes3) if i not in indices]
            self.taxonFamille = [val for i, val in enumerate(self.taxonFamille) if i not in indices]

        self.debug = debug

        self.file_path = None  # Initialiser le chemin du fichier temporaire
        self.status_df = None # Initialiser le dataFrame de status
        self.step=0
        self.status_download_counter = 0
        self.status_counter=0

        # Configuration de la fenêtre
        self.setWindowTitle('Mise à jour de TAXREF et des statuts')
        self.setGeometry(300, 300, 400, 200)

        # Layout et widgets
        layout = QVBoxLayout()

        # Ajout de la deuxième barre de progression
        # Label et barre de progression secondaire
        self.progressLabelSecondary = QLabel("Progression globale (étapes)")
        layout.addWidget(self.progressLabelSecondary)
        self.progressBarSecondary = QProgressBar(self)
        self.progressBarSecondary.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progressBarSecondary)

        if self.new_version == True or self.new_status == True :
            self.progressLabel = QLabel("En attente du téléchargement")
            layout.addWidget(self.progressLabel)
            self.progressBar = QProgressBar(self)
            self.progressBar.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.progressBar)
            # Bouton Annuler
            self.cancel_button = QPushButton("Annuler")
            self.cancel_button.clicked.connect(self.cancel_process)
            layout.addWidget(self.cancel_button)

            if new_version == True :
                self.n_step = 6
                self.start_getURL()
            elif new_status == True:
                self.n_step = 3
                self.start_download_status()
        else :
            # Bouton Annuler
            self.cancel_button = QPushButton("Annuler")
            self.cancel_button.clicked.connect(self.cancel_process)
            layout.addWidget(self.cancel_button)
            QgsMessageLog.logMessage(f"In else", "AutoUpdateTAXREF", level=Qgis.Info)
            self.n_step = 1
            self.start_save_sources()

        self.setLayout(layout)

    def cancel_process(self):
        """Déclenche l'annulation."""
        self.cancel_flag = True
        self.cancel_requested.emit()  # Émet un signal pour annuler les threads
        self.update_progress_text("Annulation en cours...")
        self.close()

    def update_progress_text(self, text):
        """Met à jour le texte du label principal."""
        if hasattr(self, 'progressLabel'):
            self.progressLabel.setText(text)

    def update_secondary_progress_text(self, text):
        """Met à jour le texte du label secondaire."""
        if hasattr(self, 'progressLabelSecondary'):
            self.progressLabelSecondary.setText(text)

    def start_getURL(self):

        self.geturl_thread = GetURLThread(self.version)
        self.geturl_thread.finished.connect(self.url_found)
        self.cancel_requested.connect(self.geturl_thread.terminate)  # Connecte l'annulation
        self.update_secondary_progress_text(f"Progression globale (étapes {int(self.step+1)}/{self.n_step})")
        self.geturl_thread.start()

    def url_found(self, url):
        
        self.url = url
        self.step += 1
        self.secondary_progress_value = int(round(100*self.step/self.n_step))
        self.progressBarSecondary.setValue(self.secondary_progress_value)

        if self.secondary_progress_value >= 100:
            self.secondary_progress_value = 100
            self.close()

        self.start_download()

    def start_download(self):
        #self.download_button.setEnabled(False)  # Désactive le bouton pendant le téléchargement

        # Lancer le téléchargement dans un thread séparé
        self.download_thread = DownloadThread(self.url)
        self.download_thread.progress.connect(self.progressBar.setValue)  # Connecter la progression à la barre principale
        self.download_thread.finished.connect(self.download_complete)  # Quand terminé, on appelle download_complete
        self.cancel_requested.connect(self.download_thread.terminate)
        self.update_secondary_progress_text(f"Progression globale (étapes {int(self.step+1)}/{self.n_step})")
        self.update_progress_text("Téléchargement de TAXREF en cours...")
        self.download_thread.start()

    def download_complete(self, file_path):
        #self.download_button.setEnabled(True)
        self.file_path = file_path
        self.progressBar.setValue(100)  # Marquer la barre comme complète
        self.update_progress_text("Téléchargement de TAXREF terminé")
        #self.download_finished.emit(file_path)

        # Incrémentation de la deuxième barre de progression (1 étape sur 3)
        self.step += 1
        self.secondary_progress_value = int(round((100*self.step/self.n_step)))
        self.progressBarSecondary.setValue(self.secondary_progress_value)

        if self.secondary_progress_value >= 100:
            self.secondary_progress_value = 100  # Limiter la valeur de la barre à 100%
            self.close()

        self.start_save_taxref()

    def start_save_taxref(self):

        self.majtaxref_thread = MajTaxrefThread(self.file_path, self.version,
                                                self.taxonTitles, self.taxonRegnes,
                                                self.taxonGroupes1, self.taxonGroupes2,
                                                self.taxonGroupes3, self.taxonFamille,
                                                self.save_path, self.synonyme)
        self.majtaxref_thread.finished.connect(self.taxref_saved)
        self.cancel_requested.connect(self.majtaxref_thread.terminate)
        self.update_secondary_progress_text(f"Progression globale (étapes {int(self.step+1)}/{self.n_step})")
        self.majtaxref_thread.start()

    def taxref_saved(self):
        self.step += 1
        self.secondary_progress_value = int(round(100*self.step/self.n_step))
        self.progressBarSecondary.setValue(self.secondary_progress_value)

        if self.secondary_progress_value >= 100:
            self.secondary_progress_value = 100 # Limiter la valeur de la barre à 100%
            self.close()

        self.start_download_status()

    def start_download_status(self):

        self.get_status_thread = GetStatusThread(self.save_path,
                                                 self.taxonTitles, self.statusIds,
                                                 self.save_excel, self.folder_excel,
                                                 debug=self.debug)
        self.get_status_thread.progress.connect(self.progressBar.setValue)
        #self.get_status_thread.download_finish.connect(self.on_status_download_finished)
        self.get_status_thread.finished.connect(self.start_save_sources)
        self.cancel_requested.connect(self.get_status_thread.termination_process)
        self.update_secondary_progress_text(f"Progression globale (étapes {int(self.step+1)}/{self.n_step})")
        self.update_progress_text("Téléchargement des statuts en cours...")
        self.get_status_thread.start()
    
    def start_save_sources(self):

        self.step += 1

        self.secondary_progress_value = int(round(100*self.step/self.n_step))
        self.progressBarSecondary.setValue(self.secondary_progress_value)
        self.update_progress_text("Téléchargement des statuts terminé")

        QgsMessageLog.logMessage(f"In start save sources", "AutoUpdateTAXREF", level=Qgis.Info)
        self.save_sources_thread = SaveSourcesThread(self.save_path, self.new_version, self.new_sources)
        self.save_sources_thread.finished.connect(self.sources_saved)
        self.cancel_requested.connect(self.save_sources_thread.terminate)
        self.update_secondary_progress_text(f"Progression globale (étapes {int(self.step+1)}/{self.n_step})")
        self.save_sources_thread.start()

    def sources_saved(self):

        QgsMessageLog.logMessage(f"In sources saved", "AutoUpdateTAXREF", level=Qgis.Info)
        self.step += 1
        self.secondary_progress_value = int(round(100*self.step/self.n_step))
        self.progressBarSecondary.setValue(self.secondary_progress_value)

        if self.secondary_progress_value >= 100:
            self.secondary_progress_value = 100
            self.close()
        self.close()

class DownloadWindowTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Test Download Window')
        self.setGeometry(300, 300, 200, 100)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Test de la fenêtre"))
        self.setLayout(layout)

# Exemple d'utilisation
if __name__ == '__main__':
    app = QApplication(sys.argv)  # Remplacez par votre URL de fichier ZIP
    window = DownloadWindow()
    window.show()
    downloaded_file_path = window.file_path
    sys.exit(app.exec_())
