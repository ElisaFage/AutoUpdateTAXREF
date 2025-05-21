import requests
import pandas as pd


class StatusType():

    types_url = "https://taxref.mnhn.fr/api/status/types"

    def __init__(self,
                 type_id: str,
                 name: str,
                 admin_level:str):
        
        self.type_id = type_id
        self.name = name
        self.admin_level = admin_level
        self.in_api = True

    def is_national(self):
        return True if self.admin_level == "national" else False
    
    def is_regional(self):
        return not self.is_national()
    
    def is_in_api(self):
        
        response = requests.get(self.types_url)
        data_json = response.json()

        status_list = data_json['_embedded']['statusTypes']
        df_page = pd.json_normalize(status_list, sep='_')
        list_types = df_page["id"].to_list()

        return self.type_id in list_types
    
    def set_in_api(self, bool_val: bool=None):
        if bool_val == None :
            self.in_api = self.is_in_api()
        else :
            self.in_api = bool_val

DIRECTIVE_HABITAT = StatusType(**{"type_id": "DH",
                     "name": "Directive Habitat",
                     "admin_level": "national"})
DIRECTIVE_OISEAUX = StatusType(**{"type_id": "DO",
                     "name": "Directive Oiseaux",
                     "admin_level": "national"})
PROTECTION_NATIONALE = StatusType(**{"type_id": "PN",
                        "name": "Protection Nationale",
                        "admin_level": "national"})
PROTECTION_REGIONALE = StatusType(**{"type_id": "PR",
                        "name": "Protection Régionale",
                        "admin_level": "régional"})
PROTECTION_DEPARTEMENTALE = StatusType(**{"type_id": "PD",
                             "name": "Protection Départementale",
                             "admin_level": "régional"})
LISTE_ROUGE_NATIONALE = StatusType(**{"type_id": "LRN",
                         "name": "Liste Rouge Nationale",
                         "admin_level": "national"})
LISTE_ROUGE_REGIONALE = StatusType(**{"type_id": "LRR",
                         "name": "Liste Rouge Régionale",
                         "admin_level": "régional"})
PLAN_NATIONAL_ACTION = StatusType(**{"type_id": "PNA",
                         "name": "Plan National d'Action",
                         "admin_level": "national"})
PRIORITE_ACTION_PUBLIQUE_NATIONALE = StatusType(**{"type_id": "PAPNAT",
                                      "name": "Priorité Action Publique ationale",
                                      "admin_level": "national"})
DETERMINANT_ZNIEFF = StatusType(**{"type_id": "ZDET",
                      "name": "ZNIEFF Déterminantes",
                      "admin_level": "régional"})
LUTTE_CONTRE_ESPECES = StatusType(**{"type_id": "REGLLUTTE",
                        "name": "Lutte contre certaines espèces",
                        "admin_level": "régional"})


STATUS_TYPES = [DIRECTIVE_HABITAT, DIRECTIVE_OISEAUX,
                PROTECTION_NATIONALE, PROTECTION_REGIONALE, PROTECTION_DEPARTEMENTALE,
                LISTE_ROUGE_NATIONALE, LISTE_ROUGE_REGIONALE, DETERMINANT_ZNIEFF,
                PLAN_NATIONAL_ACTION, PRIORITE_ACTION_PUBLIQUE_NATIONALE,
                LUTTE_CONTRE_ESPECES]
STATUS_IDS = [status.type_id for status in STATUS_TYPES]

def get_status_types_from_ids(list_ids: list[str]):
    return [status for status in STATUS_TYPES if status.type_id in list_ids]
