import os
import pandas as pd
 
from .utils import (save_dataframe, save_to_gpkg_via_qgs, 
                    print_debug_info, get_file_save_path,
                    list_layers_from_gpkg, list_layers_from_qgis,
                    load_layer_as_dataframe, load_layer, parse_layer_to_dataframe)
from .taxongroupe import (OISEAUX)
from .statustype import (LISTE_ROUGE_NATIONALE,
                         LISTE_ROUGE_REGIONALE,
                         DIRECTIVE_HABITAT,
                         DIRECTIVE_OISEAUX,
                         PRIORITE_ACTION_PUBLIQUE_NATIONALE,
                         PROTECTION_DEPARTEMENTALE,
                         PROTECTION_NATIONALE,
                         PROTECTION_REGIONALE,
                         PLAN_NATIONAL_ACTION,
                         LUTTE_CONTRE_ESPECES,
                         DETERMINANT_ZNIEFF)

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
    status_ids = [DIRECTIVE_HABITAT.type_id, DIRECTIVE_OISEAUX.type_id,
                  PROTECTION_NATIONALE.type_id, PROTECTION_REGIONALE.type_id,
                  PROTECTION_DEPARTEMENTALE.type_id,
                  LISTE_ROUGE_NATIONALE.type_id, LISTE_ROUGE_REGIONALE.type_id,
                  PLAN_NATIONAL_ACTION.type_id, PRIORITE_ACTION_PUBLIQUE_NATIONALE.type_id,
                  DETERMINANT_ZNIEFF.type_id, LUTTE_CONTRE_ESPECES.type_id]

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
            key=lambda col: (
                col == status,  # "statusId" prioritaire
                col.startswith("sourceId"),  # Puis "sourceID_statusId"
                col.startswith("source")  # Enfin "source_statusId"
            ),
            reverse=True)

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

    print_debug_info(debug, 1, f"\tPour {taxon_title}, début de sauvegarde {save_type}")

    # Colonnes pour le merge
    col_to_check = ["CD_REF"]
    national_value = "national"
    regional_value = "regional"
    bird_col = []

    # Construction du chemin vers le fichier GeoPackage
    file_save_path = get_file_save_path(path, taxon_title)

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

    layer = load_layer(file_save_path, layer_name)
    # Si une couche existe déjà, on la lit et prépare une fusion avec les nouvelles données
    if layer.isValid() :#["name"].values:
        print_debug_info(debug, 3, f"{layer_name} is valid")
        old_file = parse_layer_to_dataframe(layer)
        #load_layer_as_dataframe(file_save_path, layer_name=layer_name)
        if not old_file.empty :
            #pd.DataFrame(gpd.read_file(file_save_path, layer=layer_name))

            print_debug_info(debug, 3, f"{layer_name} old_file : {old_file.columns}")

            # Forcer les colonnes clé en chaîne pour éviter les erreurs de jointure
            old_file['CD_REF'] = old_file['CD_REF'].astype(str) 
            status_df['CD_REF'] = status_df['CD_REF'].astype(str)
    
            # Colonnes communes à retirer de l'ancien fichier pour ne pas écraser les nouvelles données
            colonnes_sans_cd_ref = [col for col in status_df.columns if ((col not in col_to_check) and (col in old_file.columns))]
            
            print_debug_info(debug, 3, f"Pour {taxon_title} : les colonnes de status_df sont {status_df.columns}")

            # Nettoyer la version ancienne pour préparer le merge
            colonnes_a_supprimer = [col for col in colonnes_sans_cd_ref + bird_col if col in old_file.columns]
            old_file_light = old_file.drop(columns=colonnes_a_supprimer)
            
            # Fusion : priorise les clés communes et conserve les lignes valides
            # Si la sauvegarde est régionale
            if save_type == regional_value:
                status_merged_heavy = pd.merge(old_file_light, status_df, on=col_to_check, how='outer')
                print_debug_info(debug, 3, f"Pour {taxon_title} : les colonnes de merged heavy sont {status_merged_heavy.columns}")

                # Colonnes à tester pour la suppression des lignes vides après fusion (axis=0)
                subset_col_dropna = [col for col in status_merged_heavy.columns if col not in col_to_check]
                status_merged = status_merged_heavy.dropna(axis=0, how="all", subset=subset_col_dropna)
            
            # Si la sauvegarde n'est pas régionale : nationale
            else:
                status_merged = pd.merge(old_file_light, status_df, on=col_to_check, how='outer')

            print_debug_info(debug, 3, f"Pour {taxon_title} : les colonnes de merged sont {status_merged.columns}")

            # Supprime les colonnes vides de la table fusionnée
            status_na_dropped = status_merged.dropna(axis=1, how="all")

        else:
            # Si aucune couche existante, on nettoie juste les colonnes vides (axis=1)
            status_na_dropped = status_df.dropna(axis=1, how="all")

    else:
        print_debug_info(debug, 3, f"{layer_name} is not Valid")
        # Si aucune couche existante, on nettoie juste les colonnes vides (axis=1)
        status_na_dropped = status_df.dropna(axis=1, how="all")

    print_debug_info(debug, 3, f"Pour {taxon_title} : les colonnes de result sont {status_na_dropped.columns}")

    # Réorganise les colonnes de manière standard et supprime les doublons
    status_to_save = reorder_columns(status_na_dropped).drop_duplicates()

    print_debug_info(debug, 3, f"Pour {taxon_title} : les colonnes après reordonnancement sont {status_to_save.columns}")
        
    # Convertit le DataFrame en GeoDataFrame et sauvegarde dans le fichier GeoPackage
    save_to_gpkg_via_qgs(status_to_save, file_save_path, layer_name, debug=debug)

    return
