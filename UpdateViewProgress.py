import pandas as pd
from typing import List

from PyQt5.QtWidgets import (
    QApplication,  QWidget, QVBoxLayout,
    QProgressBar, QPushButton, QLabel)
from PyQt5.QtCore import pyqtSignal

from .utils import print_debug_info
        

class ProgressionWindow(QWidget):
    """
    Fenêtre de téléchargement et de mise à jour de TAXREF et des statuts.

    Cette fenêtre orchestre plusieurs threads pour :
      - Récupérer l'URL de téléchargement
      - Télécharger le fichier TAXREF
      - Sauvegarder les données TAXREF
      - Télécharger les statuts
      - Sauvegarder les sources

    Les paramètres de téléchargement (version, synonymes, etc.) sont définis lors de l'initialisation.
    """

    cancel_requested = pyqtSignal()  # Signal pour annuler les threads
    download_finished = pyqtSignal()

    # Attributs de classe définissant les taxons
    version = None

    def __init__(self,
                 total_steps: int):
        """
        Initialise la fenêtre de téléchargement de TAXREF.

        :param total_steps (bool): Donne le nombre d'étapes et donc le nombre de portions de barre de chargement.
        """
        super().__init__()

        # Définition des paramètres
        # Compteurs et suivi d'étapes
        self.current_step = 0
        self.total_steps = total_steps

        # Interface graphique
        self._setup_ui()

    def _setup_ui(self):
        """Configurer l'interface utilisateur."""
        self.setWindowTitle('Mise à jour TAXREF et statuts')
        self.setGeometry(300, 300, 400, 200)

        layout = QVBoxLayout()

        # Configuration barre de progression globale
        self.global_progress_label = QLabel("Progression globale")
        layout.addWidget(self.global_progress_label)
        self.global_progress_bar = QProgressBar(self)
        layout.addWidget(self.global_progress_bar)

        # Configuration barre de progression des étapes
        self.current_step_progress_label = QLabel("En attente...")
        layout.addWidget(self.current_step_progress_label)
        self.current_step_progress_bar = QProgressBar(self)
        layout.addWidget(self.current_step_progress_bar)

        # Bouton annuler
        self.cancel_button = QPushButton("Annuler")
        self.cancel_button.clicked.connect(self.cancel_process)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)
        
    def closeEvent(self, event):
        """
        Intercepte la fermeture de la fenêtre via la croix et appelle cancel_process.
        """
        self.cancel_process()  # Appelle ta méthode d’annulation
        event.accept()  # Accepte la fermeture de la fenêtre

    def cancel_process(self):
        """
        Annule le processus de téléchargement et ferme la fenêtre.
        """
        self.cancel_requested.emit()  # Émet un signal pour annuler les threads en cours
        self.update_global_progress_label("Annulation en cours...")
        self.close()

    def update_step_progress_label(self, text: str):
        """
        Met à jour le texte du label secondaire.

        :param text: Texte à afficher.
        """
        if hasattr(self, 'current_step_progress_label'):
            self.current_step_progress_label.setText(text)

    def initialize_global_bar(self):
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.total_steps})"
        )
        self.global_progress_bar.setValue(0)

    def _on_finished_save(self):
        """
        Callback appelé lorsque l'enregistrement des sources est terminé.
        """
        self.close()
        
    def update_global_progress_label(self, text: str):
        """
        Met à jour le texte du label principal.

        :param text: Texte à afficher.
        """
        if hasattr(self, 'global_progress_label'):
            self.global_progress_label.setText(text)

    def _global_increment_step(self):
        """Met à jour la barre de progression globale."""
        self.current_step += 1
        progress = int(100 * self.current_step / self.total_steps)
        self.update_global_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.total_steps})"
        )
        self.global_progress_bar.setValue(progress)

    def _step_increment_step(self, progress):
        self.current_step_progress_bar.setValue(progress)