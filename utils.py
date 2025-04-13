from qgis.core import QgsMessageLog, Qgis
from datetime import datetime
import os
import pandas as pd

# Constante variables

# Flore
FLORE = {"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]}

# Fonge
FONGE = {"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]}

# Faune
AMPHIBIENS = {"title": "Amphibiens",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Chordés"],
         "groupe2": ["Amphibiens"],
         "groupe3": [""],
         "famille": [""]}

REPTILES = {"title": "Reptiles",
         "regne": "Animalia",
         "groupe1": ["Chordés"],
         "groupe2": ["Reptiles"],
         "groupe3": [""],
         "famille": [""]}

OISEAUX = {"title": "Oiseaux",
         "regne": "Animalia",
         "groupe1": ["Chordés"],
         "groupe2": ["Oiseaux"],
         "groupe3": [""],
         "famille": [""]}

MAMMIFERES = {"title": "Mammifères",
         "regne": "Animalia",
         "ordre": ["Afrosoricida", "Carnivora", "Cetartiodactyla", "Diprotodontia", "Eulipotyphla", "Lagomorpha", "Perissodactyla", "Proboscidea", "Rodentia"],
         "groupe1": ["Chordés"],
         "groupe2": ["Mammifères"],
         "groupe3": [""],
         "famille": [""]}

CHIROPTERES = {"title": "Mammifères",
         "regne": "Animalia",
         "Ordre": ["Chiroptera"],
         "groupe1": ["Chordés"],
         "groupe2": ["Mammifères"],
         "groupe3": ["Autres"],
         "famille": [""]}

LEPIDOPTERES = {"title": "Lépidoptères",
         "regne": "Animalia",
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Lépidoptères"],
         "famille": ["Papilionidae", "Pieridae", "Nymphalidae", "Satyrinae",
            "Lycaenidae", "Hesperiidae", "Zygaenidae"]}

ODONATES = {"title": "Odonates",
         "regne": "Animalia",
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Odonates"],
         "famille": [""]}

COLEOPTERES = {"title": "Coléoptères",
         "regne": "Animalia",
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Coléoptères"],
         "famille": ["Carabidae", "Hydrophilidae", "Sphaeritidae", "Histeridae",
            "Ptiliidae", "Agyrtidae", "Leiodidae", "Staphylinidae",
            "Lucanidae", "Trogidae", "Scarabaeidae", "Eucinetidae",
            "Clambidae", "Scirtidae", "Buprestidae", "Elmidae", "Dryopidae",
            "Cerophytidae", "Eucnemidae", "Throscidae", "Elateridae",
            "Lycidae", "Cantharidae", "Derodontidae", "Nosodendridae",
            "Dermestidae", "Endecatomidae", "Bostrichidae", "Ptinidae",
            "Lymexylidae", "Phloiophilidae", "Trogossitidae", "Thanerocleridae",
            "Cleridae", "Acanthocnemidae", "Melyridae", "Malachiidae",
            "Sphindidae", "Nitidulidae", "Monotomidae", "Phloeostichidae",
            "Silvanidae", "Cucujidae", "Laemophloeidae", "Cryptophagidae",
            "Erotylidae", "Biphyllidae", "Bothrideridae", "Cerylonidae",
            "Alexiidae", "Endomychidae", "Corylophidae", "Latridiidae",
            "Mycetophagidae", "Ciidae", "Tetratomidae", "Melandryidae",
            "Zopheridae", "Mordellidae", "Tenebrionidae", "Prostomidae",
            "Oedemeridae", "Pythidae", "Pyrochroidae", "Salpingidae",
            "Aderidae", "Scraptiidae", "Cerambycidae", "Chrysomelidae",
            "Anthribidae", "Brentidae", "Dryophthoridae", "Curculionidae"]}

ORTHOPTERES = {"title": "Orthoptères",
         "regne": "Animalia",
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Orthoptères"],
         "famille": ["Acrididae", "Gryllidae", "Gryllotalpidae", "Mogoplistida",
            "Myrmecophilidae", "Pamphagidae", "Phalangopsidae",
            "Pyrgomorphidae", "Rhaphidophoridae", "Tetrigidae",
            "Tettigoniidae", "Tridactylidae", "Trigonidiidae"]}

EPHEMERES = {"title": "Éphémères",
         "regne": "Animalia",
         "ordre" : ["Ephemeroptera"],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Autres"],
         "famille": [""]}

ARAIGNEES = {"title": "Araignées",
         "regne": "Animalia",
         "groupe1": ["Arthropodes"],
         "groupe2": ["Arachnides"],
         "groupe3": ["Araignées", "Opilions", "Pseudoscorpions", "Scorpions"],
         "famille": [""]}

MOLLUSQUES = {"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]}

CRUSTACES = {"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]}

POISSONS = {"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]}

TAXONS = [FLORE, FONGE, AMPHIBIENS, REPTILES, OISEAUX, MAMMIFERES, CHIROPTERES, LEPIDOPTERES, ODONATES, COLEOPTERES, ORTHOPTERES, EPHEMERES, ARAIGNEES, MOLLUSQUES, CRUSTACES, POISSONS]

class TaxonGroupe():

    def __init__(self, title: str,
                 regne: str,
                 ordre: list,
                 groupe1: list,
                 groupe2: list,
                 groupe3: list,
                 famille: list):
        
        self.title = title
        self.regne = regne
        self.ordre = ordre
        self.groupe1 = groupe1
        self.groupe2 = groupe2
        self.groupe3 = groupe3
        self.famille = famille

    def isflore(self):
        return self.regne == "Plantae"
    
    def isfaune(self):
        return self.regne == "Animalia"
    
    def isfungi(self):
        return self.regne == "Fungi"
    
    def is_ordre_empty(self):
        return self.ordre == [""]
    
    def is_groupe1_empty(self):
        return self.groupe1 == [""]
    
    def is_groupe2_empty(self):
        return self.groupe2 == [""]
    
    def is_groupe3_empty(self):
        return self.groupe3 == [""]

    def is_famille_empty(self):
        return self.famille == [""]

    def filtre_df(self, df: pd.DataFrame, synonyme: bool=False):
        """
        Filtre les lignes d'un DataFrame en fonction des critères spécifiques
        relatifs à un groupe taxonomique, à la présence d'un nom français et à la validité du taxon.

        Args:
            df (pd.DataFrame): Le DataFrame contenant les données à filtrer.
            synonyme (bool): Indique si les synonymes doivent être inclus. Par défaut, False.

        Returns:
            pd.DataFrame: Un DataFrame filtré selon les critères spécifiés.
        """

        # Base : conditions toujours présentes
        conditions = [
            df['REGNE'] == self.regne,
            df['GROUP1_INPN'].isin(self.groupe1),
            df['FR'].isin(['P', 'E', 'S', 'C', 'I', 'J', 'M', 'B', 'D', 'G'])
        ]

        # Ordre, si précisé
        if not self.is_ordre_empty() :
            conditions.append(df['ORDRE'].isin(self.ordre))

        # Groupe2, si précisé
        if not self.is_groupe2_empty() :
            conditions.append(df['GROUP2_INPN'].isin(self.groupe2))

        # Groupe3, si précisé
        if not self.is_groupe3_empty() :
            conditions.append(df['GROUP3_INPN'].isin(self.groupe3))

        # Famille, si précisé
        if not self.is_famille_empty() :
            conditions.append(df['FAMILLE'].isin(self.famille))

        # Validité taxonomique
        if not synonyme:
            conditions.append(df['CD_NOM'] == df['CD_REF'])

        # Application des filtres combinés
        final_condition = pd.concat(conditions, axis=1).all(axis=1)

        df_filtre = df[final_condition]
        
        return df_filtre

TAXONS = [TaxonGroupe(TAXONS)]


def print_debug_info(debug_level: int,
                     debug_threshold: int,
                     msg: str,
                     name: str="")->None:

    if debug_level > debug_threshold :
        now = datetime.now()
        QgsMessageLog.logMessage(name+msg+f" ({now.hour:02}:{now.minute:02}:{now.second:02}.{now.microsecond // 1000:03})", "AutoUpdateTAXREF", level=Qgis.Info)

    return

def get_file_save_path(path: str,
                       taxon_title: str)->str:
    
    if taxon_title == "Flore":
        file_save_path = os.path.join(path, f"{taxon_title}.gpkg")
    else : 
        file_save_path = os.path.join(path, f"Faune.gpkg")

    return file_save_path