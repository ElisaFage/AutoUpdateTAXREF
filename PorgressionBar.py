import sys
import time
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton

class ProgressDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Chargement en cours")
        self.resize(300, 100)

        # Layout principal
        layout = QVBoxLayout()

        # Label pour indiquer l'état de la progression
        self.label = QLabel("Initialisation...")
        layout.addWidget(self.label)

        # Barre de chargement
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)  # Définit la progression de 0 à 100%
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def update_progress(self, value):
        # Met à jour la barre de progression et le label
        self.progress_bar.setValue(value)
        self.label.setText(f"Progression : {value}%")

# Fonction pour afficher la fenêtre de progression et effectuer la boucle de chargement
def show_progress_dialog():
    app = QApplication(sys.argv)
    dialog = ProgressDialog()
    dialog.show()

    progress_value = 0

    n=20
    # Boucle de chargement en 20 étapes avec un délai de 3 secondes
    for i in range(n):
        # Incrémente la progression de 5%
        progress_value += int(round(100/n))
        dialog.update_progress(progress_value)

        # Rafraîchit l'interface pour refléter les changements
        app.processEvents()

        # Attente de 3 secondes avant la prochaine étape
        time.sleep(3)

    # Ferme la boîte de dialogue une fois le chargement terminé
    dialog.accept()
    app.exit()

if __name__ == "__main__":
    show_progress_dialog()
