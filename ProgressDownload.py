import pandas as pd

from PyQt5.QtWidgets import (
    QApplication,  QWidget, QVBoxLayout,
    QProgressBar, QPushButton, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from qgis.core import QgsMessageLog, Qgis

from .UpdateThreadClasses import (
    GetURLThread,
    DownloadThread,
    SaveTaxrefThread,
    GetStatusThread,
    SaveSourcesThread,
)


class DownloadWindow(QWidget):
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
    taxon_titles = [
        "Flore", "Amphibiens", "Reptiles", "Oiseaux", "Mammifères",
        "Lépidoptères", "Odonates", "Coléoptères", "Orthoptères"
    ]
    taxon_regnes = [
        "Plantae", "Animalia", "Animalia", "Animalia", "Animalia",
        "Animalia", "Animalia", "Animalia", "Animalia"
    ]
    taxon_groupes_1 = [
        ["Algues", "Trachéophytes", "Bryophytes"],
        ["Chordés"], ["Chordés"], ["Chordés"], ["Chordés"],
        ["Arthropodes"], ["Arthropodes"], ["Arthropodes"], ["Arthropodes"]
    ]
    taxon_groupes_2 = [
        [""],
        ["Amphibiens"], ["Reptiles"], ["Oiseaux"], ["Mammifères"],
        ["Insectes"], ["Insectes"], ["Insectes"], ["Insectes"]
    ]
    taxon_groupes_3 = [
        [""],
        [""], [""], [""], [""],
        ["Lépidoptères"], ["Odonates"], ["Coléoptères"], ["Orthoptères"]
    ]
    taxon_famille = [
        [""],
        [""], [""], [""], [""],
        [
            "Papilionidae", "Pieridae", "Nymphalidae", "Satyrinae",
            "Lycaenidae", "Hesperiidae", "Zygaenidae"
        ],
        [""],
        [
            "Carabidae", "Hydrophilidae", "Sphaeritidae", "Histeridae",
            "Ptiliidae", "Agyrtidae", "Leiodidae", "Staphylinidae",
            "Lucanidae", "Trogidae", "Scarabaeidae", "Eucinetidae",
            "Clambidae", "Scirtidae", "Buprestidae", "Elmidae", "Dryopidae",
            "Cerophytidae", "Eucnemidae", "Throscidae", "Elateridae",
            "Lycidae", "Cantharidae", "Derodontidae", "Nosodendridae",
            "Dermestidae", "Endecatomidae", "Bostrichidae", "Ptinidae",
            "Lymexylidae", "Phloiophilidae", "Trogossitidae", "Thanerocleridae",
            "Cleridae", "Acanthocnemidae", "Melyridae", "Malachiidae",
            "Sphindidae", "Nitidulidae", "Monotomidae", "Phloeostichidae",
            "Silvanidae", "Cucujidae", "Laemophloeidae", "Cryptophagidae",
            "Erotylidae", "Biphyllidae", "Bothrideridae", "Cerylonidae",
            "Alexiidae", "Endomychidae", "Corylophidae", "Latridiidae",
            "Mycetophagidae", "Ciidae", "Tetratomidae", "Melandryidae",
            "Zopheridae", "Mordellidae", "Tenebrionidae", "Prostomidae",
            "Oedemeridae", "Pythidae", "Pyrochroidae", "Salpingidae",
            "Aderidae", "Scraptiidae", "Cerambycidae", "Chrysomelidae",
            "Anthribidae", "Brentidae", "Dryophthoridae", "Curculionidae"
        ],
        [
            "Acrididae", "Gryllidae", "Gryllotalpidae", "Mogoplistida",
            "Myrmecophilidae", "Pamphagidae", "Phalangopsidae",
            "Pyrgomorphidae", "Rhaphidophoridae", "Tetrigidae",
            "Tettigoniidae", "Tridactylidae", "Trigonidiidae"
        ]
    ]

    def __init__(self, path: str, status_ids: list,
                 version: int = None,
                 synonyme: bool = False,
                 new_version: bool = False,
                 new_status: bool = False,
                 new_sources: pd.DataFrame = pd.DataFrame(columns=["id", "fullCitation"]),
                 save_excel: bool = False,
                 folder: str = "",
                 faune: bool = True,
                 flore: bool = True,
                 debug: int = 0):
        """
        Initialise la fenêtre de téléchargement de TAXREF.

        :param path: Chemin de sauvegarde.
        :param status_ids: Liste des identifiants de statut.
        :param version: Version du fichier TAXREF.
        :param synonyme: Prise en compte des synonymes.
        :param new_version: Indique si une nouvelle version doit être téléchargée.
        :param new_status: Indique si les statuts doivent être mis à jour.
        :param new_sources: DataFrame contenant les nouvelles sources.
        :param save_excel: Sauvegarde dans un fichier Excel.
        :param folder: Dossier de sauvegarde du fichier Excel.
        :param faune: Téléchargement des données de faune si True.
        :param flore: Téléchargement des données de flore si True.
        :param debug: Niveau de débogage.
        """
        super().__init__()

        # Définition des paramètres
        self.save_path = path
        self.status_ids = status_ids
        self.version = version
        self.synonyme = synonyme
        self.new_version = new_version
        self.new_status = new_status
        self.new_sources = new_sources
        self.save_excel = save_excel
        self.folder_excel = folder
        self.debug = debug
        
        # Initialisation des attributs de suivi
        self.file_path = None
        self.status_df = None
        self.status_download_counter = 0
        self.status_counter = 0

        # Compteurs et suivi d'étapes
        self.current_step = 0
        self.total_steps = 6 if new_version else 3 if new_status else 1

        # Filtrer les taxons selon les paramètres 'faune' et 'flore'
        if not faune:
            self._filter_taxa("Animalia")

        if not flore:
            self._filter_taxa("Plantae")

        self._setup_ui()

        # Démarrage initial selon les paramètres
        if new_version:
            self._start_get_url()
        elif new_status:
            self.__start_download_status()
        else:
            self.__start_save_sources()

    def _filter_taxa(self, regne: str):
        """Filtrer les taxons par règne."""
        indices = [i for i, r in enumerate(self.taxon_regnes) if r == regne]
        for attr in ['taxon_titles', 'taxon_regnes', 'taxon_groupes_1',
                     'taxon_groupes_2', 'taxon_groupes_3', 'taxon_famille']:
            setattr(self, attr, [v for i, v in enumerate(getattr(self, attr)) if i not in indices])

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

    def cancel_process(self):
        """
        Annule le processus de téléchargement et ferme la fenêtre.
        """
        self.cancel_requested.emit()  # Émet un signal pour annuler les threads en cours
        self.update_global_progress_label("Annulation en cours...")
        self.close()

    def update_global_progress_label(self, text):
        """
        Met à jour le texte du label principal.

        :param text: Texte à afficher.
        """
        if hasattr(self, 'global_progress_label'):
            self.global_progress_label.setText(text)

    def update_step_progress_label(self, text):
        """
        Met à jour le texte du label secondaire.

        :param text: Texte à afficher.
        """
        if hasattr(self, 'current_step_progress_label'):
            self.current_step_progress_label.setText(text)

    def _start_get_url(self):
        """
        Démarre le thread permettant de récupérer l'URL de téléchargement.
        """
        self.get_url_thread = GetURLThread(self.version)
        self.get_url_thread.finished.connect(self._on_url_found)
        self.cancel_requested.connect(self.get_url_thread.terminate)  # Connecte le signal d'annulation
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.n_step})"
        )
        self.get_url_thread.start()

    def _on_url_found(self, url):
        """
        Callback appelé lorsque l'URL de téléchargement est récupérée.

        :param url: URL récupérée.
        """
        self.file_url = url
        self._increment_step()
        self._start_download()

    def _start_download(self):
        """
        Démarre le thread de téléchargement du fichier TAXREF.
        """
        self.download_thread = DownloadThread(self.url)
        self.download_thread.progress.connect(self.current_step_progress_bar.setValue)
        self.download_thread.finished.connect(self._on_download_complete)
        self.cancel_requested.connect(self.download_thread.terminate)
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.n_step})"
        )
        self.update_global_progress_label("Téléchargement de TAXREF en cours...")
        self.download_thread.start()

    def _on_download_complete(self, file_path):
        """
        Callback appelé lorsque le téléchargement est terminé.

        :param file_path: Chemin du fichier téléchargé.
        """
        self.file_path = file_path
        self._increment_step()
        self._start_save_taxref()

    def _start_save_taxref(self):
        """
        Démarre le thread de sauvegarde des données TAXREF.
        """
        self.save_taxref_thread = SaveTaxrefThread(
            self.file_path,
            self.version,
            self.taxon_titles,
            self.taxon_regnes,
            self.taxon_groupes_1,
            self.taxon_groupes_2,
            self.taxon_groupes_3,
            self.taxon_famille,
            self.save_path,
            self.synonyme
        )
        self.save_taxref_thread.finished.connect(self._on_taxref_saved)
        self.cancel_requested.connect(self.save_taxref_thread.terminate)
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.n_step})"
        )
        self.save_taxref_thread.start()

    def _on_taxref_saved(self):
        """
        Callback appelé lorsque l'enregistrement des données TAXREF est terminé.
        """
        self._increment_step()
        self._start_download_status()

    def _start_download_status(self):
        """
        Démarre le thread de téléchargement des statuts.
        """
        self.get_status_thread = GetStatusThread(
            self.save_path,
            self.taxon_titles,
            self.status_ids,
            self.save_excel,
            self.folder_excel,
            debug=self.debug
        )
        self.get_status_thread.progress.connect(self.current_step_progress_bar.setValue)
        self.get_status_thread.finished.connect(self._start_save_sources)
        self.cancel_requested.connect(self.get_status_thread.termination_process)
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.n_step})"
        )
        self.update_global_progress_label("Téléchargement des statuts en cours...")
        self.get_status_thread.start()

    def _start_save_sources(self):
        """
        Démarre le thread de sauvegarde des sources.
        """
        self._increment_step()
        self.update_global_progress_label("Téléchargement des statuts terminé")

        QgsMessageLog.logMessage("In start save sources", "AutoUpdateTAXREF", level=Qgis.Info)
        self.save_sources_thread = SaveSourcesThread(
            self.save_path, self.new_version, self.new_sources
        )
        self.save_sources_thread.finished.connect(self._on_sources_saved)
        self.cancel_requested.connect(self.save_sources_thread.terminate)
        self.update_step_progress_label(
            f"Progression globale (étapes {int(self.current_step + 1)}/{self.total_steps})"
        )
        self.save_sources_thread.start()

    def _on_sources_saved(self):
        """
        Callback appelé lorsque l'enregistrement des sources est terminé.
        """
        QgsMessageLog.logMessage("In sources saved", "AutoUpdateTAXREF", level=Qgis.Info)
        self._increment_step()
        self.close()

    def _increment_step(self):
        """Met à jour la barre de progression globale."""
        self.current_step += 1
        progress = int(100 * self.current_step / self.total_steps)
        self.global_progress_bar.setValue(progress)