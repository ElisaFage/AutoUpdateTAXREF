from PyQt5.QtWidgets import QMessageBox

# Crée une fenêtre pour demander à l'utilisateur si il veux ou non faire la mise à jour de TAXREF
def AskUpdate(version: int):
    # Initialise la fenêtre
    msg_box = QMessageBox()
    # Fenetre de question
    msg_box.setIcon(QMessageBox.Question)
    # Prépare le titre de la fenêtre
    msg_box.setWindowTitle('Confirmation de la Mise à jour de TAXREF')
    # Pose la question
    msg_box.setText(f'Une nouvelle version de TAXREF (version {version}) est disponible.\nVoulez vous mettre TAXREF à jour ?')
    # Initialise les choix de réponse
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    # Attribut une réponse par défaut
    msg_box.setDefaultButton(QMessageBox.No)
    
    # Génère et affiche la fenêtre 
    result = msg_box.exec_()

    # Renvoie la réponse de l'utilisateur
    if result == QMessageBox.Yes:
        to_return = True
    else:
        to_return = False

    return to_return
    
# Demande pour garder les synonymes
"""def AskSynonyme():
    # Initialise la fenêtre
    msg_box = QMessageBox()
    # Fenetre de question
    msg_box.setIcon(QMessageBox.Question)
    # Prépare le titre de la fenêtre
    msg_box.setWindowTitle('Conservation des synonymes')
    # Pose la question
    msg_box.setText(f'Il est possible de conserver les anciens nom en plus des nouveaux noms de réference de la dernière version de TAXREF.\nVoulez vous garder les anciens noms ?\n Attention la base de données sera plus lourde, ce qui pourrait entraîner des ralentissements.')
    # Initialise les choix de réponse
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    # Attribut une réponse par défaut
    msg_box.setDefaultButton(QMessageBox.No)
    
    # Génère et affiche la fenêtre 
    result = msg_box.exec_()

    # Renvoie la réponse de l'utilisateur
    if result == QMessageBox.Yes:
        to_return = True
    else:
        to_return = False
    
    return to_return """

"""def AskCSV():
    # Initialise la fenêtre
    msg_box = QMessageBox()
    # Fenetre de question
    msg_box.setIcon(QMessageBox.Question)
    # Prépare le titre de la fenêtre
    msg_box.setWindowTitle('Conservation des synonymes')
    # Pose la question
    msg_box.setText(f'Il est possible de conserver les anciens nom en plus des nouveaux noms de réference de la dernière version de TAXREF.\nVoulez vous garder les anciens noms ?\n Attention la base de données sera plus lourde, ce qui pourrait entraîner des ralentissements.')
    # Initialise les choix de réponse
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    # Attribut une réponse par défaut
    msg_box.setDefaultButton(QMessageBox.No)
    
    # Génère et affiche la fenêtre 
    result = msg_box.exec_()

    # Renvoie la réponse de l'utilisateur
    if result == QMessageBox.Yes:
        to_return = True
    else:
        to_return = False

    return to_return """
