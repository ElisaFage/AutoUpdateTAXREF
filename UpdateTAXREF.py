import pandas as pd 
import geopandas as gpd

import os
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError, HTTPError
from datetime import datetime

import json
import zipfile


from qgis.core import QgsMessageLog, Qgis

# Générer l'URL de téléchargement pour une version donnée
def get_download_url(version):
    """
    Récupère l'URL de téléchargement pour une version spécifique de TAXREF.
    Cette fonction récupère la liste des versions de TAXREF depuis le site Web du MNHN et construit un lien 
    de téléchargement basé sur le code d'archive de la version demandée.

    Args:
        version (float): La version de TAXREF pour laquelle l'URL de téléchargement est demandée.

    Returns:
        str: L'URL de téléchargement pour la version demandée.

    Raises:
        ValueError: Si la version demandée est inférieure à 1.0.
        KeyError: Si la version demandée n'est pas trouvée dans la réponse du serveur.
    """

    # Vérifier que la version demandée est valide (supérieure ou égale à 1.0)
    if version < 1.0 :
        raise ValueError(f"La version minimum de TAXREF est la 1.0, version demandée : {version}")
    
    # Lien pour obtenir la liste de toutes les versions de TAXREF
    link_allVersions = "https://taxref.mnhn.fr/taxref-web/versions/listAllVersions"

    # Récupérer les données depuis le lien
    response = urlopen(link_allVersions)
    data_json = json.loads(response.read())

    try :
        # Extraire le code d'archive pour la version demandée
        cdDocArchive = data_json[version-1]["cdDocArchive"]  # Obtenir le code d'archive pour la version
    except IndexError:
        raise ValueError(f"Version {version} non trouvée dans la liste des versions disponibles.")
    
    # Générer l'URL de téléchargement à partir du code d'archive
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
    
    """
    Filtre les lignes d'un DataFrame en fonction des critères spécifiques
    relatifs à un groupe taxonomique, à la présence d'un nom français et à la validité du taxon.

    Args:
        df (pd.DataFrame): Le DataFrame contenant les données à filtrer.
        regne (str): Le règne biologique à filtrer. Par défaut, "Plantae".
        groupe1 (str): Liste des groupes de premier niveau à filtrer. Par défaut, ["Autres"].
        groupe2 (str): Liste des groupes de deuxième niveau à filtrer. Par défaut, [""].
        groupe3 (str): Liste des groupes de troisième niveau à filtrer. Par défaut, [""].
        famille (str): Liste des familles à filtrer. Par défaut, [""].
        synonyme (bool): Indique si les synonymes doivent être inclus. Par défaut, False.

    Returns:
        pd.DataFrame: Un DataFrame filtré selon les critères spécifiés.
    """

    # Condition de filtre pour le règne biologique
    condition_regne= df['REGNE'] == regne

    # Condition de filtre pour le groupe de premier niveau
    condition_groupe = df['GROUP1_INPN'].isin(groupe1)

    # Si un groupe de deuxième niveau est spécifié, ajouter la condition correspondante
    if groupe2 != [""]:
        condition_groupe = condition_groupe & df['GROUP2_INPN'].isin(groupe2)

        # Si un groupe de troisième niveau est spécifié, ajouter la condition correspondante
        if groupe3 != [""]:
            condition_groupe = condition_groupe & df['GROUP3_INPN'].isin(groupe3)

            # Si une famille est spécifiée, ajouter la condition correspondante
            if famille != [""]:
                condition_groupe = condition_groupe & df['FAMILLE'].isin(famille)

    # Condition de présence du nom français (sur certaines valeurs spécifiques)
    condition_presence_Fr = df['FR'].isin(['P', 'E', 'S', 'C', 'I', 'J','M','B', 'D', 'G'])

    # Condition de validité du taxon : si synonyme est False, le CD_NOM doit être égal au CD_REF
    if synonyme == False:
        condition_taxon_valide = df['CD_NOM'] == df['CD_REF']
    else:
        # Si synonyme est True, on considère que tous les taxons sont valides
        condition_taxon_valide = df['CD_REF'] == df['CD_REF']

    # Appliquer toutes les conditions pour filtrer le DataFrame
    condition = condition_regne & condition_groupe & condition_presence_Fr & condition_taxon_valide
    # Filtrer le DataFrame en fonction des conditions
    df_filtre = df[condition]
    
    return df_filtre

# Supprimer certaines colonnes inutiles du DataFrame
def tri_colonnes(df:pd.DataFrame, version:int)->pd.DataFrame:
    """
    Filtre les colonnes d'un DataFrame en supprimant certaines colonnes inutiles
    et ajoute une colonne 'VERSION' avec la valeur spécifiée.

    Args:
        df (pd.DataFrame): Le DataFrame contenant les données à filtrer.
        version (int): La version à ajouter dans la colonne 'VERSION'.

    Returns:
        pd.DataFrame: Un DataFrame avec les colonnes inutiles supprimées et la colonne 'VERSION' ajoutée.
    """
    
    # Liste des colonnes à supprimer du DataFrame
    colonnes_a_supprimer = [
        'REGNE', 'PHYLUM', 'CLASSE','ORDRE',
        'SOUS_FAMILLE', 'TRIBU', 'GROUP1_INPN',
        'GROUP2_INPN', 'GROUP3_INPN', 'CD_TAXSUP',
        'CD_SUP', 'CD_BA', 'URL_INPN', 'RANG',
        'LB_NOM', 'LB_AUTEUR', 'NOM_COMPLET',
        'NOM_COMPLET_HTML', 'NOM_VERN_ENG',
        'HABITAT', 'FR', 'GF', 'MAR', 'GUA',
        'SM', 'SB', 'SPM', 'MAY', 'EPA', 'REU',
        'SA', 'TA', 'TAAF', 'PF', 'NC', 'WF',
        'CLI', 'URL']
    
    # Suppression des colonnes spécifiéesr
    df = df.drop(columns=colonnes_a_supprimer)
    # Ajout de la colonne 'VERSION' avec la valeur donnée
    df['VERSION'] = version

    return df

# Supprimer les espèces sans nom vernaculaire et les noms vernaculaires doubles 
def supprime_nom_vernaculaire(df:pd.DataFrame, layer:str)->pd.DataFrame:
    """
    Supprime les lignes avec des valeurs manquantes dans la colonne 'NOM_VERN' pour certaines couches,
    puis groupe les données par 'NOM_VERN' et conserve uniquement la ligne avec le nom valide le plus court.

    Args:
        df (pd.DataFrame): Le DataFrame contenant les données à nettoyer.
        layer (str): Le nom de la couche pour laquelle appliquer la logique de nettoyage.

    Returns:
        pd.DataFrame: Le DataFrame nettoyé avec les lignes sélectionnées.
    """
    
    # Définition des couches pour lesquelles le nettoyage des noms vernaculaires s'applique
    nom_couches = ('Amphibiens', 'Reptiles', 'Oiseaux', 'Mammifères')

    # Vérifier si la couche est dans la liste des couches définies
    if layer in nom_couches:
        # Supprimer les lignes où la colonne 'NOM_VERN' a des valeurs manquantes
        df.dropna(subset=["NOM_VERN"], inplace=True)
        # Grouper par 'NOM_VERN' et appliquer la logique pour sélectionner la ligne avec le nom valide le plus court
        df_cleaned = (
            df.groupby("NOM_VERN", group_keys=False)
            .apply(lambda row_group: row_group.loc[row_group["NOM_VALIDE"].str.len().idxmin()])
            .reset_index(drop=True))  # Réinitialiser l'index pour éviter les conflits
        
        return df_cleaned

    else :
        # Si la couche ne correspond pas à celles définies, retourner le DataFrame sans modification
        return df


def on_DownloadComplete(temp_zip_path:str,
                        version:int,
                        titles:list, regnes:list,
                        groupes1:list, groupes2:list,
                        groupes3:list, familles:list,
                        save_path:str,
                        synonyme:bool=False,
                        debug: int=0):
    
    """
    Cette fonction est appelée lorsque le téléchargement du fichier ZIP est terminé.
    Elle extrait le fichier contenant les données taxonomiques, filtre et traite les données,
    puis les enregistre sous forme de fichiers GeoPackage.

    Args:
        temp_zip_path (str): Le chemin d'accès au fichier ZIP temporaire téléchargé.
        version (int): La version de la base de données TAXREF.
        titles (list): Liste des titres des couches de taxons (ex. "Flore", "Faune").
        regnes (list): Liste des règnes pour chaque couche.
        groupes1 (list): Liste des groupes 1 pour chaque couche.
        groupes2 (list): Liste des groupes 2 pour chaque couche.
        groupes3 (list): Liste des groupes 3 pour chaque couche.
        familles (list): Liste des familles pour chaque couche.
        save_path (str): Le chemin où enregistrer les fichiers extraits et traités.
        synonyme (bool, optional): Si True, inclut les synonymes dans les résultats. Par défaut, False.
        debug (int, optional): Niveau de débogage pour afficher des informations supplémentaires. Par défaut, 0.

    Raises:
        FileNotFoundError: Si le fichier TAXREFv{version}.txt n'est pas trouvé dans l'archive ZIP.
        TypeError: Si le type de données reçu dans un chunk n'est pas un DataFrame.
    """
    
    # Si le mode debug est activé, afficher l'heure de début du processus
    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Start on_DownloadComplete ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    # Nom du fichier à ouvrir après extraction
    file_to_open = f"TAXREFv{version}.txt"

    # Ouvrir et extraire l'archive ZIP
    with zipfile.ZipFile(temp_zip_path) as zip_file :
        
        if file_to_open not in zip_file.namelist():
            raise FileNotFoundError(f"Le fichier {file_to_open} n'a pas été trouvé dans l'archive ZIP.")
        
        # Extraire le fichier ZIP dans le répertoire de sauvegarde
        zip_file.extract(file_to_open, save_path)
        
    extracted_file_path = os.path.join(save_path, file_to_open)

    # Traitement de chaque couche de taxons  
    for title, regne, groupe1, groupe2, groupe3, famille in zip(titles, regnes, groupes1, groupes2, groupes3, familles):
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Etape de lecture et de tri de la couche {title} ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})",
                                     "AutoUpdateTAXREF", level=Qgis.Info)
            
        # Lire le fichier extrait par morceaux (chunks)
        with open(extracted_file_path, 'r', encoding='utf-8') as file:
            # Lire directement le fichier dans un DataFrame pandas en flux
            df = pd.read_csv(file, delimiter='\t', dtype=str, chunksize=50000)  # Chunksize : 50,000 lignes
            
            # Traitement par morceaux pour éviter les problèmes de mémoire
            filtered_frames = []
            for chunk in df:

                # Vérifier que chaque morceau est bien un DataFrame
                if not isinstance(chunk, pd.DataFrame):
                    raise TypeError(f"TriLignes attend un DataFrame, mais a reçu {type(chunk)}")

                # Appliquer les fonctions de filtrage sur les données 
                filtered_chunk = tri_colonnes(tri_lignes(chunk, regne=regne, groupe1=groupe1,
                                                groupe2=groupe2, groupe3=groupe3, famille=famille,
                                                synonyme=synonyme), version=version)

                filtered_frames.append(filtered_chunk)

            # Combiner les morceaux filtrés en un seul DataFrame
            filtered_frames = [df for df in filtered_frames if not df.empty]
            df_filtre = pd.concat(filtered_frames, ignore_index=True)

            # Supprimer les noms vernaculaires doubles ou vides pour certains taxons
            df_filtre_nom_vern = supprime_nom_vernaculaire(df=df_filtre, layer=title)

            # Convertir le pandas.DataFrame en geopandas.GeoDataFrame
            gdf = gpd.GeoDataFrame(df_filtre_nom_vern)

            # Définir le CRS (bien que ce ne soit pas nécessaire pour les couches non-géométriques)
            if title == "Flore":
                file_save_path = os.path.join(save_path, f"{title}.gpkg")
            else :
                file_save_path = os.path.join(save_path, f"Faune.gpkg")
            # Enregistrer dans un GeoPackage
            gdf.to_file(file_save_path, layer=f"Liste {title}", driver="GPKG")
    
    # Supprimer les fichiers temporaire ZIP
    os.remove(temp_zip_path)
    os.remove(extracted_file_path)

    return