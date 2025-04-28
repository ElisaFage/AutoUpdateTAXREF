import pandas as pd 
import geopandas as gpd
import re

import os
import requests
from typing import List, Tuple, Dict

from .utils import (print_debug_info, get_file_save_path,
                    time_decorator, save_dataframe,
                    load_layer_as_dataframe, list_layers_from_gpkg)
from .taxongroupe import (TaxonGroupe, OISEAUX)
from .statustype import (StatusType, STATUS_TYPES,
                          LUTTE_CONTRE_ESPECES, 
                          LISTE_ROUGE_NATIONALE, LISTE_ROUGE_REGIONALE,
                          PROTECTION_DEPARTEMENTALE, PROTECTION_NATIONALE, PROTECTION_REGIONALE,
                          PLAN_NATIONAL_ACTION, PRIORITE_ACTION_PUBLIQUE_NATIONALE,
                          DETERMINANT_ZNIEFF, DIRECTIVE_HABITAT, DIRECTIVE_OISEAUX)

# Supprime les lignes non nécessaires dans le pandas dataframe
def filter_by_cd_ref(df_concat: pd.DataFrame, taxons: List[TaxonGroupe], path: str) -> pd.DataFrame:
    """
    Filtre les données en fonction des références taxonomiques et exclut les enregistrements hors DOM-TOM.

    Args:
        df_concat (pd.DataFrame): Le DataFrame concaténé contenant les données taxonomiques à filtrer.
        taxonTitles (List[TaxonGroupe]): Liste des titres des taxons à traiter (ex. "Flore", "Faune").
        path (str): Le chemin d'accès au répertoire contenant les fichiers GPKG.

    Returns:
        dict: Un dictionnaire avec les titres de taxons comme clés et les DataFrames filtrés comme valeurs.
    """

    # Liste des DOM-TOM à exclure
    domtom = ["Guadeloupe", "Guyane", "Martinique", "Réunion", "Mayotte"]

    # Filtrer les lignes où 'taxon_referenceId' correspond à 'taxon_id'
    df_concat = df_concat[df_concat['taxon_referenceId'].astype(int) == df_concat["taxon_id"].astype(int)]
    # Charger les fichiers GPKG pour chaque titre une seule fois et les stocker dans un dictionnaire
    
    file_path = get_file_save_path(path)
    dict_df_out = {}
    for taxon in taxons:
        # Définir le chemin du fichier GPKG en fonction du titre du taxon
        
        # Charger le fichier GPKG dans un DataFrame et stocker dans le dictionnaire
        df_ref = load_layer_as_dataframe(file_path, f"Liste {taxon.title}")
        #pd.DataFrame(gpd.read_file(file_path, layer=f"Liste {title}"))

        # Filtrer df_concat pour ne conserver que les lignes dont 'taxon_referenceId' est dans 'CD_REF'
        df_out = df_concat[df_concat['taxon_referenceId'].astype(int).isin(df_ref['CD_REF'].astype(int).values)]
        # Exclure les lignes correspondant à des localisations dans les DOM-TOM
        status_no_domtom = df_out[~df_out["locationName"].isin(domtom)]
        # Stocker le DataFrame filtré dans le dictionnaire
        dict_df_out[taxon.title] = status_no_domtom

    return dict_df_out

# Extrait un status_code en fonction de 4 conditions
def extract_status_code(row, status: StatusType, currentTaxon: str, oiseauxKeywords: List[str]):
    """
    Extrait un code de statut basé sur plusieurs conditions et informations provenant de la ligne de données.

    Args:
        row (dict): Une ligne de données contenant les informations à analyser.
        statusId (str): L'ID du statut qui influence l'extraction.
        currentTaxon (str): Le nom du taxon actuellement traité (utilisé pour "Oiseaux").
        departements (list): Liste des départements, bien que non utilisée dans cette version de la fonction.
        oiseauxKeywords (list): Liste de mots-clés pour les oiseaux, à utiliser dans les remarques de statut.

    Returns:
        str: Le code de statut extrait, ou "No Data" si aucun statut pertinent n'a été trouvé.
    """

    # Condition 1: Ajouter locationName si applicable
    location = row.get("locationName", "")
    if not ((row.get("locationAdminLevel", "") == "Département") or (status in [DETERMINANT_ZNIEFF, LUTTE_CONTRE_ESPECES])):
        # Si ce n'est pas un département ou un statut particulier, ne pas inclure locationName
        location = ""

    # Condition 2 : Ajouter mots-clés de self.oiseauxKeywords s'ils sont dans statusRemarks
    keywords = ""
    if (OISEAUX.title in currentTaxon) and (status == LISTE_ROUGE_NATIONALE):
        status_remarks = row.get("statusRemarks", "")
        if status_remarks:
            # Recherche de mots-clés d'oiseaux dans les remarques de statut
            keywords = ", ".join([word for word in oiseauxKeywords if word in status_remarks])

    # Condition 3 : Ajouter l'information regex depuis statusName
    annex_article = ""
    status_name = row.get("statusName", "")
    if isinstance(status_name, str):
        # Vérifie que statusName est une chaîne valide
        match = re.search(r"(Annexe [IVXLCDM]+|Annexe \d+(er)?|Annexe [IVXLCDM]+/\d+|Article [IVXLCDM]+|Article \d+(er)?)$", status_name)
        if match:
            annex_article = match.group(1)
            
    # Condition 4 : Ajouter statusCode sauf si self.statusId == "ZDET"
    if not (status in (DETERMINANT_ZNIEFF,
                       DIRECTIVE_OISEAUX,
                       DIRECTIVE_HABITAT,
                       PROTECTION_NATIONALE,
                       PROTECTION_REGIONALE,
                       PROTECTION_DEPARTEMENTALE,
                       PRIORITE_ACTION_PUBLIQUE_NATIONALE,
                       PLAN_NATIONAL_ACTION)) :
        status_code = row.get("statusCode", "")
    elif status in (PRIORITE_ACTION_PUBLIQUE_NATIONALE, PLAN_NATIONAL_ACTION) :
        # Si c'est PAPNAT ou PNA, utiliser statusName comme statusCode
        status_code = status_name
    else :
        status_code = ""

    # Combiner les résultats pour créer un code de statut
    result = " : ".join(filter(None, [location, status_code, keywords, annex_article]))

    return result if result else "No Data"

def reorganize_columns_and_codes(status_data_in: pd.DataFrame,
                                 status: StatusType,
                                 taxon_title: str,
                                 oiseaux_keywords: List[str])->pd.DataFrame:
    
    """
    Réorganise et nettoie les colonnes d’un DataFrame contenant des statuts TAXREF,
    applique le traitement spécifique pour extraire les codes de statut, et renomme 
    les colonnes en fonction du statut.

    Parameters
    ----------
    status_data_in : pd.DataFrame
        DataFrame brut issu du parsing des statuts d’un taxon, contenant plusieurs champs.
    status_id : str
        Identifiant du statut (ex: "LR", "LRN", "REGLLUTTE").
    taxon_title : str
        Nom du groupe taxonomique (utilisé notamment pour filtrer les oiseaux).
    oiseaux_keywords : list
        Liste de mots-clés (comme "Nicheur", "Hivernant", "Visiteur") à chercher dans les remarques
        pour affiner les codes de statut.

    Returns
    -------
    pd.DataFrame
        DataFrame nettoyé et renommé, prêt pour l’agrégation régionale.
    """

    # Colonnes à garder pour traiter les statuts
    columns_to_keep = ["taxon_referenceId", "statusCode",
                       "source", "sourceId",
                       "locationName", "locationAdminLevel",
                       "statusRemarks", "statusName"]
    
    # Dictionaire pour renommer les colonnes 
    rename_dict = {
        "taxon_referenceId": "CD_REF",
        "statusCode": status.type_id,
        "source": f"source_{status.type_id}",
        "sourceId": f"sourceId_{status.type_id}"}
    
    # Suppréssion des colonnes inutiles
    status_column_reduced = status_data_in[columns_to_keep]

    # Réccupération des status_code pour la colonne statusCode
    newlist = status_column_reduced.apply(lambda x: extract_status_code(x, status, taxon_title, oiseaux_keywords), axis=1)
    status_column_reduced.loc[:, "statusCode"] = newlist

    # Renommer les colonnes
    status_data_out = status_column_reduced.rename(columns=rename_dict)

    return status_data_out

# Fonction pour filtrer les portions contenant un mot-clé
def filter_by_keyword(lrn_string: str, keyword: str)->str:
    """
    Filtre les portions d'une chaîne qui contiennent un mot-clé et supprime ce mot-clé de ces portions.

    Args:
        lrn_string (str): La chaîne contenant des portions séparées par des points-virgules.
        keyword (str): Le mot-clé à rechercher dans les portions.

    Returns:
        str: Les portions filtrées, séparées par des points-virgules, sans le mot-clé.
    """
    if pd.isna(lrn_string): 
        # Gestion des valeurs manquantes
        return ""
    
    # Filtrer les portions contenant le mot-clé et supprimer le mot-clé de ces portions
    filtered_portions = [
        portion.replace(f" : {keyword}", "").strip()  # Retirer le mot-clé et les espaces en excès
        for portion in lrn_string.split(";")
        if keyword in portion
    ]

    # Si des portions filtrées sont trouvées, les joindre avec un point-virgule, sinon renvoyer une chaîne vide
    return ";".join(filtered_portions) if filtered_portions else ""

# Sauve les statuts dans des fichier XLS ou CSV
def do_save_excel(save_excel: bool,
                  folder_excel:str,
                  status_data: pd.DataFrame,
                  status: StatusType,
                  taxon_title: str,
                  debug: int=0)->None:

    """
    Sauvegarde les données de statut par région dans des fichiers CSV distincts.

    Si un fichier existe déjà pour une région, les données sont fusionnées 
    (sans doublons) avec les anciennes.

    Parameters
    ----------
    save_excel : bool
        Active ou non la sauvegarde.
    folder_excel : str
        Chemin vers le dossier de sauvegarde.
    status_data : pd.DataFrame
        Données de statut à enregistrer.
    status_id : str
        Identifiant du statut (ex : "LR", "REGLLUTTE").
    taxon_title : str
        Titre du taxon (utilisé dans le nom de fichier).
    debug : int, optional
        Niveau de debug. Si > 0, affiche des messages de suivi.
    """

    if not save_excel:
        return

    # Crée le dossier s'il n'existe pas
    os.makedirs(folder_excel, exist_ok=True)

    for locName in status_data['locationName'].unique():

        print_debug_info(debug, 1, f"Sauve {locName} en CSV")

        condition_location_name = status_data["locationName"]==locName
        filename = f'{locName.title().replace(" ", "")}_{status.type_id}_{taxon_title}.csv'
        csv_path = os.path.join(folder_excel, filename)

        # Fusion avec l'ancien fichier s'il existe
        if os.path.isfile(csv_path):
            old_csv = pd.read_csv(csv_path)
            new_csv = pd.concat([old_csv, status_data[condition_location_name]], ignore_index=True).drop_duplicates()
            new_csv.to_csv(csv_path, index=False)
        else:
            status_data[condition_location_name].to_csv(csv_path, index=False)

    return

# Fonction pour générer les DataFrames par niveau administratif    
def generate_status_by_level(df: pd.DataFrame, level_name: str,
                             region_filter_func,
                             lambdafunc_dict: dict,
                             regions: dict, status: StatusType)->List[pd.DataFrame]:
    """
    Génère un statut agrégé par niveau (Région ou autre niveau administratifs) en fonction de `statusId`.

    Args:
        df (pd.DataFrame): Le DataFrame contenant les données à traiter.
        level_name (str): Le nom du niveau administratif (par exemple, "Département").
        region_filter_func (function): Une fonction permettant de filtrer les régions à traiter.
        lambdafunc_dict (dict): Un dictionnaire de fonctions d'agrégation à appliquer sur les données.
        regions (dict): Dictionnaire de régions à traiter.
        statusId (StatusType): L'ID du statut qui déterminera la logique de traitement.
        taxonTitle (str): Le titre du taxon, utilisé pour des traitements spécifiques si nécessaire.

    Returns:
        list: Une liste de DataFrames contenant les résultats agrégés par région ou niveau administratif.
    """

    result = []
    status_nationaux = [status_type for status_type in STATUS_TYPES if status_type.is_national()]

    # Vérification si le statusId n'appartient pas aux statuts particuliers
    if status not in status_nationaux:
        for region in regions:
            # Appliquer le filtre avant d'effectuer des transformations
            filtered_df = df[region_filter_func(region)]

            # Assurez-vous que les colonnes nécessaires existent dans filtered_df
            required_columns = ["CD_REF", "locationName", "locationAdminLevel", "statusRemarks", "statusName"]
            missing_columns = [col for col in required_columns if col not in filtered_df.columns]
            if missing_columns:
                raise ValueError(f"Colonnes manquantes dans le DataFrame filtré : {', '.join(missing_columns)}")
            
            # Effectuer l'assignation et la transformation uniquement sur le sous-ensemble filtré
            temp_df = (filtered_df
                .assign(**{"Région" : region})
                .assign(agg_region_cdref=lambda x: x["Région"] + x["CD_REF"].astype(str))
                .drop(columns=["locationName", "locationAdminLevel", "statusRemarks", "statusName"])
                .groupby(["Région", "CD_REF"], as_index=False)
                .agg(lambdafunc_dict))

            result.append(temp_df)
    else :
        # Pour les statuts particuliers, appliquer un filtrage spécifique
        filtered_df = df[(df["locationName"].isin(["France", "France métropolitaine"])) & (df["locationAdminLevel"] == level_name )]

        # Vérification de l'existence des colonnes requises dans filtered_df
        required_columns = ["CD_REF", "locationName", "locationAdminLevel"]
        missing_columns = [col for col in required_columns if col not in filtered_df.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes dans le DataFrame filtré : {', '.join(missing_columns)}")

        # Effectuer l'assignation et la transformation uniquement sur le sous-ensemble filtré
        temp_df = (filtered_df
            .drop(columns=["locationName", "locationAdminLevel", "statusRemarks", "statusName"])
            .groupby(["CD_REF"], as_index=False)
            .agg(lambdafunc_dict))

        result.append(temp_df)
    
    return result

# Fonction pour créer les fonctions d'aggrégation
def definir_agg_function(status: StatusType,
                         status_data: pd.DataFrame)->Tuple[pd.DataFrame, Dict[str, str]] :
    """
    Définit un dictionnaire de fonctions d'agrégation pour concaténer les colonnes 
    liées à un statut donné, en les séparant par un point-virgule.

    Parameters
    ----------
    status : StatusType
        L'identifiant du statut (par exemple "LR", "REGLLUTTE", etc.).
    status_data : pd.DataFrame
        Le DataFrame contenant les colonnes à concaténer.

    Returns
    -------
    tuple
        Un tuple contenant :
        - Un dictionnaire {nom_colonne: fonction d'agrégation}
        - Le DataFrame modifié avec les colonnes converties en chaînes
    """

    # Colonnes à concaténer lors de l'agrégation
    columns_to_combine = [status.type_id, f"source_{status.type_id}", f"sourceId_{status.type_id}"]
    
    # On s'assure que ces colonnes sont bien des chaînes de caractères
    for col in columns_to_combine :
        status_data[col]=status_data[col].astype(str)

    # Dictionnaire des fonctions d'agrégation : join avec point-virgule    
    lambdafunc_dict = {col: '; '.join for col in columns_to_combine}

    return lambdafunc_dict, status_data

# Fonction pour appliquer le rangement en fonction des localisation
def reorganize_on_admin_level(status: StatusType, status_data_in: pd.DataFrame):
    """
    Réorganise les données de statut par niveau administratif (État, région, département, etc.)
    en les agrégeant selon des règles spécifiques aux anciennes et nouvelles régions.

    Parameters
    ----------
    status_id : str
        Identifiant du statut à traiter (ex : "LR", "REGLLUTTE").
    status_data_in : pd.DataFrame
        Données en entrée avec les statuts à réorganiser.

    Returns
    -------
    pd.DataFrame
        Données réorganisées et agrégées par niveau administratif.
    """

    # Liste des niveaux administratifs à traiter
    adminLevels = ["État", "Territoire", "Région", "Ancienne région", "Département"]
    
    # Définition des régions associées aux différents territoires
    regions = {"Auvergne" : ["Auvergne-Rhône-Alpes", "Allier", "Cantal", "Haute-Loire", "Puy-de-Dôme"],
                        "Rhône-Alpes":["Auvergne-Rhône-Alpes", "Ain", "Ardèche", "Drôme", "Isère", "Loire", "Rhône", "Savoie", "Haute-Savoie"],
                        "Bourgogne":["Gourgogne-Franche-Comté", "Côte-d'Or", "Nièvre", "Saône-et-Loire", "Yonne"],
                        "Franche-Comté":["Bourgogne-Franche-Comté", "Doubs", "Jura", "Haute-Saône"],
                        "Bretagne":["Bretagne", "Côtes-d'Armor", "Finistère", "Ille-et-Vilaine", "Morbian"],
                        "Centre":["Centre-Val de Loire", "Cher", "Eure-et-Loir", "Indre", "Indre-et-Loire", "Loir-et-Cher", "Loiret"],
                        "Corse":["Corse", "Corse-du-Sud", "Haute-Corse"],
                        "Champagne-Ardenne":["Grand-Est", "Ardennes", "Aube", "Marne", "Haute-Marne"],
                        "Alsace":["Grand-Est", "Bas-Rhin", "Haut-Rhin"],
                        "Lorraine":["Grand-Est", "Meurthe-et-Moselle", "Meuse", "Vosges"],
                        "Picardie":["Hauts-de-France", "Aisne", "Oise","Somme"],
                        "Nord-Pas-de-Calais":["Haute-de-France", "Nord", "Pas-de-Calais"],
                        "Ile-de-France":["Ile-de-France", "Paris", "Seine-et-Marne", "Yvelines", "Essonne", "Hauts-de-Seine", "Seine-Saint-Denis", "Val-de-Marne", "Val-d'Oise"],
                        "Haute-Normandie":["Normandie", "Eure", "Seine-Maritime"],
                        "Basse-Normandie":["Normandie", "Calvados","Manche", "Orne"],
                        "Poitou-Charentes":["Nouvelle-Aquitaine", "Charente", "Charente-Maritime", "Deux-Sèvre", "Vienne"],
                        "Aquitaine":["Nouvelle-Aquitaine", "Dordogne", "Gironde", "Landes", "Lot-et-Garonne", "Pyrénées-Atlantique"],
                        "Limousin":["Nouvelle-Aquitaine", "Corrèze", "Creuse", "Deux-Sèvre", "Haute-Vienne"],
                        "Midi-Pyrénées":["Occitanie", "Ariège", "Aveyron", "Haute-Garonne", "Gers", "Lot", "Hautes-Pyrénées", "Tarn", "Tarn-et-Garonne"],
                        "Languedoc-Roussillon":["Occitanie", "Aude", "Gard", "Hérault", "Lozère", "Pyrénées-Orientales"],
                        "Pays de la Loire":["Pays de la Loire", "Loire-Atlantique", "Maine-et-Loire", "Mayenne", "Sarthe", "Vendée"],
                        "Provence-Alpes-Côte d'Azur":["Provence-Alpes-Côte-d'Azur", "Alpes-de-Haute-Provence", "Hautes-Alpes", "Alpes-Maritimes", "Bouches-du-Rhône", "Var", "Vaucluse"]}

    # Définir les fonctions d'agrégation pour les groupes
    lambdafunc_dict, status_data_as_str = definir_agg_function(status, status_data_in)

    status_array_dict = {}
    for adminLevel in adminLevels :
    # Générer les DataFrames pour chaque niveau administratif
        status_array_dict[adminLevel] = generate_status_by_level(
            status_data_as_str,
            adminLevel,
            lambda region: (status_data_as_str["locationName"].isin(["France", "France métropolitaine", region] + regions[region])) & 
                (status_data_as_str["locationAdminLevel"]==adminLevel),
            lambdafunc_dict, regions, status)

    # Concaténer tous les DataFrames en un seul
    status_data_out = pd.concat([df for dfs in status_array_dict.values() for df in dfs], ignore_index=True)

    return status_data_out

# Modifie les status pour les Oiseaux et les statuts REGLLUTTE
def modifier_statuts_specifiques(status: StatusType,
                                 taxon_title: str,
                                 status_data_in: pd.DataFrame,
                                 oiseaux_keywords: list)->pd.DataFrame:
    """
    Modifie les colonnes de statuts spécifiques en fonction du type de taxon et de l'identifiant de statut.

    Parameters
    ----------
    status_id : str
        Identifiant du statut (ex : "LRN", "REGLLUTTE").
    taxon_title : str
        Titre ou groupe taxonomique (ex : "Oiseaux", "Mammifères").
    status_data_in : pd.DataFrame
        Données d'entrée contenant les statuts.
    oiseaux_keywords : list
        Liste de mots-clés pour les statuts des oiseaux (ex : ["Nicheur", "Hivernant"]).

    Returns
    -------
    pd.DataFrame
        DataFrame mis à jour avec les statuts spécifiques modifiés ou ajoutés.
    """

    # Créer des colonnes spécifiques pour les oiseaux (Nicheur, Hivernant, Visiteur)
    if (status == LISTE_ROUGE_NATIONALE) and (OISEAUX.title in taxon_title) :
        for keyword in oiseaux_keywords:
            col_name = f"{status.type_id} - {keyword}"
            status_data_in[col_name] = status_data_in[LISTE_ROUGE_NATIONALE.type_id].apply(lambda x: filter_by_keyword(x, keyword))
    
    # Modifier la colonne des status REGLLUTTE
    elif (status == LUTTE_CONTRE_ESPECES) :
        status_data_in[status.type_id] = status_data_in[status.type_id].apply(lambda x: x.replace(" : ", " - "))

    # Passer les élements de la colonne CD_REF en string plutot qu'en int
    status_data_in['CD_REF'] = status_data_in['CD_REF'].astype(int)

    return status_data_in

# Fait le status array a sauvegarder temporairement
@time_decorator
def make_status_array(status: StatusType,
                    taxon_title: str, status_array_in: pd.DataFrame,
                    save_excel: bool, folder_excel: str,
                    debug: int=0):

    """
    Cette fonction génère un tableau de statuts agrégés pour un taxon donné, en traitant des informations 
    provenant de données d'entrée et en appliquant diverses transformations et agrégations. Elle peut également
    enregistrer les résultats dans des fichiers CSV pour chaque localisation.

    Args:
        statusId (str): L'ID du statut à traiter (ex. "LRN", "DH", etc.).
        taxonTitle (str): Le titre du taxon (ex. "Flore", "Oiseaux").
        status_array_in (pd.DataFrame): Le DataFrame d'entrée contenant les informations de statut.
        save_excel (bool): Si True, les résultats seront enregistrés dans des fichiers CSV.
        folder_excel (str): Le dossier où les fichiers CSV seront sauvegardés.
        debug (int, optionnel): Niveau de débogage. Par défaut, 0. Si >1, des messages de débogage seront affichés.

    Returns:
        pd.DataFrame: Un DataFrame contenant les données agrégées pour le statut et le taxon donnés.
    """

    print_debug_info(debug, 1, f"Pour {status.type_id} au taxon {taxon_title}, début de make_status_array")

    # Liste des mots-clés utilisés pour les oiseaux
    oiseaux_keywords = ["Nicheur", "Hivernant", "Visiteur"]

    # Preprocess des statuts pour organiser les colonnes et avoir les status code avant tri
    status_data_preprocessed = reorganize_columns_and_codes(status_array_in,
                                                            status,
                                                            taxon_title,
                                                            oiseaux_keywords)

    # Sauver en fichier excel les tableaux 
    do_save_excel(save_excel,
                  folder_excel,
                  status_data_preprocessed,
                  status,
                  taxon_title,
                  debug=debug)


    # Organise les status dans un seul pandas.DataFrame en fonction des localisations et type de statuts
    status_local_organized = reorganize_on_admin_level(status, status_data_preprocessed)

    # Ajoute des modification spécifique à certains statuts
    status_array_out = modifier_statuts_specifiques(status,
                                                    taxon_title,
                                                    status_local_organized,
                                                    oiseaux_keywords)

    print_debug_info(debug, 1, f"Pour {status.type_id} au taxon {taxon_title}, fin de make_status_array")

    return status_array_out

def get_all_status_type():
    
    url = "https://taxref.mnhn.fr/api/status/types"

    response = requests.get(url)
    data_json = response.json()

    status_list = data_json['_embedded']['statusTypes']
    df_page = pd.json_normalize(status_list, sep='_')
    list_types = df_page["id"].to_list()

    return list_types

#
@time_decorator
def download_status(status: StatusType,
                 taxons: List[TaxonGroupe],
                 path: str,
                 save_excel: bool,
                 folder_excel: str,
                 debug: int=0):
    
    """
    Télécharge les statuts depuis l'API TAXREF en fonction d'un identifiant de statut,
    filtre les données pour chaque taxon spécifié, puis génère des tableaux de statuts.

    Parameters
    ----------
    status_id : str
        Identifiant du type de statut à récupérer (ex : "LRN", "REGLLUTTE").
    taxon_titles : list
        Liste des titres de groupes taxonomiques à filtrer (ex : ["Oiseaux", "Mammifères"]).
    path : str
        Chemin vers le dossier contenant les fichiers de référence (CD_REF).
    save_excel : bool
        Si True, les tableaux sont enregistrés en tant que fichiers Excel.
    folder_excel : str
        Dossier de destination pour les fichiers Excel si `save_excel` est activé.
    debug : int, optional
        Niveau de verbosité du débogage (0 = aucun message, 1 = messages de progression).

    Returns
    -------
    dict
        Dictionnaire où les clés sont les `taxon_titles` et les valeurs sont des listes
        de tableaux (résultats de `make_status_array`).
    """
    
    # Initialiser un dictionnaire vide pour stocker les tableaux par taxon
    dict_make_array_out = {taxon.title: [] for taxon in taxons}

    # Préparer l'URL pour la pagination
    url_prefix = f"https://taxref.mnhn.fr/api/status/findByType/{status.type_id}?page="
    url_suffix = "&size=10000"

    # Initialisé à 1 pour commencer la boucle
    i = 1
    total_pages = 1

    while i <= total_pages:
        url = url_prefix + str(i) + url_suffix
        
        print_debug_info(debug, 1, f"Pour {status.type_id}, début du téléchargement page {i}")

        # Requête HTTP
        response = requests.get(url)
        data_json = response.json()

        print_debug_info(debug, 1, f"Pour {status.type_id}, fin du téléchargement page {i}")

        # Mettre à jour le nombre total de pages lors de la première itération
        if i == 1:
            total_pages = data_json['page']['totalPages']

        # Extraire la liste des statuts et convertir en DataFrame
        status_list = data_json['_embedded']['status']
        df_page = pd.json_normalize(status_list, sep='_')
        df_page["statusId"] = status.type_id
        df_page["taxon_referenceId"] = df_page["taxon_referenceId"].astype(str)

        # Filtrer les statuts en fonction des taxons définis par CD_REF
        dict_df_filter = filter_by_cd_ref(df_page, taxons, path)

        # Générer les tableaux par taxon si des données sont présentes  
        for key in dict_df_filter:
            
            if len(dict_df_filter[key]) != 0:
                dict_make_array_out[key].append(
                    make_status_array(
                        status, key,
                        dict_df_filter[key],
                        save_excel,
                        folder_excel,
                        debug=debug))

        # Page suivante
        i += 1

    return dict_make_array_out

def save_temp_file_status(dict_make_array_in: Dict[str, pd.DataFrame],
                          status: StatusType,
                          taxons: List[TaxonGroupe],
                          path: str,
                          debug: int=0):

    """
    Concatène les tableaux de statuts par taxon, les transforme en GeoDataFrame, puis les enregistre
    temporairement au format GeoPackage (.gpkg).

    Parameters
    ----------
    dict_make_array_in : dict
        Dictionnaire contenant des listes de DataFrames pour chaque taxon (résultats de `make_status_array`).
    status_id : str
        Identifiant du statut (ex : "LRN", "REGLLUTTE").
    taxons : list of TaxonGroupe
        Liste des noms des taxons à traiter.
    path : str
        Répertoire où enregistrer les fichiers GeoPackage temporaires.
    debug : int, optional
        Niveau de verbosité du débogage (0 = silencieux, 1 = messages).

    Returns
    -------
    list
        Liste des chemins vers les fichiers GPKG générés.
    """

    temp_pathes = []
    for taxon in taxons:
        print_debug_info(debug, 1, f"Pour {status.type_id} au taxon {taxon.title}, début de concaténation")

        # Si on a des DataFrames pour ce taxon, on les concatène
        if len(dict_make_array_in[taxon.title]) != 0:
            dict_make_array_in[taxon.title] = pd.concat(dict_make_array_in[taxon.title], ignore_index=True)
        else :
            # Sinon, on crée un DataFrame vide avec les colonnes minimales
            dict_make_array_in[taxon.title] = pd.DataFrame({}, columns=["Région", "CD_REF"])

        # Conversion en GeoDataFrame (même s'il n'y a pas encore de géométrie)
        gdf = gpd.GeoDataFrame(dict_make_array_in[taxon.title])

        # Construction du chemin de fichier temporaire
        temp_path = os.path.join(path, f"{taxon.title}_{status.type_id}.gpkg")
        temp_pathes.append(temp_path)
        
        print_debug_info(debug, 1, f"Pour {status.type_id} au taxon {taxon.title}, début de sauvegarde")
        
        # Sauvegarde au format GPKG
        gdf.to_file(temp_path, driver="GPKG")
        
        print_debug_info(debug, 1, f"Pour {status.type_id} au taxon {taxon.title}, fin de sauvegarde")


    return temp_pathes

@time_decorator
def run_download_status(status: StatusType,
                        taxons: List[TaxonGroupe],
                        path: str,
                        save_excel: bool,
                        folder_excel: str,
                        debug: int=0)->str:
    """
    Télécharge les statuts d'un type donné (status_id) pour les taxons spécifiés, puis les sauvegarde
    dans un fichier GeoPackage (.gpkg). Si nécessaire, les résultats sont également enregistrés sous forme
    de fichiers Excel.

    Cette fonction combine les étapes de téléchargement des statuts et de sauvegarde des résultats.

    Parameters
    ----------
    status_id : str
        Identifiant du statut (par exemple "LRN" ou "REGLLUTTE").
    taxons : list of TaxonGroupe
        Liste des taxons à traiter.
    path : str
        Dossier où enregistrer les fichiers générés (GeoPackage et éventuellement Excel).
    save_excel : bool
        Indicateur pour savoir si un fichier Excel doit être généré (True/False).
    folder_excel : str
        Dossier où enregistrer les fichiers Excel si `save_excel` est True.
    debug : int, optional
        Niveau de verbosité du débogage (0 = aucun message, 1 = messages détaillés), par défaut 0.

    Returns
    -------
    list of str
        Liste des chemins vers les fichiers GeoPackage générés.
    """

    list_all_status_type_ids = get_all_status_type()
    status.set_in_api(bool_val = (status.type_id in list_all_status_type_ids))
    if  status.in_api :

        # Télécharger les données de statu
        dict_make_array_out = download_status(status,
                                              taxons,
                                              path,
                                              save_excel,
                                              folder_excel,
                                              debug=debug)

        # Sauvegarder les données sous forme de fichiers GeoPackage temporaires
        temp_pathes = save_temp_file_status(dict_make_array_out,
                                            status,
                                            taxons,
                                            path,
                                            debug=debug)
        return temp_pathes
    
    else :
        print_debug_info(1, 0, f"Le type de status '{status.type_id}' n'est pas reconnu comme un status dans l'API TAXREF.")

        return ""

def reorder_columns(df: pd.DataFrame)->pd.DataFrame:
    """
    Réorganise les colonnes d'un DataFrame en fonction de certains critères de priorisation.
    Les colonnes sont regroupées par statut (status_id) et triées de manière à placer :
    1. Les colonnes de statut de type "statusId" en premier.
    2. Ensuite, les colonnes commençant par "sourceId_" pour chaque statut.
    3. Enfin, les colonnes commençant par "source_" pour chaque statut.

    Les colonnes ne correspondant à aucun des statuts sont placées en premier, suivies des colonnes triées par statut.

    Parameters
    ----------
    df : pd.DataFrame
        Le DataFrame dont les colonnes doivent être réorganisées.

    Returns
    -------
    pd.DataFrame
        Un nouveau DataFrame avec les colonnes réorganisées.
    """

    # Liste des statusId à rechercher dans les colonnes
    status_ids = ["DH", "DO", "PN", "PR", "PD", "LRN", "LRR", "PNA", "PAPNAT", "ZDET", "REGLLUTTE"]

    # Créer des groupes
    base_group = []  # Colonnes qui ne contiennent aucun statusId
    grouped_columns = {status: [] for status in status_ids}  # Colonnes qui contiennent les statusIds

    # Parcours des colonnes du DataFrame pour les classer selon leur statut
    for col in df.columns:
        matched = False
        # Recherche des colonnes correspondant à un statut donné
        for status in status_ids:
            if (col == status) or col.startswith(f"source_{status}") or col.startswith(f"sourceId_{status}"):
                grouped_columns[status].append(col)
                matched = True
                break
        if not matched:
            # Si la colonne ne correspond à aucun statut, elle est ajoutée au groupe de base
            base_group.append(col)

    # Respecter l'ordre des groupes et l'ordre interne des statusIds
    ordered_columns = base_group
    for status in status_ids:
        # Ordre dans chaque groupe : statusId, source_statusId, sourceID_statusId
        ordered_columns += sorted(
            grouped_columns[status],
            key=lambda x: (
                x == status,  # "statusId" prioritaire
                x.startswith("sourceId"),  # Puis "sourceID_statusId"
                x.startswith("source")  # Enfin "source_statusId"
            ),
            reverse=True
        )

    return df[ordered_columns]

def save_global_status(status_df: pd.DataFrame,
                path: str,
                taxon_title: str,
                save_type: str,
                debug:int=0)->None:
    """
    Sauvegarde les statuts d'un taxon (à l'échelle nationale ou régionale) dans un fichier GeoPackage.
    Cette fonction fusionne les nouveaux statuts avec ceux déjà présents dans un fichier `.gpkg`, en respectant
    la structure des colonnes et en supprimant les doublons et colonnes vides.
    
    Parameters
    ----------
    status_df : pd.DataFrame
        Le DataFrame contenant les statuts à sauvegarder (nouvelles données).
    path : str
        Le chemin du dossier où le fichier GeoPackage sera enregistré.
    taxon_title : str
        Le nom du taxon (ex. : "Oiseaux", "Mammifères") utilisé pour nommer les couches.
    save_type : str
        Indique si la sauvegarde est "national" ou "regional" :
            - "national" : sauvegarde une liste nationale.
            - "regional" : sauvegarde une liste avec séparation par région.
    debug : int, optional
        Niveau de verbosité pour afficher des messages de débogage (par défaut 0).

    Raises
    ------
    ValueError
        Si le paramètre `save_type` n'est ni "national" ni "regional".
    
    Returns
    -------
    None
    """

    print_debug_info(debug, -1, f"\tPour {taxon_title}, début de sauvegarde {save_type}")

    # Colonnes pour le merge
    col_to_check = ["CD_REF"]
    national_value = "national"
    regional_value = "regional"
    bird_col = []

    # Construction du chemin vers le fichier GeoPackage
    file_save_path = get_file_save_path(path, taxon_title)

    # Liste des couches déjà présentes dans le fichier
    available_layers =  list_layers_from_gpkg(file_save_path)
    #gpd.list_layers(file_save_path)

    # Choix du nom de la couche et configuration spécifique selon le type de sauvegarde
    if save_type == regional_value:
        layer_name = f"Statuts {taxon_title}"
        # Fusion régionale implique une clé supplémentaire
        col_to_check.append("Région")

    elif save_type == national_value:
        layer_name = f"Liste {taxon_title}"
        # Cas particulier : pour les oiseaux, ignorer "LRN" lors de la fusion
        bird_col = [LISTE_ROUGE_NATIONALE.type_id] if taxon_title == OISEAUX.title else []
    else:
        raise ValueError(f"save_type should be either \"{national_value}\" or \"{regional_value}\" but is : {save_type}")
    
    # Si une couche existe déjà, on la lit et prépare une fusion avec les nouvelles données
    if layer_name in available_layers :#["name"].values:
        print_debug_info(1, 0, f"{layer_name} in {available_layers}")
        old_file = load_layer_as_dataframe(file_save_path, layer_name=layer_name)
        #pd.DataFrame(gpd.read_file(file_save_path, layer=layer_name))

        print_debug_info(1, 0, f"{layer_name} old_file : {old_file.columns}")

        # Forcer les colonnes clé en chaîne pour éviter les erreurs de jointure
        old_file['CD_REF'] = old_file['CD_REF'].astype(str) 
        status_df['CD_REF'] = status_df['CD_REF'].astype(str)
 
        # Colonnes communes à retirer de l'ancien fichier pour ne pas écraser les nouvelles données
        colonnes_sans_cd_ref = [col for col in status_df.columns if ((col not in col_to_check) and (col in old_file.columns))]
        
        print_debug_info(debug, 2, f"Pour {taxon_title} : les colonnes de status_df sont {status_df.columns}")

        # Nettoyer la version ancienne pour préparer le merge
        old_file_light = old_file.drop(columns=colonnes_sans_cd_ref+bird_col)

        # Colonnes à tester pour la suppression des lignes vides après fusion
        subset_col_dropna = [col for col in old_file_light.columns if col not in col_to_check]
        
        # Fusion : priorise les clés communes et conserve les lignes valides
        if save_type == regional_value:
            status_merged = pd.merge(old_file_light, status_df, on=col_to_check, how='outer').dropna(axis=0, how="all", subset=subset_col_dropna)
        else:
            status_merged = pd.merge(old_file_light, status_df, on=col_to_check, how='outer')

        # Supprime les colonnes vides de la table fusionnée
        status_na_dropped = status_merged.dropna(axis=1, how="all")

    else:
        # Si aucune couche existante, on nettoie juste les colonnes vides
        status_na_dropped = status_df.dropna(axis=1, how="all")

    print_debug_info(debug, 2, f"Pour {taxon_title} : les colonnes de result sont {status_na_dropped.columns}")

    # Réorganise les colonnes de manière standard et supprime les doublons
    status_to_save = reorder_columns(status_na_dropped).drop_duplicates()

    print_debug_info(debug, 2, f"Pour {taxon_title} : les colonnes après reordonnancement sont {status_to_save.columns}")
        
    # Convertit le DataFrame en GeoDataFrame et sauvegarde dans le fichier GeoPackage
    save_dataframe(status_to_save, file_save_path, layer_name)

    return
