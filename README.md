# AutoUpdateTAXREF – Plugin QGIS pour la mise à jour automatique des espèces et statuts via l'API TAXREF de l'INPN 🔄

AutoUpdateTAXREF est un plugin QGIS qui permet d'automatiser la mise à jour des espèces et de leurs statuts directement depuis l'API TAXREF fournie par l'INPN.

## 🎯 Objectif
Ce plugin simplifie la mise à jour des espèces et de leurs statuts dans des projets QGIS comme QBiome, QFlore, QFaune ou tout autre projet QField naturaliste (comme par exemple : [QFieldNatura](https://github.com/ElisaFage/QFieldNatura/archive/refs/heads/main.zip)).

## 📋 Prérequis
- Un projet QGIS contenant un fichier GeoPackage nommé `Données`.
- Ce GeoPackage doit contenir des couches dont les noms correspondent exactement aux taxons à mettre à jour. Ces noms doivent être au singulier, sans accent et avec une majuscule initiale. Voici la liste précise des taxons pris en charge : Amphibien, Avifaune, Araignee, Coleoptere, Crustace, Ephemere, Mammifere, Mollusque, Odonates, Orthoptere, Poisson, Reptile, Chiroptere, Lepidoptere, Flore, Fonge.
- Avoir une connexion internet pour que le programme accède à l'API de TAXREF.

## ⚙️ Fonctionnement
À chaque ouverture d'un projet dans QGIS, AutoUpdateTAXREF vérifie automatiquement :
- ✅ Si la version actuelle de TAXREF est à jour.
- 🔄 Si de nouveaux statuts sont disponibles.

À partir des couches taxonomiques présentes dans le GeoPackage `Données`, le plugin génère automatiquement deux types de couches par taxon dans le GeoPackage `Statuts` (si elles n'existent pas déjà) :
- 📃 `Liste` : liste actualisée des espèces.
- 📌 `Statuts` : statuts actualisés pour chaque espèce.

Vous pouvez également déclencher manuellement une mise à jour via l'icône 🔄 d'AutoUpdateTAXREF située dans la commande `Extensions` de la barre d'outils de QGIS.

Lorsqu'une mise à jour est disponible, le plugin propose automatiquement de l'appliquer aux espèces ou statuts concernés.
Les statuts pris en compte incluent : Directive Habitat, Directive Oiseaux, Protection nationale, Protection régionale, Protection départementale, Liste rouge nationale, Liste rouge régionale, PNA (Plans Nationaux d'Actions), PAPNAT (Priorité Action Publique Nationale), Déterminantes ZNIEFF et Lutte contre certaines espèces.

À noter que pour les statuts régionaux, toutes les régions de France métropolitaine sont concernées (les statuts outre-mer sont exclus par le programme). Vous devez spécifier dans votre projet QField la région française pour laquelle vous souhaitez suivre les statuts des taxons.

Le programme ajoute une couche `Sources` dans le GeoPackage `Données` qui permet de vérifier les mises à jour des statuts. Cette couche ne doit pas être supprimée.

## 🔗 Compatibilité
* Compatible avec QGIS sur les projets QBiome, QFlore, QFaune et tout autre projet QField naturaliste possédant les GeoPackages `Données` et `Statuts`.

## 📥 Installation
Recherchez et installez le plugin directement depuis le gestionnaire d'extensions de QGIS en tapant "AutoUpdateTAXREF".

## 🗃️ Catégorisation TAXREF des espèces gérées par AutoUpdateTAXREF :
🌿 Flore
* GROUP1_INPN : Algues, Bryophytes, Trachéophytes

🍄 Fonge
* GROUP1_INPN : Ascomycètes, Basidomycètes

🐦 Faune
* Avifaune : Classe Aves
* Amphibiens : Classe Amphibia
* Reptiles : GROUP2_INPN
* Mammifères (terrestres, aquatiques, semi-aquatiques) : Ordres Afrosoricida, Carnivora, Cetartiodactyla, Diprotodontia, Eulipotyphla, Lagomorpha, Perissodactyla, Proboscidea, Rodentia
* Chiropères : Ordre Chiroptera
* Poissons : GROUP2_INPN Poissons
* Mollusques : GROUP2_INPN Mollusques

🦋 Insectes
* Odonates : Ordre Odonata
* Orthoptères : Familles Acrididae, Gryllidae, Gryllotalpidae, Mogoplistidae, Myrmecophilidae, Pamphagidae, Phalangopsidae, Pyrgomorphidae, Rhaphidophoridae, Tetrigidae, Tettigoniidae, Tridactylidae, Trigonidiidae
* Lepidoptères : Familles Papilionidae, Pieridae, Nymphalidae, Satyrinae, Lycaenidae, Hesperiidae, Zygaenidae
* Coleoptères : Familles Carabidae, Hydrophilidae, Sphaeritidae, Histeridae, Ptiliidae, Agyrtidae, Leiodidae, Staphylinidae, Lucanidae, Trogidae, Scarabaeidae, Eucinetidae, Clambidae, Scirtidae, Buprestidae, Elmidae, Dryopidae, Cerophytidae, Eucnemidae, Throscidae, Elateridae, Lycidae, Cantharidae, Derodontidae, Nosodendridae, Dermestidae, Endecatomidae, Bostrichidae, Ptinidae, Lymexylidae, Phloiophilidae, Trogossitidae, Thanerocleridae, Cleridae, Acanthocnemidae, Melyridae, Malachiidae, Sphindidae, Nitidulidae, Monotomidae, Phloeostichidae, Silvanidae, Cucujidae, Laemophloeidae, Cryptophagidae, Erotylidae, Biphyllidae, Bothrideridae, Cerylonidae, Alexiidae, Endomychidae, Corylophidae, Latridiidae, Mycetophagidae, Ciidae, Tetratomidae, Melandryidae, Zopheridae, Mordellidae, Tenebrionidae, Prostomidae, Oedemeridae, Pythidae, Pyrochroidae, Salpingidae, Aderidae, Scraptiidae, Cerambycidae, Chrysomelidae, Anthribidae, Brentidae, Dryophthoridae, Curculionidae
* Ephémères : Ordre Ephemeroptera
* Araignées : GROUP3_INPN Araignées, Opilions, Pseudoscorpions, Scorpions
* Crustacés : GROUP2_INPN Crustacés
  
