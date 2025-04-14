from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QCheckBox,
                             QPushButton, QScrollArea, QWidget,
                             QGridLayout, QLabel, QMessageBox,
                             QFileDialog)
from PyQt5.QtCore import Qt

class UpdateTAXREFDialog(QDialog):

    def __init__(self, version: int):
        
        super().__init__()

        self.setWindowTitle("Mise à jour disponible")

        # Variables internes de réponse utilisateur
        self.user_response = False  # False pour "Non" par défaut
        self.dont_ask_again = False

        # Layout principal
        layout = QVBoxLayout()

        self.text = QLabel(f'Une nouvelle version de TAXREF (version {version}) est disponible.\nVoulez vous mettre TAXREF à jour ?')
        layout.addWidget(self.text)

        # Boutons Oui et Non
        # Crée un layout pour les boutons
        button_layout = QHBoxLayout()

        # Crée un bouton "Oui"
        self.yes_button = QPushButton("Oui")
        # Connecte le click sur le bouton à on_yes_clicked
        self.yes_button.clicked.connect(self.on_yes_clicked)
        # Ajoute le bouton "Oui" au layout des boutons
        button_layout.addWidget(self.yes_button)

        # Crée un bouton "Non"
        self.no_button = QPushButton("Non")
        # Connecte le click sur le bouton à on_no_clicked
        self.no_button.clicked.connect(self.on_no_clicked)
        # Définit "Non" comme bouton par défaut
        self.no_button.setDefault(True)
        # Ajoute le bouton "Non" au layout des boutons
        button_layout.addWidget(self.no_button)

        # Ajout du layout des boutons au layout principal
        layout.addLayout(button_layout)
        # Application du layout à la boîte de dialogue
        self.setLayout(layout)

    def on_yes_clicked(self):
        """
        Enregistre une réponse positive et ferme la boîte de dialogue.
        """
        self.user_response = True
        self.accept()

    def on_no_clicked(self):
        """
        Enregistre une réponse négative et ferme la boîte de dialogue.
        """
        self.user_response = False
        self.accept()

class UpdateStatusDialog(QDialog):
    """
    Boîte de dialogue permettant à l'utilisateur de confirmer une mise à jour de statuts
    et de sélectionner les statuts concernés.

    Attributs :
        user_response (bool) : Réponse de l'utilisateur (True si "Oui", False si "Non").
        dont_ask_again (bool) : Indique si la boîte ne doit plus être affichée.
        selected_statuses (set) : Statuts sélectionnés par l'utilisateur.
    """
    def __init__(self, text_lines, status_names):
        """
        Initialise la boîte de dialogue avec le texte informatif et les statuts disponibles.

        Args:
            text_lines (list of str) : Lignes de texte listant les sources de mise à jour.
            status_names (list of str) : Liste des noms de statuts sélectionnables.
        """
        super().__init__()

        self.setWindowTitle("Mise à jour disponible")

        # Variables internes de réponse utilisateur
        self.user_response = False  # False pour "Non" par défaut
        self.dont_ask_again = False
        self.selected_statuses = set(status_names) # Contient les statuts sélectionnés

        # Layout principal
        layout = QVBoxLayout()

        # Texte introductif formaté en HTML
        intro_text = "De potentielles mises à jour peuvent être approtées par les sources suivantes :"
        html_text = f"<p>{intro_text}</p><ul>" + "".join(f"<li>{line}</li>" for line in text_lines) + "</ul>"

        self.scrollable_text = QTextEdit()
        self.scrollable_text.setHtml(html_text)
        self.scrollable_text.setReadOnly(True)
        # Limite initiale de la hauteur
        self.scrollable_text.setFixedHeight(50)
        layout.addWidget(self.scrollable_text)

        # Bouton pour agrandir/réduire le texte
        self.toggle_button = QPushButton("Montrer le texte")
        self.toggle_button.clicked.connect(self.toggle_text)
        layout.addWidget(self.toggle_button)

        # Label descriptif
        description_label = QLabel("Quel(s) statut(s) souhaitez-vous mettre à jour ?")
        layout.addWidget(description_label)

        # Scroll area contenant les cases à cocher
        # Crée une zone scrollable pour le future container de checkbox
        self.checkbox_scroll_area = QScrollArea()
        # Permet de modifier la taille de la zone
        self.checkbox_scroll_area.setWidgetResizable(True)
        # Crée un conatiner pour les future layout à checkbox
        checkbox_container = QWidget()
        # Crée un layout pour afficher les checkbox
        checkbox_layout = QGridLayout()

        # Création dynamique des cases à cocher
        self.checkboxes = {}  # Pour stocker les QCheckBox et leurs noms associés
        # Boucle des checkbox pour chaque statut
        for i, status in enumerate(status_names):
            # Crée une checkbox avec le nom status
            checkbox = QCheckBox(status)
            # Cocher par défaut
            checkbox.setChecked(True) 
            # Connecte le changement détat de la checkbox à on_checkbox_changed
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            # Ajoute la checkbox à l'iterable checkboxes
            self.checkboxes[checkbox] = status
            # Ajoute la checkbox au layout
            checkbox_layout.addWidget(checkbox, i // 2, i % 2)  # Deux colonnes

        # Ajoute le layout a checkbox dans un container
        checkbox_container.setLayout(checkbox_layout)
        # Ajoute ce container à une zone scrollable
        self.checkbox_scroll_area.setWidget(checkbox_container)
        # Ajoute le tout au layout principal
        layout.addWidget(self.checkbox_scroll_area)

        # Case à cocher pour ne plus reproposer
        self.checkbox = QCheckBox("Ne plus me reproposer cette mise à jour")
        # Connecte le cochage/décochage de la case à on_checkbox_state_changed
        self.checkbox.stateChanged.connect(self.on_checkbox_state_changed)
        layout.addWidget(self.checkbox)

        # Boutons Oui et Non
        # Crée un layout pour les boutons
        button_layout = QHBoxLayout()

        # Crée un bouton "Oui"
        self.yes_button = QPushButton("Oui")
        # Connecte le click sur le bouton à on_yes_clicked
        self.yes_button.clicked.connect(self.on_yes_clicked)
        # Ajoute le bouton "Oui" au layout des boutons
        button_layout.addWidget(self.yes_button)

        # Crée un bouton "Non"
        self.no_button = QPushButton("Non")
        # Connecte le click sur le bouton à on_no_clicked
        self.no_button.clicked.connect(self.on_no_clicked)
        # Définit "Non" comme bouton par défaut
        self.no_button.setDefault(True)
        # Ajoute le bouton "Non" au layout des boutons
        button_layout.addWidget(self.no_button)

        # Ajout du layout des boutons au layout principal
        layout.addLayout(button_layout)
        # Application du layout à la boîte de dialogue
        self.setLayout(layout)

        # État du texte (réduit par défaut)
        self.text_expanded = False

    def toggle_text(self):
        """
        Agrandit ou réduit la zone de texte selon son état actuel.
        """
        if self.text_expanded:
            # Réduit la hauteur
            self.scrollable_text.setFixedHeight(50)  
            self.toggle_button.setText("Montrer le texte")
        else:
            # Augmente la hauteur pour montrer tout le texte
            self.scrollable_text.setFixedHeight(150)  
            self.toggle_button.setText("Cacher le texte")
        self.text_expanded = not self.text_expanded

    def on_checkbox_changed(self, state):
        """
        Met à jour la liste des statuts sélectionnés en fonction des cases cochées.

        Args:
            state (int): État de la case (Qt.Checked ou Qt.Unchecked).
        """
        checkbox = self.sender()
        status = self.checkboxes[checkbox]
        if state == Qt.Checked:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)

    def on_checkbox_state_changed(self, state):
        """
        Met à jour le drapeau `dont_ask_again` selon l'état de la case à cocher.

        Args:
            state (int): État de la case (Qt.Checked ou Qt.Unchecked).
        """
        self.dont_ask_again = (state == Qt.Checked)

    def on_yes_clicked(self):
        """
        Enregistre une réponse positive et ferme la boîte de dialogue.
        """
        self.user_response = True
        self.accept()

    def on_no_clicked(self):
        """
        Enregistre une réponse négative et ferme la boîte de dialogue.
        """
        self.user_response = False
        self.accept()

class SaveXlsxDialog(QDialog):
    """
    Boîte de dialogue simple demandant à l'utilisateur s'il souhaite sauvegarder
    les listes de statuts au format CSV/Excel.

    Attributs :
        user_response (bool) : Réponse de l'utilisateur (True si "Oui", False sinon).
    """

    def __init__(self):
        """
        Initialise la boîte de dialogue avec un message d'information et deux boutons de réponse.
        """
        super().__init__()
        self.setWindowTitle("Mise à jour disponible")

        # Variables pour stocker les valeurs des choix utilisateur
        self.user_response = False

        # Layout principal
        layout = QVBoxLayout()

        # Texte déroulant avec contenu configurable
        intro_text = "Souhaitez-vous enregistrer les listes de chaque statut au format CSV ?"
        self.scrollable_text = QTextEdit(intro_text)
        layout.addWidget(self.scrollable_text)

        # Boutons Oui et Non
        # Crée un layout pour les boutons
        button_layout = QHBoxLayout()

        # Crée un bouton "Oui"
        self.yes_button = QPushButton("Oui")
        # Connecte le click sur le bouton à on_yes_clicked
        self.yes_button.clicked.connect(self.on_yes_clicked)
        # Ajoute le bouton "Oui" au layout des boutons
        button_layout.addWidget(self.yes_button)

        # Crée un bouton "Non"
        self.no_button = QPushButton("Non")
        # Connecte le click sur le bouton à on_no_clicked
        self.no_button.clicked.connect(self.on_no_clicked)
        # Définit "Non" comme bouton par défaut
        self.no_button.setDefault(True)
        # Ajoute le bouton "Non" au layout des boutons
        button_layout.addWidget(self.no_button)

        # Ajout du layout des boutons au layout principal
        layout.addLayout(button_layout)
        # Application du layout à la boîte de dialogue
        self.setLayout(layout)

    def on_yes_clicked(self):
        """
        Gère le clic sur "Oui" : enregistre la réponse et ferme la boîte.
        """
        self.user_response = True
        self.accept()

    def on_no_clicked(self):
        """
        Gère le clic sur "Non" : enregistre la réponse et ferme la boîte.
        """
        self.user_response = False
        self.accept()

def ask_update(version: int):
    """
    Affiche une boîte de dialogue demandant à l'utilisateur s'il souhaite mettre à jour la version de TAXREF.

    Paramètres :
        version (int) : Numéro de la nouvelle version disponible de TAXREF.

    Retourne :
        bool : True si l'utilisateur accepte la mise à jour, False sinon.
    """
    
    # Initialise la fenêtre

    ask_update_dialog = UpdateTAXREFDialog(version)
    ask_dialog_result = ask_update_dialog.exec()

    do_update = ask_update_dialog.user_response

    if ask_dialog_result == QDialog.Accepted and do_update :
        return do_update
    
    return False

def ask_save_excel():
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
    save_excel = save_excel_dialog.user_response

    # Si l'utilisateur accepte, on lui demande le dossier de sauvegarde
    if save_dialog_result == QDialog.Accepted and save_excel:
        folder = QFileDialog.getExistingDirectory(None, "Sélectionnez un dossier pour sauvegarder le fichier")
    else:
        folder = ""
        
    return save_excel, folder