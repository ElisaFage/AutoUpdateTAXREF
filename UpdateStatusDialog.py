from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QCheckBox,
                             QPushButton, QScrollArea, QWidget,
                             QGridLayout, QLabel)
from PyQt5.QtCore import Qt

class UpdateStatusDialog(QDialog):
    def __init__(self, text_lines, status_names):
        super().__init__()

        self.setWindowTitle("Mise à jour disponible")

        # Variables pour stocker les valeurs des choix utilisateur
        self.user_response = False  # False pour "Non" par défaut
        self.dont_ask_again = False
        self.selected_statuses = set(status_names) # Contient les statuts sélectionnés

        # Layout principal
        layout = QVBoxLayout()

        # Texte déroulant avec contenu configurable
        intro_text = "De potentielles mises à jour peuvent être approtées par les sources suivantes :"
        html_text = f"<p>{intro_text}</p><ul>" + "".join(f"<li>{line}</li>" for line in text_lines) + "</ul>"
        #full_text = intro_text + "\n\n" + "\n".join(text_lines)
        #self.scrollable_text = QTextEdit(full_text)
        self.scrollable_text = QTextEdit()
        self.scrollable_text.setHtml(html_text)
        self.scrollable_text.setReadOnly(True)
        self.scrollable_text.setFixedHeight(50)  # Limite initiale de la hauteur
        layout.addWidget(self.scrollable_text)

        # Bouton pour montrer/cacher le texte
        self.toggle_button = QPushButton("Montrer le texte")
        self.toggle_button.clicked.connect(self.toggle_text)
        layout.addWidget(self.toggle_button)

        # Phrase descriptive pour les statuts
        description_label = QLabel("Quel(s) statut(s) souhaitez-vous mettre à jour ?")
        layout.addWidget(description_label)

        # Section des cases à cocher
        self.checkbox_scroll_area = QScrollArea()
        self.checkbox_scroll_area.setWidgetResizable(True)
        checkbox_container = QWidget()
        checkbox_layout = QGridLayout()

        self.checkboxes = {}  # Pour stocker les QCheckBox et leurs noms associés
        for i, status in enumerate(status_names):
            checkbox = QCheckBox(status)
            checkbox.setChecked(True)  # Cocher par défaut
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            self.checkboxes[checkbox] = status
            checkbox_layout.addWidget(checkbox, i // 2, i % 2)  # Deux colonnes

        checkbox_container.setLayout(checkbox_layout)
        self.checkbox_scroll_area.setWidget(checkbox_container)
        layout.addWidget(self.checkbox_scroll_area)

        # Case à cocher pour ne plus reproposer
        self.checkbox = QCheckBox("Ne plus me reproposer cette mise à jour")
        self.checkbox.stateChanged.connect(self.on_checkbox_state_changed)
        layout.addWidget(self.checkbox)

        # Boutons Oui et Non
        button_layout = QHBoxLayout()
        self.yes_button = QPushButton("Oui")
        self.yes_button.clicked.connect(self.on_yes_clicked)
        button_layout.addWidget(self.yes_button)

        self.no_button = QPushButton("Non")
        self.no_button.clicked.connect(self.on_no_clicked)
        self.no_button.setDefault(True)  # Définit "Non" comme bouton par défaut
        button_layout.addWidget(self.no_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # État du texte (réduit par défaut)
        self.text_expanded = False

    def toggle_text(self):
        if self.text_expanded:
            self.scrollable_text.setFixedHeight(50)  # Réduit la hauteur
            self.toggle_button.setText("Montrer le texte")
        else:
            self.scrollable_text.setFixedHeight(150)  # Augmente la hauteur pour montrer tout le texte
            self.toggle_button.setText("Cacher le texte")
        self.text_expanded = not self.text_expanded

    def on_checkbox_changed(self, state):
        checkbox = self.sender()
        status = self.checkboxes[checkbox]
        if state == Qt.Checked:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)

    def on_checkbox_state_changed(self, state):
        self.dont_ask_again = (state == Qt.Checked)

    def on_yes_clicked(self):
        self.user_response = True
        self.accept()

    def on_no_clicked(self):
        self.user_response = False
        self.accept()

class SaveXlsxDialog(QDialog):

    def __init__(self):
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

        button_layout = QHBoxLayout()
        self.yes_button = QPushButton("Oui")
        self.yes_button.clicked.connect(self.on_yes_clicked)
        button_layout.addWidget(self.yes_button)

        self.no_button = QPushButton("Non")
        self.no_button.clicked.connect(self.on_no_clicked)
        self.no_button.setDefault(True)  # Définit "Non" comme bouton par défaut
        button_layout.addWidget(self.no_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def on_yes_clicked(self):
        self.user_response = True
        self.accept()

    def on_no_clicked(self):
        self.user_response = False
        self.accept()


# Fonction pour ouvrir la boîte de dialogue et récupérer les valeurs
def show_update_dialog(text_lines):
    app = QApplication([])  # Crée l'application
    dialog = UpdateStatusDialog(text_lines)  # Crée la boîte de dialogue avec le texte personnalisé

    if dialog.exec_() == QDialog.Accepted:
        # Récupération des réponses utilisateur
        print("Réponse de l'utilisateur:", "Oui" if dialog.user_response else "Non")
        #print("Ne plus reproposer:", dialog.dont_ask_again)
    
    app.exit()

if __name__ == "__main__":
    # Exécuter le dialogue avec un texte personnalisé pour la démonstration
    text_content = [
        "Mise à jour 1.1 : Améliorations de la stabilité.",
        "Correction de plusieurs bugs.",
        "Nouvelles fonctionnalités ajoutées.",
        "Compatibilité étendue pour les appareils récents."
    ]
    show_update_dialog(text_content)