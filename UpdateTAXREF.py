import pandas as pd 
import geopandas as gpd
import numpy as np

import io
import os
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError, HTTPError
from datetime import datetime, date

import json
import zipfile

#from .ProgressDialog import ProgressDialog
from PyQt5.QtWidgets import QMessageBox #QProgressBar, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsMessageLog, Qgis

# Générer l'URL de téléchargement pour une version donnée
def get_download_url(version):

    if version < 1.0 :
        raise ValueError(f"La version minimum de TAXREF est la 1.0, version demandée : {version}")
    
    link_allVersions = "https://taxref.mnhn.fr/taxref-web/versions/listAllVersions"

    response = urlopen(link_allVersions)
    data_json = json.loads(response.read())
    cdDocArchive = data_json[version-1]["cdDocArchive"]  # Obtenir le code d'archive pour la version
    # Générer le lien de téléchargement
    link_download = "https://inpn.mnhn.fr/docs-web/docs/download/"+str(cdDocArchive)

    return link_download

# Télécharger le fichier ZIP à partir de l'URL donnée
def download_zip(link_download: str, save_path: str)-> None:

    try:
        print(f"Téléchargement depuis {link_download} ...")
        urlretrieve(link_download, save_path)
        print(f"Fichier téléchargé et sauvegardé à {save_path}")
    except HTTPError as e:
        print(f"Erreur HTTP: {e.code} - {e.reason}")
    except URLError as e:
        print(f"Erreur de connexion: {e.reason}")
    except Exception as e:
        print(f"Une erreur est survenue: {str(e)}")

    return

# Filtrer les lignes du DataFrame selon plusieurs conditions
def tri_lignes(df:pd.DataFrame,
              regne:str="Plantae",
              groupe1:str=["Autres"],
              groupe2:str=[""],
              groupe3:str=[""],
              famille:str=[""],
              synonyme:bool=False)->pd.DataFrame:
    
    condition_regne= df['REGNE'] == regne
    condition_groupe = df['GROUP1_INPN'].isin(groupe1)
    if groupe2 != [""]:
        condition_groupe = condition_groupe & df['GROUP2_INPN'].isin(groupe2)
        if groupe3 != [""]:
            condition_groupe = condition_groupe & df['GROUP3_INPN'].isin(groupe3)
            if famille != [""]:
                condition_groupe = condition_groupe & df['FAMILLE'].isin(famille)
    condition_presence_Fr = df['FR'].isin(['P', 'E', 'S', 'C', 'I', 'J','M','B', 'D', 'G'])
    if synonyme == False:
        condition_taxon_valide = df['CD_NOM'] == df['CD_REF']
    else:
        condition_taxon_valide = df['CD_REF'] == df['CD_REF']

    # Appliquer les conditions et filtrer le DataFrame
    condition = condition_regne & condition_groupe & condition_presence_Fr & condition_taxon_valide
    df_filtre = df[condition]
    
    return df_filtre

# Supprimer certaines colonnes inutiles du DataFrame
def tri_colonnes(df:pd.DataFrame, version:int)->pd.DataFrame:
    colonnes_a_supprimer = ['REGNE', 'PHYLUM', 'CLASSE', 'ORDRE', 'SOUS_FAMILLE', 'TRIBU', 'GROUP1_INPN', 'GROUP2_INPN', 'GROUP3_INPN', 'CD_TAXSUP', 'CD_SUP', 'CD_BA', 'URL_INPN', 'RANG', 'LB_NOM', 'LB_AUTEUR', 'NOM_COMPLET', 'NOM_COMPLET_HTML', 'NOM_VERN_ENG', 'HABITAT', 'FR', 'GF', 'MAR', 'GUA', 'SM', 'SB', 'SPM', 'MAY', 'EPA', 'REU', 'SA', 'TA', 'TAAF', 'PF', 'NC', 'WF', 'CLI', 'URL']  # Remplace par les noms des colonnes à supprimer
    df = df.drop(columns=colonnes_a_supprimer)
    df['VERSION'] = version

    return df

# Supprimer les espèces sans nom vernaculaire et les noms vernaculaires doubles 
def supprime_nom_vernaculaire(df:pd.DataFrame, layer:str)->pd.DataFrame:
    nom_couches = ('Amphibiens', 'Reptiles', 'Oiseaux', 'Mammifères')
    if layer in nom_couches:
        df.dropna(subset=["NOM_VERN"], inplace=True)
        df_cleaned = (
            df.groupby("NOM_VERN", group_keys=False)
            .apply(lambda row_group: row_group.loc[row_group["NOM_VALIDE"].str.len().idxmin()])
            .reset_index(drop=True))  # Réinitialiser l'index pour éviter les conflits
        
        return df_cleaned

    else :
        return df


def on_DownloadComplete(temp_zip_path:str,
                        version:int,
                        titles:list, regnes:list,
                        groupes1:list, groupes2:list,
                        groupes3:list, familles:list,
                        save_path:str,
                        synonyme:bool=False,
                        debug: int=0):
    
    #data_path = os.path.join(save_path, "Data")
    #if not os.path.exists(data_path):
    #    os.makedirs(data_path)

    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Start on_DownloadComplete ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    file_to_open = f"TAXREFv{version}.txt"

    # Ouvrir et extraire l'archive ZIP
    with zipfile.ZipFile(temp_zip_path) as zip_file :
        
        if file_to_open not in zip_file.namelist():
            raise FileNotFoundError(f"Le fichier {file_to_open} n'a pas été trouvé dans l'archive ZIP.")
        
        # Extraire le fichier ZIP dans un répertoire temporaire
        """temp_extract_dir = os.path.join(save_path, "extracted")
        if not os.path.exists(temp_extract_dir):
            os.makedirs(temp_extract_dir)"""
        
        zip_file.extract(file_to_open, save_path)
        
    extracted_file_path = os.path.join(save_path, file_to_open)
    #print(f"Fichier extrait : {extracted_file_path}")
        
    for title, regne, groupe1, groupe2, groupe3, famille in zip(titles, regnes, groupes1, groupes2, groupes3, familles):
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Etape de lecture et de tri de la couche {title} ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})",
                                     "AutoUpdateTAXREF", level=Qgis.Info)
        with open(extracted_file_path, 'r', encoding='utf-8') as file:
            # Lire directement le fichier dans un DataFrame pandas en flux
            df = pd.read_csv(file, delimiter='\t', dtype=str, chunksize=50000)  # Chunksize : 50,000 lignes
            
            #chunk par chunk pour la mémoire
            filtered_frames = []
            for chunk in df:
                #print(chunk)

                # Vérifier si df est bien un DataFrame
                if not isinstance(chunk, pd.DataFrame):
                    #print(chunk)
                    raise TypeError(f"TriLignes attend un DataFrame, mais a reçu {type(chunk)}")

                # Filtrer les lignes et colonnes 
                filtered_chunk = tri_colonnes(tri_lignes(chunk, regne=regne, groupe1=groupe1,
                                                groupe2=groupe2, groupe3=groupe3, famille=famille,
                                                synonyme=synonyme), version=version)
                #print(filtered_chunk)
                filtered_frames.append(filtered_chunk)

            # Combiner les morceaux filtrés en un seul DataFrame
            filtered_frames = [df for df in filtered_frames if not df.empty]
            #print(title)
            #print(regne, groupe1, groupe2, groupe3)
            #print(filtered_frames)
            df_filtre = pd.concat(filtered_frames, ignore_index=True)

            # On supprime les noms vernaculaires doubles ou vide dans certains taxons
            df_filtre_nom_vern = supprime_nom_vernaculaire(df=df_filtre, layer=title)

            # Convertir le pandas.DataFrame en geopandas.GeoDataFrame
            gdf = gpd.GeoDataFrame(df_filtre_nom_vern)

            # Définir le CRS (bien que ce ne soit pas nécessaire pour les couches non-géométriques)
            #gdf.crs = None
            if title == "Flore":
                file_save_path = os.path.join(save_path, f"{title}.gpkg")
            else :
                file_save_path = os.path.join(save_path, f"Faune.gpkg")
            # Enregistrer dans un GeoPackage
            gdf.to_file(file_save_path, layer=f"Liste {title}", driver="GPKG")
            #gdf.to_file("C:\\Users\\EFA\\Desktop\\TAXREF_v17_2024\\TAXREFv"+str(version)+".gpkg", driver='GPKG', layer='Status')
    
    # Supprimer les fichiers temporaire ZIP
    os.remove(temp_zip_path)
    os.remove(extracted_file_path)

    return