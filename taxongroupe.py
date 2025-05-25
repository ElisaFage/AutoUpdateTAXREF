import pandas as pd
from .utils import list_layers_from_gpkg, list_layers_from_qgis, print_debug_info
#from utils2 import list_layers_from_gpkg, list_layers_from_qgis, print_debug_info

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

# Constante variables

# Flore
FLORE = TaxonGroupe(**{"title": "Flore",
         "regne": "Plantae",
         "ordre": [""],
         "groupe1": ["Algues", "Trachéophytes", "Bryophytes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]})
# Fonge
FONGE = TaxonGroupe(**{"title": "Fonge",
         "regne": "Fungi",
         "ordre": [""],
         "groupe1": ["Ascomycètes", "Basidomycètes"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]})

# Faune
AMPHIBIENS = TaxonGroupe(**{"title": "Amphibien",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Chordés"],
         "groupe2": ["Amphibiens"],
         "groupe3": [""],
         "famille": [""]})

REPTILES = TaxonGroupe(**{"title": "Reptile",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Chordés"],
         "groupe2": ["Reptiles"],
         "groupe3": [""],
         "famille": [""]})

OISEAUX = TaxonGroupe(**{"title": "Avifaune",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Chordés"],
         "groupe2": ["Oiseaux"],
         "groupe3": [""],
         "famille": [""]})

MAMMIFERES = TaxonGroupe(**{"title": "Mammifere",
         "regne": "Animalia",
         "ordre": ["Afrosoricida", "Carnivora", "Cetartiodactyla", "Diprotodontia", "Eulipotyphla", "Lagomorpha", "Perissodactyla", "Proboscidea", "Rodentia"],
         "groupe1": ["Chordés"],
         "groupe2": ["Mammifères"],
         "groupe3": [""],
         "famille": [""]})

CHIROPTERES = TaxonGroupe(**{"title": "Chiroptere",
         "regne": "Animalia",
         "ordre": ["Chiroptera"],
         "groupe1": ["Chordés"],
         "groupe2": ["Mammifères"],
         "groupe3": ["Autres"],
         "famille": [""]})

LEPIDOPTERES = TaxonGroupe(**{"title": "Lepidoptere",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Lépidoptères"],
         "famille": ["Papilionidae", "Pieridae", "Nymphalidae", "Satyrinae",
            "Lycaenidae", "Hesperiidae", "Zygaenidae"]})

ODONATES = TaxonGroupe(**{"title": "Odonate",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Odonates"],
         "famille": [""]})

COLEOPTERES = TaxonGroupe(**{"title": "Coleoptere",
         "regne": "Animalia",
         "ordre": [""],
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
            "Anthribidae", "Brentidae", "Dryophthoridae", "Curculionidae"]})

ORTHOPTERES = TaxonGroupe(**{"title": "Orthoptere",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Orthoptères"],
         "famille": ["Acrididae", "Gryllidae", "Gryllotalpidae", "Mogoplistida",
            "Myrmecophilidae", "Pamphagidae", "Phalangopsidae",
            "Pyrgomorphidae", "Rhaphidophoridae", "Tetrigidae",
            "Tettigoniidae", "Tridactylidae", "Trigonidiidae"]})

EPHEMERES = TaxonGroupe(**{"title": "Ephemere",
         "regne": "Animalia",
         "ordre" : ["Ephemeroptera"],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Insectes"],
         "groupe3": ["Autres"],
         "famille": [""]})

ARAIGNEES = TaxonGroupe(**{"title": "Araignee",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Arachnides"],
         "groupe3": ["Araignées", "Opilions", "Pseudoscorpions", "Scorpions"],
         "famille": [""]})

MOLLUSQUES = TaxonGroupe(**{"title": "Mollusque",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Mollusques"],
         "groupe2": [""],
         "groupe3": [""],
         "famille": [""]})

CRUSTACES = TaxonGroupe(**{"title": "Crustace",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Arthropodes"],
         "groupe2": ["Crustacés"],
         "groupe3": [""],
         "famille": [""]})

POISSONS = TaxonGroupe(**{"title": "Poisson",
         "regne": "Animalia",
         "ordre": [""],
         "groupe1": ["Chordés"],
         "groupe2": ["Poissons"],
         "groupe3": [""],
         "famille": [""]})

TAXONS = [FLORE, FONGE, AMPHIBIENS, REPTILES,
               OISEAUX, MAMMIFERES, CHIROPTERES, LEPIDOPTERES,
               ODONATES, COLEOPTERES, ORTHOPTERES, EPHEMERES,
               ARAIGNEES, MOLLUSQUES, CRUSTACES, POISSONS]

TAXON_TITLES = [taxon.title for taxon in TAXONS]

def get_taxon_titles(path:str, prefix: str=None)->list[str]:
    """
    Récupère les noms de couches d'un GeoPackage,
    éventuellement filtrées par préfixe.

    Args:
        path (str): Chemin du fichier GeoPackage.
        prefix (str, optional): Préfixe recherché pour filtrer les couches.
                                Si None, retourne toutes les couches.

    Returns:
        list: Liste des noms de couches ou des noms de taxons extraits.
    """
    available_layers = list_layers_from_qgis(path)
    if not available_layers:
        return []

    if prefix is None:
        return available_layers

    print_debug_info(1,0,f"available_layers : {available_layers}")
    # Récupère les taxons après le préfix
    taxon_titles = [taxon.split(" ")[-1] for taxon in available_layers if taxon.startswith(prefix)]
    print_debug_info(1,0,f"taxon_titles : {taxon_titles}")
    # Récupère les titres correspondant à des titres de groupes de taxons 
    real_taxon_titles = [title for title in taxon_titles if title in TAXON_TITLES]
    #print_debug_info(1,0,f"real_taxon_titles : {real_taxon_titles}")
    return real_taxon_titles

def get_taxon_from_titles(taxon_titles: list[str])->list[TaxonGroupe]:
    return [taxon for taxon in TAXONS if taxon.title in taxon_titles]
