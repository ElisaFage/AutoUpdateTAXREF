# Bibliothèque communes
import os.path
import geopandas as gpd

# Import pour PyQt
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Fonctions pratiques
from .utils import (print_debug_info,
                    list_layers_from_gpkg)

# Models
from .taxongroupe import (TAXONS,
                          get_taxon_titles, get_taxon_from_titles)
from .statustype import (STATUS_TYPES, get_status_types_from_ids)
from .UpdateSearchStatus import SourcesManager
from .GetVersions import VersionManager

from .AutoUpdateTAXREF_dialog import AutoUpdateTAXREFDialog

from .UpdateThreadClasses import (GetURLThread,
                                 DownloadTaxrefThread,
                                 SaveTaxrefThread,
                                 GetStatusThread)

# Views
from .UpdateStatusDialog import UpdateTAXREFDialog, UpdateStatusDialog, SaveXlsxDialog
from .UpdateViewProgress import ProgressionWindow

class UpdateController(QThread):
    cancel_requested = pyqtSignal()  # Signal pour annuler les threads
    update_launch_signal = pyqtSignal()
    last_save_finished = pyqtSignal()
    
    search_for_update_finished = pyqtSignal()
    global_progress = pyqtSignal()

    def __init__(self, project_path: str, debug: int=0):
        """
        Initialisation d'une instance de UpdateController

        :param:
        project_path (str): chemin absolu du projet
        debug (int): niveau de debug
        """
        super().__init__()

        # Donne l'état du télécharmegement des maj (en cours: running == True, à l'arrêt: running == False)
        self.running = False
        # Change l'état de running quand le signal de fin de maj est emit
        self.last_save_finished.connect(self.run_state_off)
        # Change l'état de running lorsqu'une maj se lance
        self.update_launch_signal.connect(self.run_state_on)
        self.project_path = project_path
        self.debug = debug
        
        # Attributs pour gérer les mises à jour
        # Attribut pour lance une maj
        self.do_update = False
        # Attribut indiquant une nouvelle version de taxref
        self.new_version = False
        # Attribut indiquant des nouvelles sources pour les statuts
        self.new_status = False
        
        self.local_status_types = STATUS_TYPES
        self.synonyme = False

        # Chemin des fichiers Donnees.gpkg et Statuts.gpkg
        self.data_path = os.path.join(self.project_path, "Donnees.gpkg")
        self.status_path = os.path.join(self.project_path, "Statuts.gpkg")

        # Si les deux fichiers gpkg existent
        if os.path.isfile(self.data_path) and os.path.isfile(self.status_path):
            # Récupère les taxons d'intérêt
            local_taxon_titles = get_taxon_titles(self.data_path)
            self.local_taxons = get_taxon_from_titles(local_taxon_titles)
            
            # Instancie le manager des sources
            self.source_model = SourcesManager(self.data_path, debug=self.debug)

            # Si Donnees.gpkg contient des couches avec des taxons
            if len(self.local_taxons) != 0:
                # Instancie le manager des Versions
                self.version_model = VersionManager(self.project_path, self.local_taxons, debug=self.debug)
                # Connect le signal émit en fin de search_for_update à on_update_search_finished
                self.search_for_update_finished.connect(self.on_update_search_finished)
                self.search_for_update() 
            # s'il n'y a pas de taxon d'intérêt dans Donnees.gpkg
            else :
                self.version_model = VersionManager(self.project_path, TAXONS, debug=self.debug)  

        # Si au moins un des deux fichiers gpkg n'existe pas
        else :
            self.local_taxons = TAXONS
            self.version_model = VersionManager(self.project_path, TAXONS, debug=self.debug)
            self.source_model = SourcesManager(self.data_path, debug=self.debug)

            print_debug_info(self.debug, 0, "Il n'y a ni de fichier 'Donnees.gpkg', ni de fichier 'Statuts.gpkg'. Aucune mise à jour ne se fera automatiquement. Cliquez sur le bouton prévu à cet effet si vous souhaitez tout de même faire une mise à jour des taxons et/ou statuts.")

    def run_state_off(self):
        self.running = False

    def run_state_on(self):
        self.running = True

    def cancel_process(self):
        """
        Annule le processus de téléchargement et ferme la fenêtre.
        """
        self.cancel_requested.emit()  # Émet un signal pour annuler les threads en cours
        self.last_save_finished.emit() # Emet un signal connecté à la mise en off de running
        self.terminate() # potentiellement à commenter pour éviter la destruction de l'objet controller

    def launch_updates(self):
        """
        Démarre les mises à jour des données taxonomiques ou des statuts 
        """

        # Met l'état du thread en running true
        self.run_state_on()

        # définit le nombre d'étape nécessaire
        total_steps_number = 6 if self.new_version else 3 if self.new_status else 1

        self.download_window = ProgressionWindow(total_steps_number)
        self.global_progress.connect(self.download_window._global_increment_step)
        self.download_window.cancel_requested.connect(self.cancel_process)
        self.last_save_finished.connect(self.download_window._on_finished_save)
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
        Affiche une boîte de dialogue demandant à l'utilisateur.rice s'il ou elle souhaite mettre à jour la version de TAXREF.
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
        Affiche une boîte de dialogue demandant à l'utilisateur.rice s'il ou elle souhaite sauvegarder les données
        dans un fichier Excel, et le cas échéant, lui propose de sélectionner un dossier de destination.

        Retourne :
            tuple (bool, str) :
                - True si l'utilisateur.rice souhaite sauvegarder un fichier Excel, False sinon.
                - Le chemin du dossier sélectionné pour la sauvegarde, ou une chaîne vide si aucun dossier n'est choisi.
        """

        # Boîte de dialogue pour demander à l'utilisateur.rice s'il ou elle souhaite sauvegarder
        save_excel_dialog = SaveXlsxDialog()
        save_dialog_result = save_excel_dialog.exec()

        # Récupère la réponse de l'utilisateur.rice (True si "Oui", False si "Non")
        self.save_excel = save_excel_dialog.user_response

        # Si l'utilisateur.rice accepte, on lui demande le dossier de sauvegarde
        if save_dialog_result == QDialog.Accepted and self.save_excel:
            self.excel_folder = QFileDialog.getExistingDirectory(None, "Sélectionnez un dossier pour sauvegarder les fichiers")
        else:
            self.excel_folder = ""

    def ask_update_status(self):

        # Récupère les noms des sources pour pouvoir les montrer à l'utilisateur.rice
        text_lines = self.source_model.get_new_sources_list()
        # Fenêtre de dialogue avec l'utilisateur.rice pour demander la maj des statuts
        self.status_dialog = UpdateStatusDialog(text_lines, [status.type_id for status in self.local_status_types])
        # Execution de la pop-up
        self.dialog_result = self.status_dialog.exec_()

        print_debug_info(self.debug, 0, f"dialog_result = {self.dialog_result}, "
                            f"dont_ask_again = {self.status_dialog.dont_ask_again}")

        # Traitement des réponses utilisateur.rice via la boîte de dialogue
        if self.dialog_result == QDialog.Accepted:
            if self.status_dialog.user_response or self.status_dialog.dont_ask_again:
                # Sauve la reponse de l'utilisateur.rice quant à la maj des statuts
                self.new_status = self.status_dialog.user_response
                # Met do_uptade
                self.do_update = True
            if self.status_dialog.user_response:
                # Si l'utrilisateur veux la maj des statuts : récupère les statuts d'intérêt
                self.local_status_types = get_status_types_from_ids(list(self.status_dialog.selected_statuses))
                # Demande à l'utilisateur.rice le besoin de sauvegarde en CSV
                self.ask_save_excel()
            if self.status_dialog.dont_ask_again:
                # Met des valeur par défaut
                self.excel_folder = ""
                self.save_excel = False

    def search_for_update(self):
        """
        Vérifie si une mise à jour est nécessaire en comparant les versions.
        Propose à l'utilisateur.rice de mettre à jour si nécessaire et émet les résultats.
        """
        # Récupération de la version actuelle locale
        self.version_model.set_data_version()

        # Récupération de la version actuelle en ligne
        self.version_model.set_current_version()

        # Récupération des taxons dans Statuts.gpkg
        taxon_liste_status = get_taxon_titles(self.status_path, prefix="Liste")
        taxon_status_status = get_taxon_titles(self.status_path, prefix="Statuts")

        local_taxon_titles = [taxon.title for taxon in self.local_taxons]
        print_debug_info(self.debug, 1, f"local_taxon_title : {local_taxon_titles}")
        print_debug_info(self.debug, 1, f"taxon_liste_status : {taxon_liste_status}")
        print_debug_info(self.debug, 1, f"local_status_status: {taxon_status_status}")

        # Check si les taxons de Donnees.gpkg sont les mêmes que dans Statuts.gpkg
        cond_liste_status = all(taxon in taxon_liste_status for taxon in local_taxon_titles)
        cond_status_status = all(taxon in taxon_status_status for taxon in local_taxon_titles)
        cond_status = cond_liste_status & cond_status_status

        # Vérification si une mise à jour de la version est nécessaire
        if (not self.version_model.issame_versions()) or not cond_status:
            # Met le booléen pour la nouvelle version de taxref en True
            self.new_version = True
            # Applique cette modification a source_model (pour la sauvegarde des sources)
            self.source_model.set_new_version(self.new_version)
            # Demande à l'utilisateur.rice s'il ou elle veux faire une sauvegarde
            self.ask_update_taxref()
            if self.do_update:
                # Demande à l'utilisateur.rice s'il ou elle veux cauver en CSV et où
                self.ask_save_excel()
        else:
            # Vérification s'il existe de nouvelles sources nécessitant une mise à jour des statuts
            self.source_model.check_update_status()
            # s'il y a des nouvelles sources d'intérêt potentiel
            if self.source_model.is_new_sources():
                # Demande à l'utilisateur.rice s'il ou elle veux faire une màj des statuts
                self.ask_update_status()

        # Émet le signal de fin de la recherche de màj
        self.search_for_update_finished.emit()

    def on_update_search_finished(self):
        
        # Si le booléen pour effecteur les màj est True
        if self.do_update :
            print_debug_info(self.debug, 1, f"Les statuts selectionnés sont : {[status.type_id for status in self.local_status_types]}")
            print_debug_info(self.debug, 1, f"Save excel : {self.save_excel} et folder excel : {self.excel_folder}")

            # Démarrage initial selon les paramètres
            self.launch_updates()

    def on_bouton(self, first_start):
        """
        Évènements lors du clique sur le bouton dans la toolbar de QGIS
        """

        # Initialisation en cas de premier clique
        if first_start :
            # Préparation des taxons d'intérêt
            if self.local_taxons == [] :
                self.local_taxons = TAXONS
            # Instanciation de la fenêtre de dialogue sur clique
            self.dlg = AutoUpdateTAXREFDialog(taxons=self.local_taxons,
                                              status_names=[status.type_id for status in STATUS_TYPES])

        # Reset la fenêtre de dialogue
        self.dlg.reset_dialog()
        # Montre le dialogue
        self.dlg.show()
        # Run la boucle de dialogue
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            
            # Attribut les valeurs en fonction de la màj demandée
            self.new_version = True if self.dlg.radio_taxref_all.isChecked() else False
            self.new_status = True if self.dlg.radio_status_only.isChecked() else False

            # Change les taxons et status d'intérêts
            self.local_taxons = get_taxon_from_titles(list(self.dlg.selected_taxons))
            self.local_status_types = get_status_types_from_ids(list(self.dlg.selected_statuses))

            print_debug_info(self.debug, 0, f"Accepted : \nTAXREF : {self.new_version} \nStatus : {self.new_status}, {[status.type_id for status in self.local_status_types]}")

            # Demande à l'utilisateur.rice, s'il ou elle veut sauver en CSV
            self.ask_save_excel()
            # Récupération de la version actuelle en ligne
            #self.version_model.set_taxons(self.local_taxons)
            self.version_model.set_current_version()
            self.source_model.check_update_status()

            # Lance les màj
            self.launch_updates()

    def _start_get_url(self):
        """
        Démarre le thread permettant de récupérer l'URL de téléchargement.
        """
        
        # Instanciation du Thread
        self.get_url_thread = GetURLThread(self.version_model.current_version)
        # Connection à l'étape suivante
        self.get_url_thread.finished.connect(self._on_url_found)
        # Connection en cas d'annulation
        self.cancel_requested.connect(self.get_url_thread.terminate)
        # Prépare la barre de chargement
        self.download_window.initialize_global_bar()
        # Lance le thread
        self.get_url_thread.start()

    def _on_url_found(self, url:str):
        """
        Callback appelé lorsque l'URL de téléchargement est récupérée.

        :param url: URL récupérée.
        """

        # Attribut l'url émit en sortie de thread par get_url_thread
        self.file_url = url
        # Emet le signal de progression
        self.global_progress.emit()
        # Lance l'étape suivante
        self._start_download_taxref()

    def _start_download_taxref(self):
        """
        Démarre le thread de téléchargement du fichier TAXREF.
        """

        # Instanciation du thread de téléchargement de TAXREF
        self.download_taxref_thread = DownloadTaxrefThread(self.file_url)
        # Connection des signaux pour la barre de progression
        self.download_taxref_thread.progress.connect(self.download_window._step_increment_step)
        # Connecte à l'étape suivante
        self.download_taxref_thread.finished.connect(self._on_download_complete)
        # Connecte en cas d'annulation
        self.cancel_requested.connect(self.download_taxref_thread.terminate)
        # Met a jour le label de la barre de progression
        self.download_window.update_step_progress_label("Téléchargement de TAXREF en cours...")
        # Lance de thread
        self.download_taxref_thread.start()

    def _on_download_complete(self, temp_file_path: str):
        """
        Callback appelé lorsque le téléchargement est terminé.

        :param file_path: Chemin du fichier téléchargé.
        """

        # Stock le chemin du fichier temporaire
        self.temp_file_path = temp_file_path
        # Emet un signal de progression globale
        self.global_progress.emit()
        # Va à l'étape suivante
        self._start_save_taxref()

    def _start_save_taxref(self):
        """
        Démarre le thread de sauvegarde des données TAXREF.
        """

        # Instanciation du thread
        self.save_taxref_thread = SaveTaxrefThread(
            self.temp_file_path,
            self.version_model.current_version,
            self.local_taxons,
            self.project_path,
            self.synonyme)
        
        # Connecte la fin du thread à l'étape suivante
        self.save_taxref_thread.finished.connect(self._on_taxref_saved)
        # Connecte en cas d'annulation
        self.cancel_requested.connect(self.save_taxref_thread.terminate)
        # Lance le thread
        self.save_taxref_thread.start()

    def _on_taxref_saved(self):
        """
        Callback appelé lorsque l'enregistrement des données TAXREF est terminé.
        """

        # Emet un sigan de progression globale
        self.global_progress.emit()
        # Va à l'étape suivante
        self._start_download_status()

    def _start_download_status(self):
        """
        Démarre le thread de téléchargement des statuts.
        """

        # Instanciation du thread 
        self.get_status_thread = GetStatusThread(
            self.project_path,
            self.local_taxons,
            self.local_status_types,
            self.save_excel,
            self.excel_folder,
            debug=self.debug)
        
        # Connecte à la progression
        self.get_status_thread.progress.connect(self.download_window._step_increment_step)
        # Connecte à l'étape suivante
        self.get_status_thread.finished.connect(self._start_save_sources)
        # Connecte en cas d'annulation
        self.cancel_requested.connect(self.get_status_thread.termination_process)
        # Met à jour le titre de la barre de chargement
        self.download_window.update_step_progress_label("Téléchargement des statuts en cours...")
        # Lance le thread
        self.get_status_thread.start()

    def _start_save_sources(self):
        """
        Démarre le thread de sauvegarde des sources.
        """

        # Emet un signal de progression globale
        self.global_progress.emit()
        # Met à jour le label de la barre de chargement
        self.download_window.update_step_progress_label("Téléchargement des statuts terminé")

        print_debug_info(self.debug, -1, "In start save sources")

        # Lance la sauvegarde des sources
        self.source_model.save_new_sources()

        # Emet un signal de fin des mise à jour
        self.last_save_finished.emit()
