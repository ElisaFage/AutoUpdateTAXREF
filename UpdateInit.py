from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import pandas as pd
from typing import List

from .GetVersions import recup_my_version, recup_current_version

from .UpdateSearchStatus import check_update_status
from .UpdateStatusDialog import UpdateStatusDialog, ask_update, ask_save_excel

class UpdateInitThread(QThread):
    """
    Thread chargé de vérifier la nécessité d'effectuer une mise à jour,
    de vérifier la disponibilité de nouvelles versions ou sources, et
    de gérer les interactions utilisateur correspondantes.

    Attributs:
        finished (pyqtSignal): Signal émis à la fin du traitement avec les résultats.
    """

    finished = pyqtSignal(
        bool,         # do_update
        str,          # path
        List[str],    # local_status_ids
        List[str],    # taxon_titles
        int,          # version
        bool,         # synonyme
        bool,         # new_version
        bool,         # new_status
        pd.DataFrame, # new_sources
        bool,         # save_excel
        str,          # folder
        int           # debug
    )

    def __init__(self,
                 path: str,
                 taxon_titles: List[str],
                 status_ids: List[str]):
        """
        Initialise l'instance de la classe UpdateInitThread.

        Args:
            path (str): Chemin d'accès au fichier ou dossier à vérifier.
            taxon_titles (List[str]): Liste des taxon à mettre à jour
            status_ids (List[str]): Liste des identifiants des statuts locaux.
        """
        super().__init__()
        self.path = path
        self.debug = 1

        self.taxon_titles = taxon_titles

        self.status_ids = status_ids
        self.local_status_ids = status_ids

        self.do_update = False
        self.new_version = False
        self.new_status = False
        self.save_excel = False
        self.folder = None
        self.new_sources = pd.DataFrame(columns=["id", "fullCitation"])

    def run(self):
        """
        Vérifie si une mise à jour est nécessaire en comparant les versions.
        Propose à l'utilisateur de mettre à jour si nécessaire et émet les résultats.
        """
        # Récupération de la version actuelle locale
        self.my_version = recup_my_version(self.path)
        if self.debug > 0:
            QgsMessageLog.logMessage(
                f"Ma version: {self.my_version}", "AutoUpdateTAXREF", level=Qgis.Info
            )

        # Récupération de la version actuelle en ligne
        self.current_version = recup_current_version()
        if self.debug > 0:
            QgsMessageLog.logMessage(
                f"Dernière version: {self.current_version}", "AutoUpdateTAXREF", level=Qgis.Info
            )

        # Vérification si une mise à jour de la version est nécessaire
        if self.my_version != self.current_version:
            self.new_version = True
            self.do_update = ask_update(self.current_version)
            if self.do_update:
                self.ask_save_excel = ask_save_excel
                self.save_excel, self.folder = self.ask_save_excel()
            print(self.do_update)
        else:
            # Vérification s'il existe de nouvelles sources nécessitant une mise à jour des statuts
            self.new_sources = check_update_status(self.path)
            if not self.new_sources.empty:
                text_lines = self.new_sources["fullCitation"].to_list()
                self.status_dialog = UpdateStatusDialog(text_lines, self.status_ids)
                self.dialog_result = self.status_dialog.exec_()

                if self.debug > 0:
                    QgsMessageLog.logMessage(
                        f"dialog_result = {self.dialog_result}, "
                        f"dont_ask_again = {self.status_dialog.dont_ask_again}",
                        "AutoUpdateTAXREF", level=Qgis.Info
                    )

                # Traitement des réponses utilisateur via la boîte de dialogue
                if self.dialog_result == QDialog.Accepted:
                    if self.status_dialog.user_response or self.status_dialog.dont_ask_again:
                        self.new_status = self.status_dialog.user_response
                        self.do_update = True
                    if self.status_dialog.user_response:
                        self.local_status_ids = list(self.status_dialog.selected_statuses)
                        self.ask_save_excel = ask_save_excel
                        self.save_excel, self.folder = self.ask_save_excel()

        # Émission des résultats via le signal
        self.finished.emit(
            self.do_update,
            self.path,
            self.local_status_ids,
            self.taxon_titles,
            self.current_version,
            False,
            self.new_version,
            self.new_status,
            self.new_sources,
            self.save_excel,
            self.folder,
            self.debug,
        )
    