from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import pandas as pd

from .GetVersions import Recup_my_version, Recup_current_version
from .MessageBoxes import AskUpdate

from .UpdateSearchStatus import CheckUpdateStatus
from .UpdateStatusDialog import UpdateStatusDialog, SaveXlsxDialog

from .ProgressDownload import DownloadWindow, DownloadWindowTest

#def UpdateSearch(self, path:str, faune: bool=True, flore: bool=True)->None:

class UpdateInitThread(QThread):
    finished = pyqtSignal(bool, # do_update
                          str,  # path
                          list, # local_statusIds
                          int,  # version
                          bool, # synonyme
                          bool, # new_version
                          bool, # new_status
                          pd.DataFrame, # new_sources
                          bool, # save_excel
                          str,  # folder
                          bool, # faune
                          bool, # flore
                          int)  # debug

    def __init__(self, path, faune, flore, statusIds):
        super().__init__()

        self.path = path
        self.debug = 1
        
        self.faune = faune
        self.flore = flore

        self.statusIds = statusIds
        self.local_statusIds = statusIds

        self.do_update = False
        self.new_version = False
        self.new_status = False
        self.save_excel = False
        self.folder = None
        self.new_sources = pd.DataFrame(columns=["id", "fullCitation"])

        
    def run(self):
        #["DH", "DO", "PN", "PR", "PD", "LRN", "LRR", "PNA", "PAPNAT", "ZDET", "REGLLUTTE"]

        self.my_ver = Recup_my_version(self.path)
        if self.debug > 0 :
                QgsMessageLog.logMessage(f"Ma version : {self.my_ver}", "AutoUpdateTAXREF", level=Qgis.Info)
        self.current_ver = Recup_current_version()
        if self.debug > 0 :
                QgsMessageLog.logMessage(f"Dernière version : {self.current_ver}", "AutoUpdateTAXREF", level=Qgis.Info)
        # Comparer la version locale à la version actuelle
        if self.my_ver != self.current_ver:
            self.new_version = True
            self.do_update = AskUpdate(self.current_ver)
            if self.do_update == True :
                self.save_excel, self.folder = self.AskSaveExcel()
            print(self.do_update)    
        else :
            # Cherche des sources pour mettre a jour les statuts
            self.new_sources = CheckUpdateStatus(self.path)
            if not self.new_sources.empty :
                # Crée la boîte de dialogue avec le texte personnalisé
                text_lines = self.new_sources["fullCitation"].to_list()
                self.status_dialog = UpdateStatusDialog(text_lines, self.statusIds)
                self.dialog_result = self.status_dialog.exec_()

                if self.debug > 0 :
                    QgsMessageLog.logMessage(f"dialog_result = {self.dialog_result}, dont_ask_again = {self.status_dialog.dont_ask_again}", "AutoUpdateTAXREF", level=Qgis.Info)
                # Tester si l'utilisateur a accepté OU si la case "don't show again" est cochée
                if self.dialog_result == QDialog.Accepted :
                    if self.status_dialog.user_response == True or self.status_dialog.dont_ask_again:
                        self.new_status = self.status_dialog.user_response
                        self.do_update = True    
                    if self.status_dialog.user_response == True :
                        self.local_statusIds = list(self.status_dialog.selected_statuses)
                        self.save_excel, self.folder = self.AskSaveExcel()

                # Si on accepte de mettre a jour OU Si l'utilisateur refuse la maj et ne veux plus que ces nouvelles sources lui soient reproposées
                
        self.finished.emit(self.do_update,
                           self.path,
                           self.local_statusIds,
                           self.current_ver,
                           False,
                           self.new_version,
                           self.new_status,
                           self.new_sources,
                           self.save_excel,
                           self.folder,
                           self.faune,
                           self.flore,
                           self.debug)

        return
    
    def AskSaveExcel(self):
        self.save_excel_dialog = SaveXlsxDialog()
        save_dailog_result = self.save_excel_dialog.exec()
        save_excel = self.save_excel_dialog.user_response
        folder = QFileDialog.getExistingDirectory(None, "Sélectionnez un dossier pour sauvegarder le fichier") if save_dailog_result == QDialog.Accepted and self.save_excel_dialog.user_response else ""
        
        return save_excel, folder

