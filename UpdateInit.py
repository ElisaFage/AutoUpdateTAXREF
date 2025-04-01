from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import pandas as pd

from .GetVersions import Recup_my_version, Recup_current_version
from .MessageBoxes import AskUpdate

from .UpdateSearchStatus import CheckUpdateStatus
from .UpdateStatusDialog import UpdateStatusDialog, SaveXlsxDialog

from .ProgressDownload import DownloadWindow, DownloadWindowTest

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
        list,         # local_status_ids
        int,          # version
        bool,         # synonyme
        bool,         # new_version
        bool,         # new_status
        pd.DataFrame, # new_sources
        bool,         # save_excel
        str,          # folder
        bool,         # faune
        bool,         # flore
        int           # debug
    )

    def __init__(self, path, faune, flore, status_ids):
        """
        Initialise l'instance de la classe UpdateInitThread.

        Args:
            path (str): Chemin d'accès au fichier ou dossier à vérifier.
            faune (bool): Indique si la mise à jour concerne la faune.
            flore (bool): Indique si la mise à jour concerne la flore.
            status_ids (list): Liste des identifiants des statuts locaux.
        """
        super().__init__()
        self.path = path
        self.debug = 1

        self.faune = faune
        self.flore = flore

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
        self.my_version = Recup_my_version(self.path)
        if self.debug > 0:
            QgsMessageLog.logMessage(
                f"Ma version: {self.my_version}", "AutoUpdateTAXREF", level=Qgis.Info
            )

        # Récupération de la version actuelle en ligne
        self.current_version = Recup_current_version()
        if self.debug > 0:
            QgsMessageLog.logMessage(
                f"Dernière version: {self.current_version}", "AutoUpdateTAXREF", level=Qgis.Info
            )

        # Vérification si une mise à jour de la version est nécessaire
        if self.my_version != self.current_version:
            self.new_version = True
            self.do_update = AskUpdate(self.current_version)
            if self.do_update:
                self.save_excel, self.folder = self.AskSaveExcel()
            print(self.do_update)
        else:
            # Vérification s'il existe de nouvelles sources nécessitant une mise à jour des statuts
            self.new_sources = CheckUpdateStatus(self.path)
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
                        self.save_excel, self.folder = self.AskSaveExcel()

        # Émission des résultats via le signal
        self.finished.emit(
            self.do_update,
            self.path,
            self.local_status_ids,
            self.current_version,
            False,
            self.new_version,
            self.new_status,
            self.new_sources,
            self.save_excel,
            self.folder,
            self.faune,
            self.flore,
            self.debug,
        )

    def AskSaveExcel(self):
        """
        Demande à l'utilisateur s'il souhaite enregistrer les résultats dans un fichier Excel.
        Ouvre une boîte de dialogue pour choisir le dossier de sauvegarde si l'utilisateur accepte.

        Returns:
            tuple: Un tuple contenant un booléen indiquant la décision de sauvegarde et le chemin du dossier choisi.
        """
        # Création et affichage de la boîte de dialogue pour demander la sauvegarde Excel
        self.save_excel_dialog = SaveXlsxDialog()
        save_dialog_result = self.save_excel_dialog.exec()

        # Récupération de la réponse utilisateur
        save_excel = self.save_excel_dialog.user_response

        # Sélection du dossier de sauvegarde uniquement si accepté par l'utilisateur
        folder = (
            QFileDialog.getExistingDirectory(None, "Sélectionnez un dossier pour sauvegarder le fichier")
            if save_dialog_result == QDialog.Accepted and save_excel
            else ""
        )

        return save_excel, folder
    