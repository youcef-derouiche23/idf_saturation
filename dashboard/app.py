# -*- coding: utf-8 -*-
"""
app_simple.py - Dashboard Streamlit simplifié pour IDFM
Version allégée pour éviter les problèmes de chargement infini
"""

import configparser
import os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# =====================================================
# CONFIGURATION
# =====================================================

CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "config.ini")
)
_config = configparser.ConfigParser()
_config.read(CONFIG_PATH)
_api = _config["api"]

API_URL = _api.get("api_url", "http://localhost:8000")
LOGIN_USER = _api.get("login_user", "admin")
LOGIN_PASSWORD = _api.get("login_password", "admin")

st.set_page_config(
    page_title="IDFM - Analyse du Réseau Ferré",
    page_icon="🚇",
    layout="wide",
)

st.title("🚇 Tableau de Bord IDFM - Réseau Ferré")
st.markdown("**Où et quand le réseau souffre-t-il le plus ?**")

# =====================================================
# MAPPING DES LIGNES ET JOURS
# =====================================================

# CORRECTION : Mapping complet des codes STIF aux noms de lignes IDFM
STIF_TO_LIGNE = {
    100: "RER A",
    760: "RER B",
    761: "RER C",
    762: "RER D",
    800: "RER E",
    810: "Transilien H",
    820: "Transilien J",
    830: "Transilien K",
    840: "Transilien L",
    850: "Transilien N",
    860: "Transilien P",
    870: "Transilien R",
    880: "Transilien U",
}

# Mapping des codes de jour-type
JOUR_TYPE_MAPPING = {
    "DIJFP": "Lundi-Vendredi",
    "JOHV": "Samedi",
    "JOVS": "Dimanche",
    "SAHV": "Samedi",
    "SAVS": "Dimanche",
}

def map_ligne_code_to_name(code):
    """Convertir un code de ligne en nom (ex: 100 -> 'RER A')"""
    try:
        code_int = int(code) if not isinstance(code, int) else code
        return STIF_TO_LIGNE.get(code_int, str(code))
    except (ValueError, TypeError):
        # Si la conversion en int échoue, utiliser le code tel quel
        return str(code)

def map_jour_type(jour_code):
    """Convertir un code de jour-type en nom lisible"""
    return JOUR_TYPE_MAPPING.get(str(jour_code), str(jour_code))

# Cache pour les stations
_STATION_CACHE = {}
_STATION_CACHE_LOADED = False

# Mapping statique des stations (ID -> Nom)
STATION_MAPPING = {
    "PORTE MAILLOT": [1, 590],
    "ABBESSES": [2],
    "ABLON": [3],
    "ACHERES GRAND": [4],
    "ACHERES VILLE": [6],
    "COURNEUVE": [34],
    "ALESIA": [10],
    "ALEXANDR.DUMAS": [11],
    "ALFORT-ECOLE V": [12],
    "ALMA-MARCEAU": [14],
    "ANATOLE FRANCE": [16],
    "ANDRESY": [17],
    "ANGERVILLE": [18],
    "ANTONY": [19, 20],
    "ANVERS": [21],
    "ARCUEIL-CACHAN": [22],
    "ARGENTEUIL": [24],
    "ARGENTINE": [25],
    "ARPAJON": [26],
    "ARTS.METIERS": [27],
    "ASNIERES SUR S": [29],
    "ASSEMBLEE NAT.": [30],
    "ATHIS MONS": [31],
    "AUBER": [32],
    "AUBERGENVILLE": [33],
    "AUBERV.4 CHEM.": [35],
    "AULNAY SS BOIS": [37],
    "AUSTERLITZ": [38],
    "AUVERS SUR OISE": [39],
    "AVENUE DU PRESIDENT KENNEDY": [40],
    "AVENUE FOCH": [41],
    "AVENUE HENRI MARTIN": [42],
    "AV.EMILE ZOLA": [43],
    "AVRON": [44],
    "BAGNEUX": [45],
    "BAGNEAUX SUR L": [46],
    "BALARD": [47],
    "BALLANCOURT": [48],
    "BARBES-ROCH.": [49],
    "BASTILLE": [54],
    "BECON": [58],
    "BEL AIR": [59],
    "BELLEVILLE": [60],
    "BELLEVUE": [62],
    "BELLOY ST MA": [63],
    "BERAULT": [65],
    "BERCY": [66, 1019],
    "BESSANCOURT": [68],
    "BEYNES": [69],
    "BIBLIOTHEQUE FRANCOIS MITTERRAND": [71],
    "BIBLIOTHEQUE": [72],
    "BIEVRES": [73],
    "BILLANCOURT": [74],
    "BIR-HAKEIM": [75],
    "BLANC MESNIL": [77],
    "BLANCHE": [76],
    "BOB.P.PICASSO": [79],
    "BOB.R.QUENEAU": [80],
    "BOIGNEVILLE": [81],
    "BOIS COLOMBES": [82],
    "BOIS LE ROI": [83],
    "BOISSIERE": [84],
    "BOISSISE LE ROI": [85],
    "BOISSY L AILLER": [86],
    "BOISSY-ST-LEG.": [87],
    "BOLIVAR": [88],
    "BONDY GARE": [89],
    "BONNE NOUVELLE": [90],
    "BONNIERES": [92],
    "BOTZARIS": [93],
    "BOUCICAUT": [94],
    "BOUFFEMONT": [95],
    "BOUGIVAL": [96],
    "BOULAINVILLIERS": [97],
    "BOULETS-MONTR.": [98],
    "BOULOGNE-J.J.": [99],
    "BOULOGNE-ST.CL": [100],
    "BOURAY": [101],
    "BOURG-LA-REINE": [102],
    "BOURRON MARLOTT": [103],
    "BOURSE": [104],
    "BOUSSY ST ANTOI": [105],
    "BOUTIGNY": [106],
    "BREGUET-SABIN": [107],
    "BRETIGNY": [108],
    "BREUILLET BRUYE": [109],
    "BREUILLET VILLA": [110],
    "BREVAL": [111],
    "BROCHANT": [113],
    "BRUNOY": [114],
    "BRUYERES SUR O": [115],
    "BRY-SUR-MARNE": [116],
    "BUNO GIRONVILLE": [117],
    "BURES-S-YVETTE": [118],
    "BUSSY-ST-GEOR.": [119],
    "BUTTES-CHAUM.": [120],
    "BUZENVAL": [121],
    "CADET": [122],
    "CAMBRONNE": [123],
    "CAMPO-FORMIO": [124],
    "CARD.LEMOINE": [125],
    "CARREF.PLEYEL": [126],
    "CENSIER DAUB.": [127],
    "CERGY LE HAUT": [128],
    "CERGY PREFECTUR": [129],
    "CERGY ST CHRIST": [131],
    "CERNAY": [133],
    "CESSON": [135],
    "CH.D.G.ETOILE": [151, 152],
    "CH.D.VINCENNES": [160],
    "CHAMARANDE": [137],
    "CHAMP DE COURSE": [143],
    "CHAMP DE MARS-TOUR EIFFEL": [141],
    "CHAMPAGNE OISE": [138],
    "CHAMPAGNE SEINE": [139],
    "CHAMPBENOIST": [140],
    "CHAMPIGNY": [142],
    "CHAMPS-ELYSEES": [144],
    "CHANGIS ST JEAN": [146],
    "CHANTELOUP": [147],
    "CHAPONVAL": [148],
    "CHARDON-LAGACH": [149],
    "CHARENTON-ECO.": [150],
    "CHARL.MICHELS": [155],
    "CHARONNE": [156],
    "CHARS": [157],
    "CHARTRETTES": [158],
    "CHATEAU D'EAU": [159],
    "CHATEAU ROUGE": [162],
    "CHATEAU-LANDON": [161],
    "CHATELET": [163, 165],
    "CHATILLON-MON.": [171],
    "CHATOU-CROISSY": [172],
    "CHAUSS.D'ANTIN": [173],
    "CHAVILLE RD": [175],
    "CHAVILLE RG": [176],
    "CHAVILLE VELIZY": [177],
    "CHELLES GOURNAY": [178],
    "CHEMIN D ANTONY": [179],
    "CHEMIN-VERT": [180],
    "CHENAY GAGNY": [181],
    "CHEVALERET": [183],
    "CHILLY MAZ T12": [184],
    "CHOISY LE ROI": [185],
    "CITE": [188],
    "CITE UNIV.": [189],
    "CLAMART": [190],
    "CLICHY LEVALLOI": [191],
    "COLOMBES": [194],
    "COLONEL FABIEN": [195],
    "COMBS LA VILLE": [196],
    "COMMERCE": [197],
    "COMPANS": [198],
    "CONCORDE": [199],
    "CONFLANS FO": [202],
    "CONFLANS STE HO": [205],
    "CONVENTION": [206],
    "CORBEIL ESSONNE": [207],
    "CORENT.CARIOU": [209],
    "CORENT.CELTON": [210],
    "CORMEILLES": [211],
    "CORVISART": [212],
    "COUDRAY MONTCEA": [214],
    "COURBEVOIE": [217],
    "COURCELLE-S-YV": [219],
    "COURCELLES": [218],
    "COURONNES": [220],
    "CRETEIL-ECHAT": [223],
    "CRETEIL-PREF.": [224],
    "CRETEIL-UNIV.": [226],
    "CRIMEE": [227],
    "CROUY SUR OURCQ": [229],
    "CRX.DE CHAVAUX": [228],
    "DAMMARTIN": [230],
    "DANUBE": [232],
    "DAUMESNIL": [233],
    "DENFERT-ROCH.": [235, 236],
    "DEUIL MONTMAGNY": [238],
    "DOMONT": [239],
    "DOURDAN": [240],
    "DOURDAN LA FORE": [241],
    "DRANCY": [242],
    "DUGOMMIER": [244],
    "DUPLEIX": [245],
    "DUROC": [246],
    "EC.MILITAIRE": [248],
    "ECOUEN": [249],
    "EDGAR QUINET": [250],
    "EGLI.D'AUTEUIL": [251],
    "EGLI.DE PANTIN": [253],
    "EGLY": [254],
    "ENGHIEN": [256],
    "EPINAY SUR ORGE": [257],
    "EPINAY SUR SEIN": [258],
    "EPINAY VILLETAN": [259],
    "EPLUCHES": [260],
    "EPONE MEZIERES": [262],
    "ERAGNY NEUVILLE": [263],
    "ERMONT EAUBONNE": [266],
    "ERMONT HALTE": [264],
    "ESBLY": [267],
    "ESPLANADE DEF.": [269],
    "ESSONNES ROBINS": [270],
    "ETAMPES": [271],
    "ETIENNE MARCEL": [273],
    "ETRECHY": [274],
    "EUROPE": [275],
    "EVRY": [276],
    "EVRY COURCOURON": [277],
    "EXELMANS": [278],
    "F.D.ROOSEVELT": [293],
    "FAIDHERBE-CHA.": [279],
    "FALGUIERE": [280],
    "FAREMOUTIERS": [281],
    "FELIX FAURE": [282],
    "FILLES DU CALV": [283],
    "FONTAINE LE POR": [285],
    "FONTAINE-MICH.": [286],
    "FONTAINEBLEAU": [284],
    "FONTENAY FLEURY": [288],
    "FONTENAY-AUX-R": [287],
    "FONTENAY-S-B.": [289],
    "FORT D'AUBERV.": [290],
    "FRANCONVILLE": [291],
    "FREPILLON": [296],
    "FUNICULAIRE": [1017],
    "GABRIEL PERI": [297],
    "GAGNY GARE": [298],
    "GAITE": [299],
    "GALLIENI": [300],
    "GAMBETTA": [301],
    "GARANCIERES": [303],
    "GARCHES MARNES": [304],
    "GARE D'AUSTER.": [311],
    "GARE DE L'EST": [305, 313],
    "GARE DE LYON": [306, 307, 317],
    "GARE DU NORD": [308, 318],
    "GARGENVILLE": [321],
    "GARGES SARCELLE": [322],
    "GARIBALDI": [323],
    "GAZERAN": [325],
    "GENNEVILLIERS": [326],
    "GENTILLY": [327],
    "GEORGE V": [329],
    "GIF-S-YVETTE": [330],
    "GLACIERE": [331],
    "GONCOURT": [332],
    "GOUSSAINVILLE": [333],
    "GRAND BOURG": [334],
    "GRAVIGNY BAL T12": [335],
    "GRIGNY CENTRE": [337],
    "GROS NOYER": [339],
    "GROSLAY": [338],
    "GUERARD": [340],
    "GUILLERVAL": [341],
    "GUY MOQUET": [342],
    "HAUSSMANN-SAINT-LAZARE": [343],
    "HAVR.CAUMARTIN": [344],
    "HERBLAY": [346],
    "HERICY": [347],
    "HOCHE": [348],
    "HOTEL DE VILLE": [352],
    "HOUDAN": [356],
    "HOUILLES": [357],
    "IENA": [359],
    "IGNY": [360],
    "INVALIDES": [361, 362],
    "ISLES ARMENTIER": [364],
    "ISSOU PORCHEVIL": [365],
    "ISSY GARE": [366],
    "ISSY VAL SEI": [367],
    "IVRY SUR SEINE": [369],
    "J.BONSERGENT": [370],
    "JASMIN": [372],
    "JAURES": [373],
    "JAVEL": [376, 377],
    "JOINVILLE-LE-P": [378],
    "JOURDAIN": [379],
    "JOUY EN JOSAS": [380],
    "JULES JOFFRIN": [382],
    "JUSSIEU": [383],
    "JUVISY": [385],
    "JUZIERS": [388],
    "KLEBER": [389],
    "LA CHAPELLE": [409],
    "LA COURNEUVE": [412],
    "LA FOURCHE": [416],
    "LA MOTTE-PICQ.": [420],
    "LA MUETTE": [423],
    "LA VARENNE-CH.": [405],
    "LAGNY THORIGNY": [417],
    "LAMARCK-CAUL.": [419],
    "LAPLACE": [403],
    "LARDY": [424],
    "LATOUR-MAUB.": [425],
    "LAUMIERE": [426],
    "LE PARC S.MAUR": [431],
    "LE VESINET-CEN": [438],
    "LE VESINET-L.P": [439],
    "LEDRU-ROLLIN": [441],
    "LES AGNETTES": [1007],
    "LES COURTILLES": [1008],
    "LIEGE": [467],
    "LIEUSAINT-MOISS": [468],
    "LIMAY": [469],
    "LIVRY SUR SEINE": [471],
    "LIZY SUR OURCQ": [472],
    "LOGNES": [473],
    "LONGJUMEAU": [474],
    "LONGUEVILLE": [475],
    "LOUIS BLANC": [476],
    "LOUISE MICHEL": [478],
    "LOURMEL": [479],
    "LOUVECIENNES": [480],
    "LOUVRE": [481],
    "LOUVRES": [482],
    "LOZERE": [483],
    "LUXEMBOURG": [484],
    "LUZARCHES": [485],
    "MABILLON": [486],
    "MADELEINE": [487],
    "MAGENTA": [490],
    "MAIRIE CLICHY": [491],
    "MAIRIE D'ISSY": [495],
    "MAIRIE D'IVRY": [496],
    "MAIRIE D.LILAS": [494],
    "MAIRIE D.MONT": [492],
    "MAIRIE ST-OUEN": [493, 1228],
    "MAIS.ALF-JUIL.": [499],
    "MAIS.ALF-STADE": [500],
    "MAISON BLANCHE": [497],
    "MAISONS ALFORT": [498],
    "MAISONS LAFFITT": [501],
    "MAISSE": [503],
    "MALAK-P.VANVES": [504],
    "MALAK.ET.DOLET": [505],
    "MALESHERBES": [506],
    "MANTES LA JOLIE": [507],
    "MANTES STATION": [508],
    "MARAICHERS": [509],
    "MARCADET-POIS.": [510],
    "MARCEL SEMBAT": [513],
    "MAREIL": [515],
    "MARLES EN BRIE": [516],
    "MARLY LE ROI": [517],
    "MAROLLES": [518],
    "MARX DORMOY": [519],
    "MASSY-PALAIS.": [520],
    "MASSY-VERRIER.": [523],
    "MASSY VERRIERES": [524],
    "MAUBERT-MUTUA.": [525],
    "MAULE": [526],
    "MAURECOURT": [527],
    "MEAUX GARE": [529],
    "MELUN GARE": [530],
    "MENILMONTANT": [533],
    "MENNECY": [534],
    "MERIEL": [536],
    "MERY SUR OISE": [537],
    "MEUDON": [538],
    "MEUDON VAL FLEU": [540],
    "MEULAN": [541],
    "MICHEL BIZOT": [546],
    "MIRABEAU": [547],
    "MIROMESNIL": [548],
    "MITRY CLAYE": [551],
    "MONCEAU": [552],
    "MONTEREAU": [554],
    "MONTGALLET": [555],
    "MONTGERON": [556],
    "MONTGEROULT": [557],
    "MONTIGNY BEAUCH": [558],
    "MONTPARNASSE": [561, 562],
    "MONTREUIL": [566],
    "MONTSOULT": [568],
    "MORMANT": [569],
    "MORTCERF": [570],
    "MOULIN GALANT": [571],
    "MOUROUX": [572],
    "MOUTON-DUVERN.": [573],
    "MUSEE D'ORSAY": [574],
    "N.D.DE-LORETTE": [600],
    "N.D.DES-CHAMPS": [601],
    "NANGIS": [576],
    "NANTERRE UNIVER": [579],
    "NANTERRE-PREF.": [577],
    "NANTERRE-UNIV.": [578],
    "NANTERRE-VILLE": [580],
    "NANTEUIL SAACY": [581],
    "NATION": [582, 583],
    "NATIONALE": [587],
    "NEMOURS ST PIER": [588],
    "NEUILLY-PLAIS.": [589],
    "NEUVILLE UNIVER": [591],
    "NEZEL AULNAY": [592],
    "NOGENT LE PER": [593],
    "NOGENT-S-MARNE": [594],
    "NOINTEL MOURS": [595],
    "NOISIEL": [596],
    "NOISY LE SEC": [599],
    "NOISY-CHAMPS": [597],
    "NOISY-LE-GRAND": [598],
    "OBERKAMPF": [602],
    "ODEON": [604],
    "OLYMPIADES": [1006],
    "OPERA": [606],
    "ORANGIS": [609],
    "ORGERUS": [610],
    "ORLY VILLE": [611],
    "ORSAY-VILLE": [612],
    "OSNY": [613],
    "OURCQ": [614],
    "PALAIS-ROYAL": [618],
    "PALAISEAU": [616],
    "PALAISEAU-VIL.": [617],
    "PANTIN": [620],
    "PARC DE SCEAUX": [622],
    "PARC DES EXPO": [621],
    "PARMENTIER": [625],
    "PASSY": [626],
    "PASTEUR": [628],
    "PELLEPORT": [630],
    "PERE-LACHAISE": [633],
    "PEREIRE": [631],
    "PEREIRE-LEVALLOIS": [632],
    "PERNETY": [636],
    "PERSAN BEAUMONT": [637],
    "PETIT JOUY": [638],
    "PETIT VAUX": [639],
    "PHIL.AUGUSTE": [640],
    "PICPUS": [641],
    "PIERRE CURIE": [642],
    "PIERREFITTE STA": [643],
    "PIERRELAYE": [644],
    "PIGALLE": [646],
    "PLACE CLICHY": [648],
    "PLACE D'ITALIE": [652],
    "PLACE D. FETES": [650],
    "PLACE MONGE": [655],
    "PLAISANCE": [656],
    "PLAISIR GRIGNON": [657],
    "PLAISIR LES CL": [658],
    "POISSONNIERE": [659],
    "POISSY": [660],
    "PONT D.NEUILLY": [669],
    "PONT DE L'ALMA": [664],
    "PONT DE RUNGIS": [670],
    "PONT DE SEVRES": [671],
    "PONT LEVALLOIS": [668],
    "PONT MARIE": [673],
    "PONT PETIT": [678],
    "PONT-NEUF": [674],
    "PONTHIERRY": [672],
    "PONTOISE": [675],
    "PORCHEFONTAINE": [679],
    "PORT-ROYAL": [680],
    "PORTE D'ITALIE": [703],
    "PORTE D'IVRY": [704],
    "PORTE D.CLIGN.": [690],
    "PORTE D.LILAS": [697],
    "PORTE D.VANVES": [700],
    "PORTE D.VERS.": [701],
    "PORTE DAUPHINE": [682],
    "PORTE DOREE": [705],
    "PORTE-DE-CLICHY": [688],
    "PRE-ST-GERVAIS": [709],
    "PRESLES": [710],
    "PROVINS": [711],
    "PTE CHAMPERRET": [685],
    "PTE CHARENTON": [686],
    "PTE D'AUTEUIL": [683],
    "PTE D'ORLEANS": [706],
    "PTE D. VINCENN": [702],
    "PTE D.BAGNOLET": [684],
    "PTE D.CHAPELLE": [691],
    "PTE D.ST-OUEN": [696],
    "PTE D.VILLETTE": [692],
    "PTE DE CHOISY": [687],
    "PTE DE CLICHY": [689],
    "PTE DE PANTIN": [694],
    "PTE MONTREUIL": [693],
    "PTE ST-CLOUD": [695],
    "PUTEAUX": [712],
    "PYRAMIDES": [714],
    "PYRENEES": [716],
    "QUAI D.LA GARE": [717],
    "QUAI.LA RAPEE": [718],
    "QUATRE-SEPTEMB": [719],
    "RAMBOUILLET": [720],
    "RAMBUTEAU": [721],
    "RANELAGH": [722],
    "RASPAIL": [723],
    "REAUMUR-SEB.": [725],
    "RENNES": [728],
    "REPUBLIQUE": [729],
    "REUILLY-DID.": [734],
    "RICHARD LENOIR": [736],
    "RICHELIEU-DR.": [737],
    "RIQUET": [739],
    "RIS ORANGIS": [740],
    "ROBESPIERRE": [741],
    "ROBINSON": [742],
    "ROME": [746],
    "ROSNY BOIS PERR": [747],
    "ROSNY SS BOIS": [748],
    "ROSNY SUR SEINE": [749],
    "RUE D.LA POMPE": [751],
    "RUE DU BAC": [752],
    "RUEIL-MALMAIS.": [753],
    "RUNGIS": [756],
    "SAINT-AMBROISE": [758],
    "SAINT-AUGUSTIN": [759],
    "SAINT-FARGEAU": [764],
    "SAINT-GEORGES": [766],
    "SAINT-JACQUES": [768],
    "SAINT-LAZARE": [769, 822],
    "SAINT-MARCEL": [773],
    "SAINT-MAUR": [774],
    "SAINT-MICHEL": [776, 827],
    "SAINT-MICHEL NOTRE DAME": [828],
    "SAINT-PAUL": [777],
    "SAINT-PLACIDE": [779],
    "SAINT-SULPICE": [781],
    "SANNOIS": [782],
    "SANTEUIL LE PER": [783],
    "SARCELLES": [784],
    "SARTROUVILLE": [785],
    "SAVIGNY LE TEMP": [787],
    "SAVIGNY SUR ORG": [788],
    "SCEAUX": [790],
    "SEGUR": [791],
    "SENTIER": [792],
    "SERMAISE": [793],
    "SEUGY": [794],
    "SEVRAN BEAUDOTT": [795],
    "SEVRAN LIVRY": [796],
    "SEVRES RG": [797],
    "SEVRES VILLE": [801],
    "SEVRES-BABYL.": [798],
    "SEVRES-LECOUR.": [800],
    "SIMPLON": [802],
    "SOLFERINO": [803],
    "SOUPPES CHATEAU": [804],
    "ST CHERON": [811],
    "ST CLOUD": [812],
    "ST CYR": [813],
    "ST DENIS": [815],
    "ST FARGEAU": [819],
    "ST GRATIEN": [821],
    "ST LEU": [823],
    "ST MAMMES": [824],
    "ST MARTIN": [825],
    "ST MICHEL ORGE": [829],
    "ST NOM LA BRETE": [831],
    "ST OUEN": [832],
    "ST OUEN AUMONE": [833],
    "ST OUEN EGLISE": [834],
    "ST QUENTIN YVE": [938],
    "ST-DENIS-BASIL": [761],
    "ST-DENIS-PTE P": [762],
    "ST-DENIS-UNIV.": [763],
    "ST-FRAN.XAVIER": [765],
    "ST-GERM.D.PRES": [767],
    "ST-GERMAIN": [820],
    "ST-MANDE TOUR.": [772],
    "ST-MAUR-CRET.": [826],
    "ST-PH.DU-ROULE": [778],
    "ST-REMY-LES-CH": [839],
    "ST-SEBASTIEN.F": [780],
    "STADE DE FRANCE": [806],
    "STALINGRAD": [808],
    "STE COLOMBE": [817],
    "STE GENEVIEVE": [818],
    "STRAS.ST-DENIS": [836],
    "SUCY-BONNEUIL": [841],
    "SULLY-MORLAND": [842],
    "SURESNES": [843],
    "SURVILLIERS": [845],
    "TACOIGNIERES": [846],
    "TAVERNY": [847],
    "TELEGRAPHE": [848],
    "TEMPLE": [849],
    "TERNES": [850],
    "THIEUX NANTOUIL": [852],
    "THOMERY": [853],
    "THUN  PARADIS": [854],
    "TOLBIAC": [855],
    "TORCY": [856],
    "TRAPPES": [858],
    "TRIEL SUR SEINE": [859],
    "TRILPORT": [860],
    "TRINITE": [861],
    "TROCADERO": [862],
    "TUILERIES": [864],
    "US": [865],
    "VAIRES TORCY": [866],
    "VAL D ARGENT": [867],
    "VAL D.FONTENAY": [869],
    "VALMONDOIS": [870],
    "VANEAU": [871],
    "VANVES MALAKOFF": [872],
    "VARENNE": [873],
    "VAUBOYEN": [874],
    "VAUCELLES": [875],
    "VAUCRESSON": [876],
    "VAUGIRARD": [877],
    "VAUX SUR SEINE": [878],
    "VAVIN": [879],
    "VERNEUIL ETANG": [881],
    "VERNOU SUR SEIN": [882],
    "VERNOUILLET": [883],
    "VERSAILLES CH": [886],
    "VERSAILLES RD": [884],
    "VERSAILLES RG": [885],
    "VERT GALANT": [889],
    "VIARMES": [890],
    "VICTOR HUGO": [892],
    "VIGNEUX": [893],
    "VILLABE": [894],
    "VILLAINES": [895],
    "VILLEJ.L.ARAG.": [897],
    "VILLEJ.L.LAGR.": [896],
    "VILLEJ.P.V.C": [898],
    "VILLENEUVE ROI": [899],
    "VILLENEUVE ST G": [901],
    "VILLENEUVE TRIA": [902],
    "VILLENNES SEINE": [903],
    "VILLEPARISIS": [904],
    "VILLEPINTE": [905],
    "VILLEPREUX": [906],
    "VILLIERS": [907],
    "VILLIERS LE BEL": [909],
    "VILLIERS NEAUPH": [911],
    "VILLIERS SUR M": [912],
    "VINCENNES": [913],
    "VIROFLAY RD": [914],
    "VIROFLAY RG": [915],
    "VIRY CHATILLON": [917],
    "VITRY SUR SEINE": [918],
    "VOLONTAIRES": [919],
    "VOLTAIRE": [920],
    "VOSVES": [921],
    "VULAINES SUR SE": [922],
    "WAGRAM": [923],
    "YERRES": [924],
}

# Inverser le mapping pour les recherches rapides
# Créer un mapping qui accepte TOUS les types possibles (int, str, numpy)
_REVERSE_STATION_MAPPING = {}
for station_name, ids in STATION_MAPPING.items():
    for sid in ids:
        # Ajouter comme entier ET comme string pour couvrir tous les cas
        _REVERSE_STATION_MAPPING[sid] = station_name  # int
        _REVERSE_STATION_MAPPING[str(sid)] = station_name  # string
        try:
            _REVERSE_STATION_MAPPING[int(sid)] = station_name  # force int
        except (ValueError, TypeError):
            pass

def load_station_cache():
    """Charge tout le cache des stations au démarrage"""
    global _STATION_CACHE, _STATION_CACHE_LOADED
    
    if _STATION_CACHE_LOADED:
        return
    
    # D'abord, charger le mapping statique
    _STATION_CACHE.update(_REVERSE_STATION_MAPPING)
    
    try:
        # Authentifier directement
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": LOGIN_USER, "password": LOGIN_PASSWORD},
            timeout=10,
        )
        if resp.ok:
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Charger TOUTES les pages de stations
            page = 1
            while True:
                resp = requests.get(
                    f"{API_URL}/data/stations",
                    headers=headers,
                    params={"page": page, "page_size": 1000},
                    timeout=10,
                )
                if resp.ok:
                    data = resp.json()
                    stations_data = data.get("data", [])
                    
                    if not stations_data:
                        break
                    
                    for station in stations_data:
                        # Essayer plusieurs noms de colonnes possibles
                        station_id = station.get("id_station")
                        station_name = (
                            station.get("nom_station") or 
                            station.get("ArRName") or 
                            station.get("name") or
                            station.get("station_name")
                        )
                        
                        if station_id is not None and station_name:
                            _STATION_CACHE[station_id] = station_name
                    
                    page += 1
                else:
                    break
                    
    except Exception as e:
        pass
    
    _STATION_CACHE_LOADED = True

def get_station_name(station_id):
    """Obtenir le nom d'une station par son ID - SIMPLE ET ROBUSTE"""
    global _STATION_CACHE, _STATION_CACHE_LOADED
    
    # 1. Essayer directement avec la clé reçue (peu importe le type)
    if station_id in _REVERSE_STATION_MAPPING:
        return _REVERSE_STATION_MAPPING[station_id]
    
    # 2. Convertir en int et essayer
    try:
        sid_int = int(station_id)
        if sid_int in _REVERSE_STATION_MAPPING:
            return _REVERSE_STATION_MAPPING[sid_int]
    except (ValueError, TypeError):
        pass
    
    # 3. Convertir en string et essayer
    try:
        sid_str = str(station_id)
        if sid_str in _REVERSE_STATION_MAPPING:
            return _REVERSE_STATION_MAPPING[sid_str]
    except (ValueError, TypeError):
        pass
    
    # 4. Charger le cache si pas déjà fait
    if not _STATION_CACHE_LOADED:
        load_station_cache()
    
    # 5. Chercher dans le cache (tous les formats)
    if station_id in _STATION_CACHE:
        return _STATION_CACHE[station_id]
    try:
        if int(station_id) in _STATION_CACHE:
            return _STATION_CACHE[int(station_id)]
    except (ValueError, TypeError):
        pass
    try:
        if str(station_id) in _STATION_CACHE:
            return _STATION_CACHE[str(station_id)]
    except (ValueError, TypeError):
        pass
    
    # 6. Retour fallback
    return str(station_id)

def clean_dataframe(df, mapping_config):
    """
    Nettoie un dataframe en remplaçant tous les IDs par des noms lisibles
    
    mapping_config = {
        'ligne': map_ligne_code_to_name,
        'jour_type': map_jour_type,
        'id_station': get_station_name,
        'date': lambda x: str(x),
    }
    """
    df_copy = df.copy()
    
    for col, mapper_func in mapping_config.items():
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda x: mapper_func(x) if pd.notna(x) else "N/A")
    
    return df_copy

# =====================================================
# ACCES A L'API
# =====================================================

@st.cache_data(ttl=600)
def get_token():
    """Authentifie auprès de l'API"""
    try:
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": LOGIN_USER, "password": LOGIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        st.error(f"❌ Erreur d'authentification : {e}")
        return None


@st.cache_data(ttl=600)
def fetch_datamart(endpoint, page_size=5000):
    """Récupère les données du datamart"""
    token = get_token()
    if not token:
        return pd.DataFrame()

    headers = {"Authorization": f"Bearer {token}"}
    rows = []
    page = 1

    try:
        while True:
            resp = requests.get(
                f"{API_URL}/datamarts/{endpoint}",
                headers=headers,
                params={"page": page, "page_size": page_size},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("data"):
                break
            
            rows.extend(data["data"])
            page += 1

        df = pd.DataFrame(rows)
        
        # Si données vides ou invalides, utiliser fallback local
        if df.empty or (endpoint == "regularite-lignes" and df["taux_ponctualite"].sum() == 0):
            st.warning(f"⚠️ API retourne des données invalides, chargement depuis CSV local...")
            return load_regularite_local() if endpoint == "regularite-lignes" else pd.DataFrame()
        
        return df
    except Exception as e:
        st.warning(f"⚠️ Chargement API échoué pour {endpoint}, tentative CSV local...")
        # Fallback CSV local
        return load_regularite_local() if endpoint == "regularite-lignes" else pd.DataFrame()


def load_regularite_local():
    """Charger les données de régularité depuis CSV local"""
    import configparser
    import os
    
    try:
        config = configparser.ConfigParser()
        config_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "config", "config.ini")
        )
        config.read(config_path)
        
        ponctualite_csv = config["local"]["ponctualite_csv_path"]
        df = pd.read_csv(ponctualite_csv, delimiter=';')
        
        # Nettoyer les noms de colonnes (supprimer espaces inutiles)
        df.columns = df.columns.str.strip()
        
        # Mapping des colonnes attendues
        column_mapping = {}
        for old_col in df.columns:
            if old_col == 'Date':
                column_mapping[old_col] = 'date'
            elif old_col == 'Ligne':
                column_mapping[old_col] = 'ligne'
            elif old_col == 'Nom de la ligne':
                column_mapping[old_col] = 'nom_ligne'
            elif 'Taux de ponctualité' in old_col:
                column_mapping[old_col] = 'taux_ponctualite'
            elif 'voyageurs' in old_col.lower() or 'retard' in old_col.lower():
                column_mapping[old_col] = 'delai_moyen'
        
        df = df.rename(columns=column_mapping)
        
        # Convertir taux_ponctualite en float (IMPORTANT!)
        if 'taux_ponctualite' in df.columns:
            df['taux_ponctualite'] = pd.to_numeric(
                df['taux_ponctualite'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
        
        # Ajouter rang (ranking)
        if 'date' in df.columns and 'taux_ponctualite' in df.columns:
            df['rang_regularite'] = df.groupby('date')['taux_ponctualite'].rank(method='min', ascending=False)
        
        # Vérification
        print(f"✅ CSV régularité chargé: {len(df)} lignes, mean taux_ponctualite = {df['taux_ponctualite'].mean():.2f}%")
        
        return df
    except Exception as e:
        print(f"❌ Erreur chargement CSV régularité: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


# =====================================================
# INTERFACE PRINCIPALE
# =====================================================

# ✨ Charger le cache des stations au démarrage
load_station_cache()

# Guide d'utilisation
with st.expander("📖 Guide rapide"):
    st.markdown("""
    ### Qu'est-ce que ce dashboard ?
    Analyse des données de fréquentation et régularité du réseau IDFM (Métro + RER).
    
    ### Seuils clés
    - 🔴 **Saturation** : > 7% du trafic quotidien
    - 🟠 **Ponctualité critique** : < 80%
    - 🟢 **Objectif IDFM** : > 95% de ponctualité
    """)

# Sélection du datamart
datamart_choice = st.selectbox(
    "📊 Sélectionnez une analyse :",
    ["frequentation-stations", "regularite-lignes", "evolution-temporelle", "saturation-ml"]
)

# =====================================================
# PAGE 1 : FREQUENTATION
# =====================================================

if datamart_choice == "frequentation-stations":
    st.markdown("### 📈 Fréquentation par Stations/Lignes")
    st.markdown("Quelles stations/lignes sont les plus saturées ?")
    
    df = fetch_datamart("frequentation-stations")
    
    if not df.empty:
        # Seuil de saturation : 7.0% du trafic quotidien (spécification IDFM)
        SATURATION_THRESHOLD = 7.0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Stations", df["id_station"].nunique())
        with col2:
            st.metric("🚇 Lignes", df["ligne"].nunique())
        with col3:
            st.metric("⏰ Créneaux", df["heure"].nunique())
        
        st.markdown(f"""
        **Seuil de saturation** : {SATURATION_THRESHOLD}% du trafic quotidien
        - 🟢 < 3% = Faible
        - 🟠 3-7% = Normal
        - 🔴 > 7% = Saturé
        """)
        
        # Onglets pour les différentes vues
        tab1, tab2, tab3 = st.tabs(["📊 Par Ligne", "🏢 Par Station", "📋 Détail"])
        
        with tab1:
            st.markdown("#### Top 10 Lignes par Fréquentation Moyenne")
            top_lines = df.groupby("ligne")["pourcentage_validations"].mean().nlargest(10).reset_index()
            top_lines = top_lines.sort_values("pourcentage_validations")
            top_lines["ligne_nom"] = top_lines["ligne"].apply(map_ligne_code_to_name)
            
            fig = px.bar(
                top_lines,
                y="ligne_nom",
                x="pourcentage_validations",
                title="Fréquentation Moyenne par Ligne",
                orientation="h",
                color="pourcentage_validations",
                color_continuous_scale="Reds"
            )
            fig.update_layout(yaxis_title="Ligne", xaxis_title="% du Trafic Quotidien")
            fig.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="darkred", annotation_text=f"Seuil: {SATURATION_THRESHOLD}%")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau par ligne et jour
            st.markdown("##### Détail par Ligne et Jour Type")
            line_detail = df.groupby(["ligne", "jour_type"]).agg({
                "pourcentage_validations": ["mean", "max"],
                "id_station": "nunique"
            }).reset_index()
            line_detail.columns = ["Ligne", "Jour", "% Moyen", "% Max", "Stations"]
            line_detail["Ligne"] = line_detail["Ligne"].apply(map_ligne_code_to_name)
            line_detail["Jour"] = line_detail["Jour"].apply(map_jour_type)
            line_detail = line_detail.sort_values("% Moyen", ascending=False)
            st.dataframe(line_detail.head(30), use_container_width=True, hide_index=True)
        
        with tab2:
            st.markdown("#### Top 10 Stations par Fréquentation Moyenne")
            top_stations = df.groupby("id_station")["pourcentage_validations"].mean().nlargest(10).reset_index()
            top_stations = top_stations.sort_values("pourcentage_validations")
            top_stations["station_nom"] = top_stations["id_station"].apply(get_station_name)
            top_stations = top_stations[["station_nom", "pourcentage_validations"]].rename(
                columns={"station_nom": "Station", "pourcentage_validations": "% Trafic"}
            )
            
            fig = px.bar(
                top_stations,
                y="Station",
                x="% Trafic",
                title="Top 10 Stations par Fréquentation",
                orientation="h",
                color="% Trafic",
                color_continuous_scale="Oranges"
            )
            fig.update_layout(yaxis_title="Station", xaxis_title="% du Trafic Quotidien")
            fig.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="darkred", annotation_text=f"Seuil: {SATURATION_THRESHOLD}%")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau stations saturées
            st.markdown("##### Stations les Plus Saturées")
            saturated = df[df["pourcentage_validations"] > SATURATION_THRESHOLD].copy()
            if len(saturated) > 0:
                sat_summary = saturated.groupby("id_station").agg({
                    "pourcentage_validations": ["mean", "max", "count"],
                    "ligne": "first",
                    "jour_type": "first"
                }).reset_index()
                sat_summary.columns = ["Station ID", "% Moyen", "% Max", "Occurrences", "Ligne", "Jour"]
                sat_summary["Station"] = sat_summary["Station ID"].apply(get_station_name)
                sat_summary["Ligne"] = sat_summary["Ligne"].apply(map_ligne_code_to_name)
                sat_summary["Jour"] = sat_summary["Jour"].apply(map_jour_type)
                sat_summary = sat_summary[["Station", "Ligne", "Jour", "% Moyen", "% Max", "Occurrences"]].sort_values("% Max", ascending=False)
                st.dataframe(sat_summary, use_container_width=True, hide_index=True)
            else:
                st.info("✅ Aucune saturation détectée")
        
        with tab3:
            st.markdown("##### Données Détaillées (50 premières lignes)")
            display_df = df[["id_station", "ligne", "heure", "jour_type", "pourcentage_validations"]].head(50).copy()
            display_df["station_nom"] = display_df["id_station"].apply(get_station_name)
            display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df["jour_nom"] = display_df["jour_type"].apply(map_jour_type)
            display_df = display_df[["station_nom", "ligne_nom", "heure", "jour_nom", "pourcentage_validations"]].rename(
                columns={
                    "station_nom": "Station",
                    "ligne_nom": "Ligne",
                    "heure": "Heure",
                    "jour_nom": "Jour Type",
                    "pourcentage_validations": "% Trafic"
                }
            )
            st.dataframe(display_df, use_container_width=True, height=400)

# =====================================================
# PAGE 2 : REGULARITE
# =====================================================

elif datamart_choice == "regularite-lignes":
    st.markdown("### 📋 Régularité et Ponctualité")
    st.markdown("Quelles lignes sont les moins ponctuelles ?")
    
    df = fetch_datamart("regularite-lignes")
    
    if not df.empty:
        OBJECTIF = 95
        CRITIQUE = 80
        
        # Nettoyer les données
        df['taux_ponctualite'] = pd.to_numeric(df['taux_ponctualite'], errors='coerce')
        df = df.dropna(subset=['taux_ponctualite'])
        
        if len(df) > 0:
            avg_ponct = df["taux_ponctualite"].mean()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if avg_ponct >= OBJECTIF:
                    st.success(f"✅ Ponctualité moyenne : **{avg_ponct:.1f}%**")
                elif avg_ponct >= CRITIQUE:
                    st.warning(f"⚠️ Ponctualité moyenne : **{avg_ponct:.1f}%**")
                else:
                    st.error(f"🔴 Ponctualité moyenne : **{avg_ponct:.1f}%**")
            
            with col2:
                nb_lignes = df['ligne'].nunique()
                st.metric("🚇 Lignes", nb_lignes)
            
            with col3:
                nb_dates = df['date'].nunique()
                st.metric("📅 Périodes", nb_dates)
            
            st.markdown(f"""
            ### 📊 Seuils IDFM
            - 🟢 **> {OBJECTIF}%** = Excellent ✓
            - 🟠 **{CRITIQUE}-{OBJECTIF}%** = À surveiller
            - 🔴 **< {CRITIQUE}%** = Critique 🚨
            """)
            
            # Graphique par ligne avec noms
            line_avg = df.groupby("ligne")["taux_ponctualite"].mean().sort_values().reset_index()
            line_avg["ligne_nom"] = line_avg["ligne"].apply(map_ligne_code_to_name)
            
            if len(line_avg) > 0:
                # Colorier selon les seuils
                def get_color(val):
                    if val >= OBJECTIF:
                        return "#2ecc71"  # Vert
                    elif val >= CRITIQUE:
                        return "#f39c12"  # Orange
                    else:
                        return "#e74c3c"  # Rouge
                
                line_avg["color"] = line_avg["taux_ponctualite"].apply(get_color)
                
                fig = px.bar(
                    line_avg,
                    y="ligne_nom",
                    x="taux_ponctualite",
                    title="📊 Ponctualité par Ligne (Vert=Bon, Orange=À surveiller, Rouge=Critique)",
                    orientation="h",
                    color="color",
                    color_discrete_map={v: v for v in line_avg["color"].unique()}
                )
                fig.update_layout(yaxis_title="Ligne", xaxis_title="Ponctualité (%)")
                fig.add_vline(x=OBJECTIF, line_dash="dash", line_color="darkgreen", 
                             annotation_text=f"Objectif ({OBJECTIF}%)")
                st.plotly_chart(fig, use_container_width=True)
            
            # Tableau détaillé sans codes
            st.markdown("#### 📋 Détails par Ligne")
            display_df = df[["ligne", "nom_ligne", "taux_ponctualite", "date"]].copy()
            display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df = display_df[["ligne_nom", "nom_ligne", "taux_ponctualite", "date"]]
            display_df.columns = ["Ligne", "Nom Complet", "Ponctualité (%)", "Période"]
            display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
            display_df = display_df.sort_values("Ponctualité (%)", ascending=True)
            
            st.dataframe(display_df.drop_duplicates(subset=["Ligne"]), use_container_width=True, hide_index=True)
            st.caption(f"Affichage : {len(display_df)} enregistrements")
        else:
            st.warning("⚠️ Aucune donnée valide de régularité")
    else:
        st.error("❌ Impossible de charger les données de régularité")

# =====================================================
# PAGE 3 : EVOLUTION
# =====================================================

elif datamart_choice == "evolution-temporelle":
    st.markdown("### 📈 Évolution Temporelle")
    st.markdown("Comment évolue la fréquentation selon le jour-type ?")
    
    df = fetch_datamart("evolution-temporelle")
    
    if not df.empty:
        # Aggréger par jour-type
        df_by_jour = df.groupby("date").agg({
            "frequentation_cumulee": "sum",
            "nb_stations": "mean",
            "variation_semaine_precedente": "first"
        }).reset_index()
        
        df_by_jour["jour_nom"] = df_by_jour["date"].apply(map_jour_type)
        
        # Métriques générales
        col1, col2, col3 = st.columns(3)
        with col1:
            total_freq = df_by_jour["frequentation_cumulee"].sum()
            st.metric("📊 Fréquentation Totale", f"{total_freq:,.0f}")
        with col2:
            nb_jours = df_by_jour.shape[0]
            st.metric("📅 Jours Type", f"{nb_jours}")
        with col3:
            avg_variation = df_by_jour["variation_semaine_precedente"].mean()
            st.metric("📈 Variation Moyenne", f"{avg_variation:+.1f}%")
        
        # Graphique par jour-type
        fig = px.bar(
            df_by_jour.sort_values("frequentation_cumulee", ascending=True),
            y="jour_nom",
            x="frequentation_cumulee",
            title="Fréquentation Cumulée par Jour-Type",
            orientation="h",
            color="frequentation_cumulee",
            color_continuous_scale="Blues"
        )
        fig.update_layout(xaxis_title="Fréquentation Cumulée", yaxis_title="Jour Type")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé par ligne et jour-type
        st.markdown("#### 📋 Détail par Ligne et Jour-Type")
        display_df = df[["date", "ligne", "frequentation_cumulee", "nb_stations"]].copy()
        display_df["jour_nom"] = display_df["date"].apply(map_jour_type)
        display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
        display_df = display_df[["jour_nom", "ligne_nom", "frequentation_cumulee", "nb_stations"]]
        display_df.columns = ["Jour Type", "Ligne", "Fréquentation", "Stations"]
        display_df = display_df.sort_values(["Jour Type", "Fréquentation"], ascending=[True, False])
        st.dataframe(display_df, use_container_width=True, height=400)

# =====================================================
# PAGE 4 : SATURATION ML
# =====================================================

elif datamart_choice == "saturation-ml":
    st.markdown("### 🤖 Dataset Saturation (ML)")
    st.markdown("Analyse des pics de saturation et prédiction d'IA")
    
    df = fetch_datamart("saturation-ml")
    
    if not df.empty:
        # Recalculer est_saturation basé sur le seuil IDFM de 7.0%
        SATURATION_THRESHOLD_ML = 7.0
        df["est_saturation_nouveau"] = (df["pourcentage_validations"] > SATURATION_THRESHOLD_ML).astype(int)
        
        sat_count = (df["est_saturation_nouveau"] == 1).sum()
        total = len(df)
        sat_pct = sat_count / total * 100 if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Situations Saturées", f"{sat_count:,}")
        with col2:
            st.metric("📊 Total Observations", f"{total:,}")
        with col3:
            st.metric("📈 % Saturation", f"{sat_pct:.1f}%")
        
        # Onglets
        tab1, tab2, tab3 = st.tabs(["📊 Distribution", "⚠️ Saturées", "📋 Détail"])
        
        with tab1:
            # Pie chart
            labels = ["Normal", "Saturé"]
            values = [total - sat_count, sat_count]
            fig = px.pie(
                names=labels,
                values=values,
                title="Distribution Saturation",
                color_discrete_map={"Normal": "#2ecc71", "Saturé": "#e74c3c"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Saturation par ligne
            st.markdown("##### Saturation par Ligne")
            line_sat = df[df["est_saturation_nouveau"] == 1].groupby("ligne").size().reset_index(name="Saturations")
            line_sat["Ligne"] = line_sat["ligne"].apply(map_ligne_code_to_name)
            line_sat = line_sat[["Ligne", "Saturations"]].sort_values("Saturations", ascending=True)
            
            fig = px.bar(
                line_sat,
                y="Ligne",
                x="Saturations",
                title="Nombre de Saturations par Ligne",
                orientation="h",
                color="Saturations",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown("##### Pics de Saturation")
            saturated_df = df[df["est_saturation_nouveau"] == 1].copy()
            
            if len(saturated_df) > 0:
                saturated_df["Ligne"] = saturated_df["ligne"].apply(map_ligne_code_to_name)
                saturated_df["Jour"] = saturated_df["jour_type"].apply(map_jour_type)
                display_sat = saturated_df[["Ligne", "heure", "Jour", "pourcentage_validations", "taux_ponctualite"]].head(100)
                display_sat.columns = ["Ligne", "Heure", "Jour Type", "% Trafic", "Ponctualité (%)"]
                display_sat["Ponctualité (%)"] = display_sat["Ponctualité (%)"].round(1)
                display_sat["% Trafic"] = display_sat["% Trafic"].round(2)
                display_sat = display_sat.sort_values("% Trafic", ascending=False)
                st.dataframe(display_sat, use_container_width=True, height=400, hide_index=True)
                st.caption(f"Affichage : {min(100, len(saturated_df))} pics de saturation (> 7% du trafic)")
            else:
                st.info("✅ Aucune saturation détectée")
        
        with tab3:
            st.markdown("##### Toutes les Données ML (100 premières)")
            display_df = df[["ligne", "heure", "jour_type", "pourcentage_validations", "taux_ponctualite", "est_saturation_nouveau"]].head(100).copy()
            display_df["Ligne"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df["Jour"] = display_df["jour_type"].apply(map_jour_type)
            display_df["Saturé"] = display_df["est_saturation_nouveau"].map({0: "🟢 Non", 1: "🔴 Oui"})
            display_df = display_df[["Ligne", "heure", "Jour", "pourcentage_validations", "taux_ponctualite", "Saturé"]]
            display_df.columns = ["Ligne", "Heure", "Jour Type", "% Trafic", "Ponctualité (%)", "Saturé"]
            display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
            display_df["% Trafic"] = display_df["% Trafic"].round(2)
            st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
📊 Dashboard IDFM — Source : Île-de-France Mobilités
</div>
""", unsafe_allow_html=True)
