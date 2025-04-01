import pandas as pd 
import geopandas as gpd
import numpy as np
import re

import io
import os
import requests

from datetime import datetime, date

from qgis.core import QgsMessageLog, Qgis

from .UpdateSearchStatus import GetSourcesFromYear

# Télécharge les fichier JSON des status et les charge dans un dataframe pandas
"""
                        "Guadeloupe": ["Guadeloupe"],
                        "Guyane": ["Guyane"],
                        "Martinique": ["Maritime"],
                        "Réunion": ["Réunion"],
                        "Mayotte": ["Mayotte"]}"""


# Supprime les lignes non nécessaires dans le pandas dataframe
def filter_by_cd_ref(df_concat: pd.DataFrame, taxonTitles: list, path: str) -> pd.DataFrame:

    domtom = ["Guadeloupe", "Guyane", "Martinique", "Réunion", "Mayotte"]

    # retire les statuts dont le CD_NOM ne correspondent pas au CD_REF
    df_concat = df_concat[df_concat['taxon_referenceId'].astype(int) == df_concat["taxon_id"].astype(int)]
    # Charger les fichiers GPKG pour tous les titres une seule fois
    df_refs = {}
    for title in taxonTitles:
        if title == "Flore":
            file_path = os.path.join(path, f"{title}.gpkg")
        else:
            file_path = os.path.join(path, "Faune.gpkg")
        df_refs[title] = pd.DataFrame(gpd.read_file(file_path, layer=f"Liste {title}"))
    
    # Filtrer les données par référence
    dict_df_out = {}
    for title in taxonTitles:
        df_ref = df_refs[title]
        df_out = df_concat[df_concat['taxon_referenceId'].astype(int).isin(df_ref['CD_REF'].astype(int).values)]
        # Filtrage des données hors DOM-TOM
        status_no_domtom = df_out[~df_out["locationName"].isin(domtom)]
        dict_df_out[title] = status_no_domtom
        #self.filter_finished.emit(title, df_out)

    return dict_df_out

def extract_status_code(row, statusId: str, currentTaxon: str, departements: list, oiseauxKeywords: list):

    # Condition 1: Ajouter locationName si applicable
    location = row.get("locationName", "")
    if not ((row.get("locationAdminLevel", "") == "Département") or (statusId in ["ZDET", "REGLLUTTE"])):
        location = ""

    # Condition 2 : Ajouter mots-clés de self.oiseauxKeywords s'ils sont dans statusRemarks
    keywords = ""
    if ("Oiseaux" in currentTaxon) and (statusId == "LRN"):
        status_remarks = row.get("statusRemarks", "")
        if status_remarks:
            keywords = ", ".join([word for word in oiseauxKeywords if word in status_remarks])

    # Condition 3 : Ajouter l'information regex depuis statusName
    annex_article = ""
    status_name = row.get("statusName", "")
    if isinstance(status_name, str):  # Vérifie que statusName est une chaîne valide
        match = re.search(r"(Annexe [IVXLCDM]+|Annexe \d+(er)?|Annexe [IVXLCDM]+/\d+|Article [IVXLCDM]+|Article \d+(er)?)$", status_name)
        if match:
            annex_article = match.group(1)
            
    # Condition 4 : Ajouter statusCode sauf si self.statusId == "ZDET"
    if not (statusId in ("ZDET", "DO", "DH", "PN", "PR", "PD", "PAPNAT", "PNA")) :
        status_code = row.get("statusCode", "")
    elif statusId in ("PAPNAT", "PNA") : 
        status_code = status_name
    else :
        status_code = ""

    # Combiner les résultats
    result = " : ".join(filter(None, [location, status_code, keywords, annex_article]))

    return result if result else "No Data"

# Fonction pour générer les DataFrames par niveau administratif    
def generate_status_by_level(df: pd.DataFrame, level_name: str,
                             region_filter_func,
                             lambdafunc_dict: dict,
                             regions: dict, statusId: str, taxonTitle):
    result = []

    if statusId not in ("DH", "DO", "LRN", "PN", "PNA", "PAPNAT"):
        for region in regions:
            # Appliquer le filtre avant d'effectuer des transformations
            filtered_df = df[region_filter_func(region)]

            # Effectuer l'assignation et la transformation uniquement sur le sous-ensemble filtré
            temp_df = (filtered_df
                .assign(**{"Région" : region})
                .assign(agg_region_cdref=lambda x: x["Région"] + x["CD_REF"].astype(str))
                .drop(columns=["locationName", "locationAdminLevel", "statusRemarks", "statusName"])
                .groupby(["Région", "CD_REF"], as_index=False)
                .agg(lambdafunc_dict))

            result.append(temp_df)
    else :
        # Appliquer le filtre avant d'effectuer des transformations
        filtered_df = df[(df["locationName"].isin(["France", "France métropolitaine"])) & (df["locationAdminLevel"] == level_name )]

        # Effectuer l'assignation et la transformation uniquement sur le sous-ensemble filtré
        temp_df = (filtered_df
            .drop(columns=["locationName", "locationAdminLevel", "statusRemarks", "statusName"])
            .groupby(["CD_REF"], as_index=False)
            .agg(lambdafunc_dict))

        result.append(temp_df)
    
    return result

# Fonction pour filtrer les portions contenant un mot-clé
def filter_by_keyword(lrn_string: str, keyword: str):
    if pd.isna(lrn_string):  # Gestion des valeurs manquantes
        return ""
    return ";".join([portion.replace(f" : {keyword}", "") for portion in lrn_string.split(";") if keyword in portion])

def MakeStatusArray(statusId: str,
                    taxonTitle: str, status_array_in: pd.DataFrame,
                    save_excel: bool, folder_excel: str,
                    debug: int=0):

    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Pour {statusId} au taxon {taxonTitle}, début de MakeStatusArray ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

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

    departements = ["Ain", "Allier", "Ardèche", "Cantal", "Drôme", "Isère",
                "Loire", "Haute-Loire", "Puy-de-Dôme", "Rhône", "Savoie",
                "Haute-Savoie", "Côte-d'Or", "Doubs", "Jura", "Nièvre",
                "Haute-Saône", "Saône-et-Loire", "Yonne", "Côtes-d'Armor",
                "Finistère", "Ille-et-Vilaine", "Morbian", "Cher",
                "Eure-et-Loir", "Indre", "Indre-et-Loire", "Loir-et-Cher",
                "Loiret", "Corse-du-Sud", "Haute-Corse", "Ardennes", "Aube",
                "Marne", "Haute-Marne", "Meurthe-et-Moselle", "Meuse",
                "Bas-Rhin", "Haut-Rhin", "Vosges", "Aisne", "Nord", "Oise",
                "Pas-de-Calais", "Somme", "Paris", "Seine-et-Marne",
                "Yvelines", "Essonne", "Hauts-de-Seine", "Seine-Saint-Denis",
                "Val-de-Marne", "Val-d'Oise", "Calvados", "Eure", "Manche",
                "Orne", "Seine-Maritime", "Charente", "Charente-Maritime",
                "Corrèze", "Creuse", "Dordogne", "Gironde", "Landes",
                "Lot-et-Garonne", "Pyrénées-Atlantique", "Deux-Sèvre",
                "Vienne", "Haute-Vienne", "Ariège", "Aude", "Aveyron",
                "Gard", "Haute-Garonne", "Gers", "Hérault", "Lot", "Lozère",
                "Hautes-Pyrénées", "Pyrénées-Orientales", "Tarn",
                "Tarn-et-Garonne", "Loire-Atlantique", "Maine-et-Loire",
                "Mayenne", "Sarthe", "Vendée", "Alpes-de-Haute-Provence",
                "Hautes-Alpes", "Alpes-Maritimes", "Bouches-du-Rhône", "Var", "Vaucluse"]

    oiseauxKeywords = ["Nicheur", "Hivernant", "Visiteur"]

    #QgsMessageLog.logMessage(f"statusId is : {self.statusId}, and taxon is {taxonTitle}", "AutoUpdateTAXREF", level=Qgis.Info)
    # Réduction des colonnes et ajout de nouvelles valeurs
    status_column_reduced = status_array_in[["taxon_referenceId", "statusCode",
                                                "source", "sourceId",
                                                "locationName", "locationAdminLevel",
                                                "statusRemarks", "statusName"]]

    # Calcul du statusCode avec assign pour éviter l'utilisation d'apply
    newlist = status_column_reduced.apply(lambda x: extract_status_code(x, statusId, taxonTitle, departements, oiseauxKeywords), axis=1)
    status_column_reduced.loc[:, "statusCode"] = newlist

    # Renommer les colonnes
    rename_dict = {
        "taxon_referenceId": "CD_REF",
        "statusCode": statusId,
        "source": f"source_{statusId}",
        "sourceId": f"sourceId_{statusId}"}
    #status_col_renamed = status_newCode.rename(columns=rename_dict)
    status_col_renamed = status_column_reduced.rename(columns=rename_dict)

    # Sauver en fichier excel les tableaux 
    if save_excel:
        for locName in status_col_renamed['locationName'].unique():
            if debug > 1 :
                QgsMessageLog.logMessage(f"Sauve {locName} en CSV", "AutoUpdateTAXREF", level=Qgis.Info)
            csv_path = os.path.join(folder_excel, f'{locName.title().replace(" ", "")}_{statusId}_{taxonTitle}.csv')
            if os.path.isfile(csv_path):
                old_csv = pd.read_csv(csv_path)
                new_csv = pd.concat([old_csv, status_col_renamed[status_col_renamed["locationName"]==locName]], ignore_index=True).drop_duplicates()
                new_csv.to_csv(csv_path, index=False)
            else:
                status_col_renamed[status_col_renamed["locationName"]==locName].to_csv(csv_path, index=False)   

    # Définir les fonctions d'agrégation pour les groupes
    columns_to_combine = [statusId, f"source_{statusId}", f"sourceId_{statusId}"]
    for col in columns_to_combine :
        status_col_renamed[col]=status_col_renamed[col].astype(str)
        
    lambdafunc_dict = {col: '; '.join for col in columns_to_combine}

    adminLevels = ["État", "Territoire", "Région", "Ancienne région", "Département"]
    statusArrayDict = {}
    for adminLevel in adminLevels :
    # Générer les DataFrames pour chaque niveau administratif
        statusArrayDict[adminLevel] = generate_status_by_level(
            status_col_renamed,
            adminLevel,
            lambda region: (status_col_renamed["locationName"].isin(["France", "France métropolitaine", region] + regions[region])) & 
                (status_col_renamed["locationAdminLevel"]==adminLevel),
            lambdafunc_dict, regions, statusId, taxonTitle)

    # Concaténer tous les DataFrames en un seul
    statusArrayOut = pd.concat([df for dfs in statusArrayDict.values() for df in dfs], ignore_index=True)

    # Créer des colonnes spécifiques pour les oiseaux (Nicheur, Hivernant, Visiteur)
    if (statusId == "LRN") and ("Oiseaux" in taxonTitle) :
        for keyword in oiseauxKeywords:
            col_name = f"{statusId} - {keyword}"
            statusArrayOut[col_name] = statusArrayOut["LRN"].apply(lambda x: filter_by_keyword(x, keyword))
            #statusArrayOut = statusArrayOut.assign(**{col_name : statusArrayOut["LRN"].apply(lambda x: self.filter_by_keyword(x, keyword))})
    
    elif (statusId == "REGLLUTTE") :
        statusArrayOut[statusId] = statusArrayOut[statusId].apply(lambda x: x.replace(" : ", " - "))

    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Pour {statusId} au taxon {taxonTitle}, fin de MakeStatusArray ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    if taxonTitle == "Flore":
        QgsMessageLog.logMessage(f"Colonne de StatusArrayOut : {statusArrayOut.columns}", "AutoUpdateTAXREF", level=Qgis.Info)

    statusArrayOut['CD_REF'] = statusArrayOut['CD_REF'].astype(int) 

    return statusArrayOut

def run_download(statusId: str, taxonTitles: list, path: str, save_excel: bool, folder_excel: str, debug: int=0):
    #QgsMessageLog.logMessage(f"statusId: {statusId}", "AutoUpdateTAXREF", level=Qgis.Info)

    dict_makeArray_out = {}
    for title in taxonTitles :
        dict_makeArray_out[title] = []

    url_prefix = f"https://taxref.mnhn.fr/api/status/findByType/{statusId}?page="
    url_suffix = "&size=10000"

    # Effectuer la première requête pour obtenir le nombre total de pages
    url = url_prefix + "1" + url_suffix
    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Pour {statusId}, début du téléchargement page 1 ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    response = requests.get(url)
    data_json = response.json()
    if debug > 1 :
        now = datetime.now()
        QgsMessageLog.logMessage(f"Pour {statusId}, fin du téléchargement page 1 ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    # Récupérer le nombre total de pages
    total_pages = data_json['page']['totalPages']

    # Extraire la liste des statuts et convertir en DataFrame de la premiere requete
    status_list = data_json['_embedded']['status']
    df_page = pd.json_normalize(status_list, sep='_')

    # Initialiser une liste pour stocker les DataFrames
    dict_df_filter = filter_by_cd_ref(df_page, taxonTitles, path)
        
    for key in dict_df_filter:
        #QgsMessageLog.logMessage(f"longueur df 1: {len(dict_df_filter[key])}", "AutoUpdateTAXREF", level=Qgis.Info)
        if len(dict_df_filter[key]) != 0:
            dict_makeArray_out[key].append(
                MakeStatusArray(statusId, key, dict_df_filter[key], save_excel, folder_excel, debug=debug))

    # Boucle pour télécharger chaque page
    for i in range(2, total_pages + 1):

        url = url_prefix + str(i) + url_suffix
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Pour {statusId}, début du téléchargement page {i} ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)
        response = requests.get(url)
        data_json = response.json()
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Pour {statusId}, fin du téléchargement page {i} ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

        # Extraire la liste des statuts et convertir en DataFrame
        status_list = data_json['_embedded']['status']
        df_page = pd.json_normalize(status_list, sep = '_')
        df_page["statusId"] = statusId
        df_page["taxon_referenceId"] = df_page["taxon_referenceId"].astype(str)
        
        # Ajouter le DataFrame à la liste
        #QgsMessageLog.logMessage(f"longueur df {i}: {len(df_page)}", "AutoUpdateTAXREF", level=Qgis.Info)
        dict_df_filter = filter_by_cd_ref(df_page, taxonTitles, path)
        
        for key in dict_df_filter:
            #QgsMessageLog.logMessage(f"longueur df {i}: {len(dict_df_filter[key])}", "AutoUpdateTAXREF", level=Qgis.Info)
            if len(dict_df_filter[key]) != 0:
                dict_makeArray_out[key].append(
                    MakeStatusArray(statusId, key, dict_df_filter[key], save_excel, folder_excel, debug=debug))

    temp_pathes = []
    for title in taxonTitles:
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Pour {statusId} au taxon {title}, début de concaténation ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

        if len(dict_makeArray_out[title]) != 0:
            dict_makeArray_out[title] = pd.concat(dict_makeArray_out[title], ignore_index=True)
        else :
            dict_makeArray_out[title] = pd.DataFrame({}, columns=["Région", "CD_REF"])
        gdf = gpd.GeoDataFrame(dict_makeArray_out[title])
        temp_path = os.path.join(path, f"{title}_{statusId}.gpkg")
        temp_pathes.append(temp_path)
        #QgsMessageLog.logMessage(f"statusId: {statusId} et taxon est : {title}", "AutoUpdateTAXREF", level=Qgis.Info)
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Pour {statusId} au taxon {title}, début de sauvegarde ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

        gdf.to_file(temp_path, driver="GPKG")
        if debug > 1 :
            now = datetime.now()
            QgsMessageLog.logMessage(f"Pour {statusId} au taxon {title}, fin de sauvegarde ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)


    return temp_pathes

def reorder_columns(df):

    statusIds = ["DH", "DO", "PN", "PR", "PD", "LRN", "LRR", "PNA", "PAPNAT", "ZDET", "REGLLUTTE"]

    # Créer des groupes
    base_group = []  # Colonnes qui ne contiennent aucun statusId
    grouped_columns = {status: [] for status in statusIds}  # Colonnes qui contiennent les statusIds

    for col in df.columns:
        matched = False
        for status in statusIds:
            if (col == status) or col.startswith(f"source_{status}") or col.startswith(f"sourceId_{status}"):
                grouped_columns[status].append(col)
                matched = True
                break
        if not matched:
            base_group.append(col)

    # Respecter l'ordre des groupes et l'ordre interne des statusIds
    ordered_columns = base_group
    for status in statusIds:
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

def SaveRegionalStatus(status_df: pd.DataFrame, path: str, taxonTitle: str):
    
    now = datetime.now()
    QgsMessageLog.logMessage(f"\tPour {taxonTitle}, début de sauvegarde regionale ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)
    
    # Enregistrer dans un fichier GeoPackage    
    if taxonTitle == "Flore":
        file_save_path = os.path.join(path, f"{taxonTitle}.gpkg")
    else : 
        file_save_path = os.path.join(path, f"Faune.gpkg")
    
    available_layers = gpd.list_layers(file_save_path)
    layer_name = f"Statuts {taxonTitle}"

    if layer_name in available_layers["name"].values:
        old_file = pd.DataFrame(gpd.read_file(file_save_path, layer=layer_name))
            
        colonnes_sans_cd_ref = [col for col in status_df.columns if ((col not in ['CD_REF', "Région"]) and (col in old_file.columns))]
        old_file_light = old_file.drop(columns=colonnes_sans_cd_ref)

        # Merge les nouvelles colonne sur la couche "Status {taxonTitle}"
        result = pd.merge(old_file_light, status_df, on=['CD_REF', 'Région'], how='outer')

        # Conserver uniquement les lignes où au moins une des colonnes non exclues n'est pas vide
        reresult = result.dropna(axis=0, how="all", subset=[col for col in result.columns if col not in ["CD_REF", "Région"]])

        #gdf = gpd.GeoDataFrame(result.drop_duplicates())
        gdf = gpd.GeoDataFrame(reorder_columns(reresult.dropna(axis=1, how="all")).drop_duplicates() )

    else :
        # gdf = gpd.GeoDataFrame(status_df.drop_duplicates())
        gdf = gpd.GeoDataFrame(reorder_columns(status_df.dropna(axis=1, how="all")).drop_duplicates())

    gdf.to_file(file_save_path, layer=layer_name, driver="GPKG")

    return

def SaveNationalStatus(status_df: pd.DataFrame, path: str, taxonTitle: str, debug: int=0):
    
    now = datetime.now()
    QgsMessageLog.logMessage(f"\tPour {taxonTitle}, début de sauvegarde nationale ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    # Enregistrer dans un fichier GeoPackage    
    if taxonTitle == "Flore":
        file_save_path = os.path.join(path, f"{taxonTitle}.gpkg")
    else : 
        file_save_path = os.path.join(path, f"Faune.gpkg")
    old_file = pd.DataFrame(gpd.read_file(file_save_path, layer=f"Liste {taxonTitle}"))

    colonnes_sans_cd_ref = [col for col in status_df.columns if ((col != 'CD_REF') and (col in old_file.columns))]

    old_file['CD_REF'] = old_file['CD_REF'].astype(str) 
    status_df['CD_REF'] = status_df['CD_REF'].astype(str)

    if debug > 2:
        QgsMessageLog.logMessage(f"Pour {taxonTitle} : les colonnes de status_df sont {status_df.columns}", "AutoUpdateTAXREF", level=Qgis.Info)

    result = pd.merge(old_file.drop(columns=colonnes_sans_cd_ref), status_df, on='CD_REF', how='outer').dropna(axis=1, how="all")
    
    if debug > 2 :
        QgsMessageLog.logMessage(f"Pour {taxonTitle} : les colonnes de result sont {result.columns}", "AutoUpdateTAXREF", level=Qgis.Info)

    reresult = reorder_columns(result).drop_duplicates()

    if taxonTitle == "Oiseaux":

        reresult = reresult.drop(columns=["LRN"])

    if debug > 2 :
        QgsMessageLog.logMessage(f"Pour {taxonTitle} : les colonnes de reresult sont {reresult.columns}", "AutoUpdateTAXREF", level=Qgis.Info)

    gdf = gpd.GeoDataFrame(reresult)
    gdf.to_file(file_save_path, layer=f"Liste {taxonTitle}", driver="GPKG")

    return

def SaveNewSources(path: str,
                   newVer: bool=False,
                   newSources: pd.DataFrame=pd.DataFrame(columns=["id", "fullCitation"]))->None:

    file_path_source = os.path.join(path, "Autre.gpkg")
    if newVer :
        current_year = date.today().year
        sources = pd.concat([GetSourcesFromYear(current_year),
                             GetSourcesFromYear(current_year-1)], ignore_index=True)[["id", "fullCitation"]]

    else :
        if os.path.isfile(file_path_source):
            available_layer = gpd.list_layers(file_path_source)
            if "Source" in available_layer["name"].values:
                sources = pd.DataFrame(gpd.read_file(file_path_source, layer="Source"))
            else :
                sources = pd.DataFrame(columns=["id", "fullCitation"])
        else :
            sources =  pd.DataFrame(columns=["id", "fullCitation"])

        sources = pd.concat([sources, newSources], ignore_index=True)
    
    sources_gdf = gpd.GeoDataFrame(sources)
    sources_gdf.to_file(file_path_source, layer="Source")

    return
