# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AutoUpdateTAXREFDialog
                                 A QGIS plugin
 Automatic update of the new version of TAXREF and species status
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-09-14
        git sha              : $Format:%H$
        copyright            : (C) 2024 by E. FAGE & C. ALLENE
        email                : elisa_fage@hotmail.fr
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from PyQt5.QtWidgets import (QLabel, QScrollArea,
                             QWidget, QGridLayout,
                             QCheckBox, QVBoxLayout,
                             QRadioButton, QButtonGroup,
                             QDialogButtonBox)
from PyQt5.QtCore import Qt
from .taxongroupe import TAXONS, TaxonGroupe
from .utils import print_debug_info

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'AutoUpdateTAXREF_dialog_base.ui'))


class AutoUpdateTAXREFDialog(QtWidgets.QDialog, FORM_CLASS):

    def __init__(self, parent=None, taxons: list[TaxonGroupe]=None, status_names=None):
        """Constructor."""
        super(AutoUpdateTAXREFDialog, self).__init__(parent)
        # Initialisation de l'interface utilisateur
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # Supprimer les boutons existants
        for child in self.findChildren(QtWidgets.QPushButton):
            if child.text() in ["Ok", "Annuler"]:  # Vérifie les boutons par leur texte
                child.deleteLater()

        all_taxon_titles = [taxon.title for taxon in TAXONS]
        self.taxon_titles = [taxon.title for taxon in taxons] if taxons != None else []
        self.selected_taxons = set(self.taxon_titles) # Contient les taxons selectionnés

        self.status_names = status_names
        self.selected_statuses = set(status_names) # Contient les statuts sélectionnés

        # Création d'un layout vertical pour inclure les nouveaux éléments
        layout = QVBoxLayout(self)

        self.update_taxon_choice_label = QLabel("Quel(s) taxon(s) doivent être mis à jour ?")
        layout.addWidget(self.update_taxon_choice_label)
        self.set_taxon_checkboxes(status_names, all_taxon_titles, layout)

        # Ajout de la question initiale avec deux choix
        self.update_choice_label = QLabel("Que souhaitez-vous mettre à jour ?")
        layout.addWidget(self.update_choice_label)

        # Boutons radio pour les choix
        self.radio_taxref_all = QRadioButton("TAXREF et tous les statuts")
        self.radio_status_only = QRadioButton("Seulement des statuts")
        self.radio_taxref_all.setChecked(True)
        
        # Groupe de boutons pour gérer la sélection unique
        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.radio_taxref_all)
        self.button_group.addButton(self.radio_status_only)

        layout.addWidget(self.radio_taxref_all)
        layout.addWidget(self.radio_status_only)

        # Connecter les boutons radio à une méthode pour gérer leur effet
        self.button_group.buttonClicked.connect(self.on_update_choice_changed)

        # Ajout de la phrase descriptive
        description_label = QLabel("Quel(s) statut(s) souhaitez-vous mettre à jour ?")
        layout.addWidget(description_label)

        # Création d'une zone de défilement pour les cases à cocher pour les statuts
        self.set_status_checkboxes(status_names, layout)

        # Ajout d'une ligne de boutons "Ok" et "Annuler"
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)  # Ferme la fenêtre avec "Ok"
        self.button_box.rejected.connect(self.reject)  # Ferme la fenêtre avec "Annuler"
        layout.addWidget(self.button_box)

        # Définir ce layout comme layout principal
        self.setLayout(layout)

        # Appliquer l'état initial des cases à cocher (activées ou non)
        self.update_checkboxes_state()

    def set_taxon_checkboxes(self, status_names, all_taxon_titles, layout: QVBoxLayout):
        # Création d'une zone de défilement pour les cases à cocher pour les taxons
        self.taxon_checkbox_scroll_area = QScrollArea()
        self.taxon_checkbox_scroll_area.setWidgetResizable(True)
        taxon_checkbox_container = QWidget()
        taxon_checkbox_layout = QGridLayout()

        # Stocker les QCheckBox et leurs noms associés
        self.taxon_checkboxes = {}
        if status_names:
            for i, taxon in enumerate(all_taxon_titles):
                taxon_checkbox = QCheckBox(taxon)
                taxon_in_data = taxon in self.taxon_titles
                taxon_checkbox.setChecked(taxon_in_data)  # Coché par défaut
                taxon_checkbox.setEnabled(True)  # Rendre cochable les cases
                taxon_checkbox.stateChanged.connect(self.on_taxon_checkbox_changed)
                self.taxon_checkboxes[taxon_checkbox] = taxon
                taxon_checkbox_layout.addWidget(taxon_checkbox, i // 2, i % 2)  # Deux colonnes

        taxon_checkbox_container.setLayout(taxon_checkbox_layout)
        self.taxon_checkbox_scroll_area.setWidget(taxon_checkbox_container)
        layout.addWidget(self.taxon_checkbox_scroll_area)

    def set_status_checkboxes(self,
                              status_names: list,
                              layout: QVBoxLayout):
        # Création d'une zone de défilement pour les cases à cocher pour les statuts
        self.status_checkbox_scroll_area = QScrollArea()
        self.status_checkbox_scroll_area.setWidgetResizable(True)
        status_checkbox_container = QWidget()
        status_checkbox_layout = QGridLayout()

        # Stocker les QCheckBox et leurs noms associés
        self.status_checkboxes = {}
        if status_names:
            for i, status in enumerate(status_names):
                status_checkbox = QCheckBox(status)
                status_checkbox.setChecked(True)  # Coché par défaut
                status_checkbox.stateChanged.connect(self.on_status_checkbox_changed)
                self.status_checkboxes[status_checkbox] = status
                status_checkbox_layout.addWidget(status_checkbox, i // 2, i % 2)  # Deux colonnes

        status_checkbox_container.setLayout(status_checkbox_layout)
        self.status_checkbox_scroll_area.setWidget(status_checkbox_container)
        layout.addWidget(self.status_checkbox_scroll_area)

    def reset_dialog(self):
        """Réinitialise la fenêtre de dialogue à son état initial."""
        # Réinitialiser les boutons radio
        self.radio_taxref_all.setChecked(True)

        # Réinitialiser les cases à cocher pour les taxons
        if hasattr(self, "taxon_checkboxes"):
            for taxon_checkbox in self.taxon_checkboxes:
                taxon_in_data = self.taxon_checkboxes[taxon_checkbox] in self.taxon_titles
                taxon_checkbox.setChecked(taxon_in_data)
                taxon_checkbox.setEnabled(True)

            # Vider la sélection des taxons
            self.selected_taxons.clear()
            self.selected_taxons = set(self.taxon_titles)
        
        # Réinitialiser les cases à cocher pour les statuts
        for status_checkbox in self.status_checkboxes:
            status_checkbox.setChecked(True)
            status_checkbox.setEnabled(False)

        # Vider la sélection des statuts
        self.selected_statuses.clear()
        self.selected_statuses = set(self.status_names)

    def on_taxon_checkbox_changed(self, state):
        taxon_checkbox = self.sender()
        taxon = self.taxon_checkboxes[taxon_checkbox]
        if state == Qt.Checked:
            self.selected_taxons.add(taxon)
        else:
            self.selected_taxons.discard(taxon)
    
    def on_status_checkbox_changed(self, state):
        status_checkbox = self.sender()
        status = self.status_checkboxes[status_checkbox]
        if state == Qt.Checked:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)

    def on_update_choice_changed(self, button):
        """Gère les changements dans les boutons radio."""
        self.update_checkboxes_state()

    def update_checkboxes_state(self):
        """Active ou désactive les cases à cocher en fonction du choix sélectionné."""
        if self.radio_taxref_all.isChecked():
            # Si "TAXREF et tous les statuts" est sélectionné, cocher toutes les cases et désactiver les interactions
            for checkbox in self.status_checkboxes:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
        elif self.radio_status_only.isChecked():
            # Si "Seulement des statuts" est sélectionné, permettre de cliquer sur les cases
            for checkbox in self.status_checkboxes:
                checkbox.setEnabled(True)

