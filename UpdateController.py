# Bibliothèque communes
import os.path
import geopandas as gpd

# Import pour PyQt
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Fonctions pratiques
from .utils import print_debug_info

# Models
from .taxongroupe import TAXONS, TAXON_TITLES, STATUS_IDS
from .UpdateSearchStatus import SourcesManager
from .GetVersions import VersionManager

from .AutoUpdateTAXREF_dialog import AutoUpdateTAXREFDialog

from UpdateThreadClasses import (GetURLThread,
                                 DownloadTaxrefThread,
                                 SaveTaxrefThread,
                                 GetStatusThread)

# Views
from .UpdateStatusDialog import UpdateTAXREFDialog, UpdateStatusDialog, SaveXlsxDialog
from .UpdateViewProgress import ProgressionWindow

class UpdateController(QThread):
    cancel_requested = pyqtSignal()  # Signal pour annuler les threads
    last_save_finished = pyqtSignal()
    
    search_for_update_finished = pyqtSignal()
    global_progress = pyqtSignal()

    def __init__(self, project_path: str, debug: int=0):

        self.project_path = project_path
        self.debug = debug

        self.taxon_titles = self.get_taxon_title_from_data(self)
        self.taxons = [taxon for taxon in TAXONS if taxon.title in self.taxon_titles]
        self.status_ids = STATUS_IDS
        self.synonyme = False

        self.source_model = SourcesManager(self.project_path, debug=self.debug)

        if len(self.taxon_titles) != 0:
            self.version_model = VersionManager(self.project_path, self.taxon_titles, debug=self.debug)
            self.search_for_update_finished.connect(self.on_update_search_finished)
            self.search_for_update()

    def cancel_process(self):
        """
        Annule le processus de téléchargement et ferme la fenêtre.
        """
        self.cancel_requested.emit()  # Émet un signal pour annuler les threads en cours
        self.terminate()

    def get_taxon_title_from_data(self):

        data_path = os.path.join(self.project_path, "Données.gpkg")

        if os.path.isfile(data_path) :
            available_layers = gpd.list_layers(data_path)
            if available_layers.shape[0] != 0 :
                taxon_titles = available_layers["Name"].values
                return taxon_titles
        
        return None

    def launch_updates(self):

        self.download_window = ProgressionWindow(self.new_version, self.new_status, self.debug)
        self.global_progress.connect(self.download_window._global_increment_step)
        self.download_window.cancel_requested.connect(self.cancel_process)
        self.last_save_finished.connect(self.download_window.close())
        self.download_window.show()

        # Démarrage initial selon les paramètres
        if self.new_version:
            self._start_get_url()
        elif self.new_status:
            self._start_download_status()
        else:
            self._start_save_sources()

    def ask_update_taxref(self):
        """
        Affiche une boîte de dialogue demandant à l'utilisateur s'il souhaite mettre à jour la version de TAXREF.
        """
        
        # Initialise la fenêtre

        ask_update_dialog = UpdateTAXREFDialog(self.version_model.current_version)
        ask_dialog_result = ask_update_dialog.exec()

        if ask_dialog_result == QDialog.Accepted:
            self.do_update = ask_update_dialog.user_response
        else :
            self.do_update = False

    def ask_save_excel(self):
        """
        Affiche une boîte de dialogue demandant à l'utilisateur s'il souhaite sauvegarder les données
        dans un fichier Excel, et le cas échéant, lui propose de sélectionner un dossier de destination.

        Retourne :
            tuple (bool, str) :
                - True si l'utilisateur souhaite sauvegarder un fichier Excel, False sinon.
                - Le chemin du dossier sélectionné pour la sauvegarde, ou une chaîne vide si aucun dossier n'est choisi.
        """

        # Boîte de dialogue pour demander à l'utilisateur s'il souhaite sauvegarder
        save_excel_dialog = SaveXlsxDialog()
        save_dialog_result = save_excel_dialog.exec()

        # Récupère la réponse de l'utilisateur (True si "Oui", False si "Non")
        self.save_excel = save_excel_dialog.user_response

        # Si l'utilisateur accepte, on lui demande le dossier de sauvegarde
        if save_dialog_result == QDialog.Accepted and self.save_excel:
            self.excel_folder = QFileDialog.getExistingDirectory(None, "Sélectionnez un dossier pour sauvegarder le fichier")
        else:
            self.excel_folder = ""

    def ask_update_status(self):

        text_lines = self.source_model.get_new_sources_list()
        self.status_dialog = UpdateStatusDialog(text_lines, self.status_ids)
        self.dialog_result = self.status_dialog.exec_()

        print_debug_info(self.debug, 0, f"dialog_result = {self.dialog_result}, "
                            f"dont_ask_again = {self.status_dialog.dont_ask_again}")

        # Traitement des réponses utilisateur via la boîte de dialogue
        if self.dialog_result == QDialog.Accepted:
            if self.status_dialog.user_response or self.status_dialog.dont_ask_again:
                self.new_status = self.status_dialog.user_response
                self.do_update = True
            if self.status_dialog.user_response:
                self.local_status_ids = list(self.status_dialog.selected_statuses)
                self.ask_save_excel()

    def search_for_update(self):
        """
        Vérifie si une mise à jour est nécessaire en comparant les versions.
        Propose à l'utilisateur de mettre à jour si nécessaire et émet les résultats.
        """
        # Récupération de la version actuelle locale
        self.version_model.set_data_version()

        # Récupération de la version actuelle en ligne
        self.version_model.set_current_version()

        # Vérification si une mise à jour de la version est nécessaire
        if self.version_model.data_version != self.version_model.current_version :
            self.new_version = True
            self.source_model.set_new_version(self.new_version)
            self.ask_update_taxref()
            if self.do_update:
                self.ask_save_excel()
            #print(self.do_update)
        else:
            # Vérification s'il existe de nouvelles sources nécessitant une mise à jour des statuts
            self.source_model.check_update_status()
            if not self.source_model.new_sources.empty:
                self.ask_update_status()

        self.search_for_update_finished.emit()

    def on_update_search_finished(self):
        
        if self.do_update :
            print_debug_info(self.debug, 1, f"Les statuts selectionnés sont : {self.local_status_ids}")
            print_debug_info(self.debug, 1, f"Save excel : {self.save_excel} et folder excel : {self.excel_folder}")

            # Démarrage initial selon les paramètres
            self.launch_updates()

    def on_bouton(self, first_start):

        if first_start :
            self.dlg = AutoUpdateTAXREFDialog(taxon_titles=self.taxon_titles, status_names=STATUS_IDS)

        # show the dialog
        self.dlg.reset_dialog()
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:

            self.new_version = True if self.dlg.radio_taxref_all.isChecked() else False
            self.new_status = True if self.dlg.radio_status_only.isChecked() else False
            self.local_taxons_titles = list(self.dlg.selected_taxons) 
            self.local_status_ids = list(self.dlg.selected_statuses)

            print_debug_info(self.debug, 0, f"Accepted : \nTAXREF : {self.new_version} \nStatus : {self.new_status}, {self.local_status_ids}")

            self.ask_save_excel()
            # Récupération de la version actuelle en ligne
            self.version_model.set_current_version()
            self.source_model.check_update_status()

            self.launch_updates()

    def _start_get_url(self):
        """
        Démarre le thread permettant de récupérer l'URL de téléchargement.
        """
        self.get_url_thread = GetURLThread(self.version_model.current_version)
        self.get_url_thread.finished.connect(self._on_url_found)
        self.cancel_requested.connect(self.get_url_thread.terminate)  # Connecte le signal d'annulation
        self.download_window.initialize_global_bar()
        self.get_url_thread.start()

    def _on_url_found(self, url:str):
        """
        Callback appelé lorsque l'URL de téléchargement est récupérée.

        :param url: URL récupérée.
        """
        self.file_url = url
        self.global_progress.emit()
        self._start_download_taxref()

    def _start_download_taxref(self):
        """
        Démarre le thread de téléchargement du fichier TAXREF.
        """
        self.download_taxref_thread = DownloadTaxrefThread(self.file_url)
        self.download_taxref_thread.progress.connect(self.download_window._step_increment_step)
        self.download_taxref_thread.finished.connect(self._on_download_complete)
        self.cancel_requested.connect(self.download_taxref_thread.terminate)
        self.download_window.update_step_progress_label("Téléchargement de TAXREF en cours...")
        self.download_taxref_thread.start()

    def _on_download_complete(self, temp_file_path: str):
        """
        Callback appelé lorsque le téléchargement est terminé.

        :param file_path: Chemin du fichier téléchargé.
        """
        self.temp_file_path = temp_file_path
        self.global_progress.emit()
        self._start_save_taxref()

    def _start_save_taxref(self):
        """
        Démarre le thread de sauvegarde des données TAXREF.
        """
        self.save_taxref_thread = SaveTaxrefThread(
            self.temp_file_path,
            self.version_model.current_version,
            self.taxons,
            self.project_path,
            self.synonyme)
        
        self.save_taxref_thread.finished.connect(self._on_taxref_saved)
        self.cancel_requested.connect(self.save_taxref_thread.terminate)
        self.save_taxref_thread.start()

    def _on_taxref_saved(self):
        """
        Callback appelé lorsque l'enregistrement des données TAXREF est terminé.
        """
        self.global_progress.emit()
        self._start_download_status()

    def _start_download_status(self):
        """
        Démarre le thread de téléchargement des statuts.
        """
        self.get_status_thread = GetStatusThread(
            self.project_path,
            self.taxon_titles,
            self.status_ids,
            self.save_excel,
            self.excel_folder,
            debug=self.debug)
        
        self.get_status_thread.progress.connect(self.download_window._step_increment_step)
        self.get_status_thread.finished.connect(self._start_save_sources)
        self.cancel_requested.connect(self.get_status_thread.termination_process)
        self.download_window.update_step_progress_label("Téléchargement des statuts en cours...")
        self.get_status_thread.start()

    def _start_save_sources(self):
        """
        Démarre le thread de sauvegarde des sources.
        """
        self.global_progress.emit()
        self.download_window.update_step_progress_label("Téléchargement des statuts terminé")

        print_debug_info(self.debug, -1, "In start save sources")
        self.source_model.save_new_sources()

        self.last_save_finished.emit()
