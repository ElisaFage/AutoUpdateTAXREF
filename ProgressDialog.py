from PyQt5.QtWidgets import QProgressBar, QVBoxLayout, QDialog
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import Qt

class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Mise à jour en cours")
        self.setMinimumWidth(300)

        # Créer la barre de progression
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        
        # Créer le layout et y ajouter la barre de progression
        layout = QVBoxLayout()
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

# Fonction principale de mise à jour
def update_data():
    # Créer la fenêtre de progression
    progress_dialog = ProgressDialog()
    progress_dialog.show()

    # Exemple d'une boucle de mise à jour où tu mets à jour ta donnée
    total_steps = 100  # Remplace par le nombre réel d'étapes
    for i in range(total_steps):
        # Simuler une étape de mise à jour
        # ...

        # Mettre à jour la barre de progression
        progress_dialog.update_progress(int((i+1) / total_steps * 100))

        # Permettre à l'interface de rester réactive
        QCoreApplication.processEvents()

    # Fermer la fenêtre de progression une fois la mise à jour terminée
    progress_dialog.close()
