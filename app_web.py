import streamlit as st
import pandas as pd
import time
import requests
import re
import os
from streamlit_gsheets import GSheetsConnection


# 1. CONFIGURATION UNIQUE DE LA PAGE (DOIT ÊTRE LA PREMIÈRE LIGNE)
st.set_page_config(
    page_title="Acheter Québécois & Canadien",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)


code_upc = "code_upc"
# Injection CSS pour l'interface et le masquage des éléments natifs
st.html("""
<style>
    #MainMenu, footer { visibility: hidden !important; display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    
    [data-testid="stHeaderActionElements"], .stAppDeployButton { 
        display: none !important; 
        visibility: hidden !important;
        width: 0px !important;
        height: 0px !important;
    }
    
    .stViewerBadge, .stGitHubIcon, a[href*="github.com"], button[title*="GitHub"] { 
        display: none !important; 
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0px !important;
    }
    
    header div:nth-child(2) { display: none !important; }
    header { background-color: transparent !important; }
    [data-testid="stSidebarCollapseButton"], [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    
    .stTextInput label p { font-size: 24px !important; font-weight: bold !important; color: #003366 !important; }
    .stTextInput input { font-size: 26px !important; padding: 15px !important; height: 65px !important; font-weight: bold !important; letter-spacing: 2px !important; }
""")
def classifier_produit_exact(nom_produit):
    """Analyse le nom du produit et retourne (Categorie, Sous_Categorie)."""
    nom = str(nom_produit).lower().strip()
    
    # =========================================================================
    # 1. PRODUITS FRAIS ET PÉRISSABLES
    # =========================================================================
    if any(m in nom for m in ["lait de", "lait homogénéisé", "lait 1%", "lait 2%", "lait 0%", "crème à cuisson", "crème à café", "creme 15%", "creme 35%", "ultra'crème", "québon", "sealtest", "lactantia", "nutrilait"]):
        if not any(x in nom for x in ["chocolat", "chocolate", "amande", "soya", "avoine", "coco", "bacon"]):
            return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["fromage", "cheddar", "mozzarella", "mozzarellissima", "parmesan", "feta", "ricotta", "mascarpone", "gouda", "swiss", "suisse", "havarti", "bocconcini", "cheestrings", "ficello", "la vache qui rit", "philadelphia", "cottage", "le cendrillion", "oka", "mizithra", "paneer", "st agur", "grana padano"]):
        return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["yogourt", "yogurt", "yaourt", "skyr", "oikos", "activia", "iogo", "yop", "danone", "danino", "pouding", "pudding", "kefir", "kéfir", "danette"]):
        return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["œuf", "oeuf", "oeufs", "blancs d'oeuf", "créations oeufs", "naturoeuf", "nutri"]):
        return "1. Produits frais et périssables", "Produits laitiers et Œufs"
    if any(m in nom for m in ["beurre", "butter", "margarine", "becel", "crystal margarine", "imperial"]):
        return "1. Produits frais et périssables", "Beurre et margarines"
    if any(m in nom for m in ["poulet", "chicken", "dinde", "turkey", "dindon", "volaille", "poitrine", "cuisse", "ailes", "nuggets", "souvlakis", "bovril aux poulet"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["bœuf", "boeuf", "porc", "veau", "agneau", "haché", "steak", "rôti", "roti", "bifteck", "grillade", "meatballs", "bovril boeuf", "longe de porc"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["jambon", "bacon", "saucisse", "saucisson", "charcuterie", "pepperoni", "salami", "bologne", "baloney", "cretons", "pancetta", "rosette de lyon"]):
        return "1. Produits frais et périssables", "Viandes et Volailles"
    if any(m in nom for m in ["crevette", "shrimp", "pétoncle", "moule", "homard", "lobster", "calmar", "calamari", "fruits de mer", "palourdes"]):
        return "1. Produits frais et périssables", "Poissons et Fruits de mer"
    if any(m in nom for m in ["saumon", "salmon", "truite", "morue", "cod ", "aiglefin", "hadock", "sole ", "thon", "tuna", "sardine", "maquereau", "anchois", "poisson", "flétan"]):
        return "1. Produits frais et périssables", "Poissons et Fruits de mer"
    if any(m in nom for m in ["fraise", "strawberry", "bleuet", "blueberry", "framboise", "raspberry", "mûre", "blackberry", "pomme", "apple", "poire", "pear", "orange", "citron", "lemon", "lime", "banane", "banana", "ananas", "pineapple", "mangue", "mango", "pamplemousse", "grapefruit", "kiwi", "cantaloup", "clémentine", "clementine"]):
        return "1. Produits frais et périssables", "Fruits et Légumes"
    if any(m in nom for m in ["carotte", "carrot", "céleri", "celery", "laitue", "lettuce", "salade", "salad", "épinard", "spinach", "chou ", "cabbage", "tomate", "tomato", "oignon", "onion", "ail ", "garlic", "avocat", "avocado", "poivron", "pepper", "jalapeño", "jalapeno", "champignon", "mushroom", "patate", "potato", "frite", "poireau", "leek", "brocoli", "broccoli", "fine herbe", "radis", "thyme", "persil", "échalotes"]):
        return "1. Produits frais et périssables", "Fruits et Légumes"
    # =========================================================================
    # 2. ÉPICERIE SÈCHE (LES ALLÉES CENTRALES)
    # =========================================================================
    if any(m in nom for m in ["pain", "bread", "loaf", "superclub pom", "miche"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["tortilla", "pita", "naan", "wraps", "wrap ", "flatbread"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["bagel", "muffin", "croissant", "brioche", "briochettes", "chocolatine", "english muffins", "crumpets"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["gâteau", "gateau", "cake", "tarte", "pie ", "pâtisserie", "patisserie", "vol au vent", "chausson", "madeleines", "strudel"]):
        return "2. Épicerie sèche (Les allées centrales)", "Boulangerie et Pâtisserie"
    if any(m in nom for m in ["riz ", "rice", "pâtes", "pates", "pasta", "spaghetti", "macaroni", "fusilli", "penne", "linguine", "nouille", "noodle", "ramen", "vermicelle", "quinoa", "couscous", "orzo"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["huile", "oil ", "vinaigre", "vinegar", "moutarde", "mustard", "ketchup", "mayonnaise", "mayo ", "relish", "pesto", "salsa", "sauce", "vinaigrette", "dressing", "tahini"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["conserve", "soupe", "soup", "bouillon", "broth", "bovril", "fèves", "feves", "beans", "lentille", "lentil", "pois ", "peas", "pois chiche", "chickpeas", "haricot", "artichaut", "olives", "clark", "aylmer", "unico", "bush's", "campbell", "habitant"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["farine", "flour", "sucre", "sugar", "cassonade", "poudre à pâte", "poudre a pate", "bicarbonate", "levure", "fecule", "fécule", "cocoa", "cacao", "baking", "maizena", "truvia", "splenda", "gelatine", "gélatine", "glaçage", "frosting"]):
        return "2. Épicerie sèche (Les allées centrales)", "Épicerie salée et Garde-manger"
    if any(m in nom for m in ["céréale", "cereal", "cheerios", "flakes", "krispies", "shreddies", "oatmeal", "gruau", "granola", "froot loops", "corn pops", "frosted flakes"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["miel", "honey", "sirop", "syrup", "érable", "maple", "tartinade", "nutella", "spread", "confiture", "jam "]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["chips", "croustille", "crisps", "pringles", "ruffles", "doritos", "cheetos", "takis", "popcorn", "maïs soufflé", "bretzel", "pretzel", "craquelin", "cracker", "crispers", "hickory sticks", "vinta"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["barre tendre", "barre granola", "granola bar", "clif", "kind bar", "chewy", "m&m", "mars", "snickers", "kitkat", "twix", "skittles", "turtles", "smarties", "lindor", "lindt", "bonbon", "candy", "friandise", "oreo", "pattes d'ours", "bear paws", "célébration", "kinder"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"
    if any(m in nom for m in ["noix", "nuts", "amande", "almond", "cacahuète", "peanut", "arachide", "cashew", "cajou", "pistache", "pistachios", "walnuts", "graine", "seeds"]):
        return "2. Épicerie sèche (Les allées centrales)", "Déjeuner et Collations"

    # =========================================================================
    # 3. SURGELÉS ET BOISSONS
    # =========================================================================
    if any(m in nom for m in ["surgelé", "congelé", "frozen", "pizza", "lasagne", "lasaña", "wonton", "dumpling", "gyoza", "egg roll", "pâté impérial", "pogo", "perogies", "ravioli", "tortellini", "gnocchi", "delissio", "giuseppe"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["pané", "panes", "janes", "pépites", "nuggets", "strips", "burgers", "wings", "ailes de poulet", "flamingo", "mères michel", "pinty's"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["frites", "fries", "mélange de légumes", "mélange de petits fruits", "bleuets sauvages boréals", "mccain", "lamb weston"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["glace", "sorbet", "creme glacee", "crème glacée", "ice cream", "magnum", "drumstick", "haagen", "chapman", "coolway", "parlour", "melona", "revello"]):
        return "3. Surgelés et Boissons", "Aliments surgelés"
    if any(m in nom for m in ["coke", "pepsi", "7up", "soda", "gazeuse", "eaux pétillantes", "pétillante", "bubly", "perrier", "fresca", "crush orange", "dr pepper", "sprite", "eska", "dasani", "montellier", "aquafina", "zevia"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["jus ", "jus de", "nectar", "limonade", "tropicana", "fruit punch", "punch aux fruits", "snapple", "oasis", "fruitsations", "pure leaf", "nestea", "apple juice", "orange juice", "ocean spray", "sunrype", "v8"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["café", "cafe ", "cappuccino", "thé ", "the ", "tisane", "infusion", "van houtte", "tim hortons", "maxwell house", "starbucks", "twinings", "mccafé", "nabob", "tassimo"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["lait d'amande", "lait de soya", "lait d'avoine", "boisson végétale", "silk", "so nice", "sofresh", "milked oats"]):
        return "3. Surgelés et Boissons", "Boissons (non alcoolisées)"
    if any(m in nom for m in ["beer", "bière", "biere", "microbrasserie", "st-ambroise", "coors", "lager", "sleeman", "bud light", "budweiser", "heineken", "madjack", "vin ", "vins", "bordeaux", "sauvignon", "shiraz", "barefoot", "cidre"]):
        return "3. Surgelés et Boissons", "Bières et Vins (Alcools)"

    # =========================================================================
    # 4. CATÉGORIES SPÉCIALISÉES
    # =========================================================================
    if "sushi" in nom or "california roll" in nom:
        return "4. Catégories spécialisées", "Prêt-à-manger / Traiteur"
    if any(m in nom for m in ["sandwich", "wrap ", "salade préparée", "salade de poulet", "salade de jambon", "salade de chou", "coleslaw", "poulet rôti chaud", "poulet cuit et chaud"]):
        return "4. Catégories spécialisées", "Prêt-à-manger / Traiteur"
    if "biologique" in nom or "bio " in nom or "organic" in nom:
        return "4. Catégories spécialisées", "Alimentation saine et produits naturels"

    return "Épicerie générale", "Non classifié"


# Structure de correspondance pour lier vos deux listes déroulantes de gauche
CORRESPONDANCE_SOUS_CATEGORIES = {
    "Tous": ["Toutes"],
    "1. Produits frais et périssables": [
        "Toutes",
        "Fruits et Légumes",
        "Viandes et Volailles",
        "Poissons et Fruits de mer",
        "Produits laitiers et Œufs"
    ],
    "2. Épicerie sèche (Les allées centrales)": [
        "Toutes",
        "Boulangerie et Pâtisserie",
        "Épicerie salée et Garde-manger",
        "Déjeuner et Collations"
    ],
    "3. Surgelés et Boissons": [
        "Toutes",
        "Aliments surgelés",
        "Boissons (non alcoolisées)",
        "Bières et Vins (Alcools)"
    ],
    "4. Catégories spécialisées": [
        "Toutes",
        "Prêt-à-manger / Traiteur",
        "Alimentation saine et produits naturels"
    ]
}
def charger_donnees():
    """Se connecte automatiquement au Google Sheet, harmonise le pays Québec et nettoie les régions et entreprises."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_initial = conn.read(worksheet="Sheet1", ttl="2m")
        if df_initial is None or df_initial.empty:
            st.error("⚠️ Le fichier Google Sheet lu est vide. Vérifiez l'onglet 'Sheet1'.")
            return pd.DataFrame()

        df_initial = df_initial.astype(str)
        df_initial.columns = [c.strip().lower() for c in df_initial.columns]
        
        if 'code_upc' in df_initial.columns:
            df_initial['code_upc'] = df_initial['code_upc'].replace(r'\.0$', '', regex=True).str.strip()
        else:
            df_initial['code_upc'] = ""
        
        # Gestion stricte des colonnes de prix pour éliminer les faux prix à 0$
        colonnes_prix = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c', 'prix_walmart', 'prix_tiger_giant', 'prix_dollarama', 'prix_provigo']
        for col_prix in colonnes_prix:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].fillna("").astype(str).str.strip().replace(["nan", "0", "0.0", "0,00"], "")
            
        if 'distribution' not in df_initial.columns and 'reseau_distribution' in df_initial.columns:
            df_initial['distribution'] = df_initial['reseau_distribution']
        elif 'distribution' not in df_initial.columns:
            df_initial['distribution'] = ""
            
        df_initial['distribution'] = df_initial['distribution'].replace('nan', '').str.strip() 

        # ==============================================================================
        # 🚀 HARMONISATION ET NETTOYAGE STRICT DES RÉGIONS
        # ==============================================================================
        if 'entreprise_province_etat' in df_initial.columns and 'entreprise_pays' in df_initial.columns:
            # Nettoyage des variantes de "Québec"
            mask_quebec = df_initial['entreprise_province_etat'].str.lower().str.contains('québec|quebec', na=False)
            df_initial.loc[mask_quebec, 'entreprise_province_etat'] = 'Québec'
            
            # Harmonisation de la nationalité économique québécoise
            df_initial.loc[mask_quebec, 'entreprise_pays'] = 'Québec'

        # ==============================================================================
        # 🚀 NETTOYAGE CHIRURGICAL DES NOMS D'ENTREPRISES (COLONNE F)
        # ==============================================================================
        if 'entreprise_proprietaire' in df_initial.columns:
            def epurer_nom_entreprise(nom):
                if pd.isna(nom) or str(nom).lower() in ['nan', 'none', '']:
                    return ""
                
                # 1. On coupe dès qu'il y a une virgule pour rejeter les adresses/villes
                nom_propre = str(nom).split(',')[0]
                
                # 2. Suppression des suffixes légaux (Insensible à la casse, gère avec ou sans point)
                # Supprime: inc, inc., limitée, limitee, ltd, ltd., company, cie
                motifs_suffixes = r'\b(inc\b\.?|limitée\b|limitee\b|ltd\b\.?|company\b|cie\b\.?)'
                nom_propre = re.sub(motifs_suffixes, '', nom_propre, flags=re.IGNORECASE)
                
                # 3. Nettoyage des espaces doubles ou en fin de chaîne
                return nom_propre.strip()

            df_initial['entreprise_proprietaire'] = df_initial['entreprise_proprietaire'].apply(epurer_nom_entreprise)

        df_initial['categorie'] = df_initial['nom'].apply(deviner_categorie)       
        return df_initial
    except Exception as e:
        st.error(f"❌ Erreur de lecture : {e}")
        return pd.DataFrame()




def sauvegarder_donnees(df_a_enregistrer):
    """Enregistre les prix automatiquement grâce aux secrets de Streamlit Cloud."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet="Sheet1", data=df_a_enregistrer)
        st.cache_data.clear()
        if 'df_produits' in st.session_state:
            del st.session_state['df_produits']
        return True
    except Exception as e:
        st.error(f"❌ Erreur de sauvegarde réelle : {e}")
        return False

def sauvegarder_historique(df_nouvel_historique):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            df_existant = conn.read(worksheet="Historique_Prix")
        except Exception:
            df_existant = pd.DataFrame()
        if not df_existant.empty:
            df_total = pd.concat([df_existant, df_nouvel_historique], ignore_index=True)
        else:
            df_total = df_nouvel_historique
        conn.update(worksheet="Historique_Prix", data=df_total)
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde de l'historique : {e}")
        return False
def verifier_boisson_pure(nom, mots_produit):
    """Filtre de liste blanche exclusive pour isoler uniquement les boissons."""
    mots_autorises_boissons = {
        "coke", "diet", "diète", "café", "cafe", "moulu", "eau", "source", "naturelle", "gazeuse", 
        "gazéifiée", "gazeifiee", "pétillante", "petillante", "thé", "the", "glacé", "glace", "glacée", 
        "glacee", "pepsi", "mini", "7up", "soda", "boisson", "boissons", "drink", "drinks", "sport", 
        "énergisante", "energisante", "energy", "juice", "jus", "concentré", "concentre", "pur", "pure", 
        "bubly", "nestea", "crush", "punch", "tea", "soya", "soja", "bien", "etre", "être", 
        "liqueur", "sodas", "cola", "zevia", "zero", "zéro", "sucre", "sugar", "schweppes", 
        "tonique", "limonade", "lemonade", "kombucha", "smoothie", "nectar", "infusion", "tisane", 
        "bière", "beer", "ale", "ipa", "lager", "vin", "vodka", "water", "redbull", "red", "bull", 
        "cidre", "boost", "ensure", "brisk", "fruitopia", "snapple", "dasani", "eska", "fiji", 
        "perrier", "montellier", "evian", "aquafina", "oat", "tropicana", "oasis", "rougemont", 
        "irrésistible", "selection", "sélection", "natura", "v8", "mélange", "van", "houtte", 
        "framboise", "régulier", "tim", "hortons", "amandes", "amande", "cerise", "pomme", "raisin", 
        "mangue", "orange", "citron", "tropical", "fruits", "fruit", "baies", "soy", "noisette", 
        "decafféiné", "instantané", "lime", "pamplemousse", "gingembre", "goyave", "cassis", "matcha", 
        "caramel", "chocolat", "vanille", "original", "enrichi", "naturel", "sucré", "sans", "liquide", 
        "fraise", "calcium", "vitamine", "probiotique", "2l", "50cl", "946", "ml", "cans", "de", "du", "et", "pour"
    }
    if all(m in mots_autorises_boissons for m in mots_produit):
        mots_declencheurs = {"coke", "café", "cafe", "eau", "thé", "the", "pepsi", "7up", "soda", "boisson", "drink", "juice", "jus", "bubly", "nestea", "crush", "tea", "soya", "soja", "liqueur", "cola", "zevia", "smoothie", "nectar", "infusion", "tisane", "bière", "beer", "vin", "moût", "mout", "cidre", "limonade", "kombucha"}
        if any(m in mots_declencheurs for m in mots_produit):
            return True
    return False

def verifier_maraicher_pur(nom, mots_produit):
    """Filtre de liste blanche exclusive pour isoler uniquement le rayon maraîcher frais."""
    mots_autorises_maraichers = {
        "abricot", "ananas", "apple", "apples", "banane", "bananes", "banana", "bananas", 
        "bleuet", "bleuets", "cerise", "citron", "citrons", "clementine", "clémentine", 
        "fraise", "fraises", "framboise", "fruit", "fruits", "grapefruit", "kiwi", "lime", 
        "mandarine", "melon", "mûre", "orange", "oranges", "pamplemousse", "cantaloup", 
        "pasteque", "pastèque", "pêche", "peche", "poire", "pomme", "pommes", "prune", "raisin", 
        "ail", "arugula", "asperge", "avocat", "basilic", "betterave", "brocoli", "carotte", 
        "celeri", "céleri", "champignon", "chou", "concombre", "coriandre", "courge", "echalote", 
        "epinard", "épinard", "spinach", "gingembre", "verts", "laitue", "romaine", "mais", "maïs", 
        "navet", "oignon", "oignons", "panais", "patate", "persil", "piment", "poireau", "leek", 
        "radis", "tomate", "tomates", "zucchini", "frais", "fraîche", "organic", "biologique", "bio", 
        "local", "vrac", "quebec", "québec", "canada", "sac", "panier", "paquet", "botte", "gros", 
        "tranche", "tranché", "rapee", "râpée", "coupé", "blanche", "jaune", "rouge", "vert", "verte", 
        "un", "une", "le", "la", "les", "de", "du", "en", "et", "à", "avec", "sans", "1l", "3lb", "4lb"
    }
    if all(m in mots_autorises_maraichers for m in mots_produit):
        mots_bruts_vegetaux = {"abricot", "ananas", "apple", "banane", "banana", "bleuet", "cerise", "citron", "clementine", "fraise", "framboise", "fruit", "fruits", "kiwi", "lime", "mandarine", "melon", "mûre", "orange", "pamplemousse", "cantaloup", "pasteque", "pêche", "peche", "poire", "pomme", "prune", "raisin", "ail", "arugula", "asperge", "avocat", "basilic", "betterave", "brocoli", "carotte", "celeri", "champignon", "chou", "concombre", "coriandre", "courge", "epinard", "spinach", "échalote", "gingembre", "laitue", "romaine", "mais", "navet", "oignon", "panais", "patate", "persil", "piment", "poireau", "radis", "tomate", "zucchini", "salade"}
        if any(m in mots_bruts_vegetaux for m in mots_produit):
            if "haricots" in nom and "verts" not in nom:
                return False
            return True
    return False
def verifier_surgele_pur(nom, mots_produit):
    """Filtre de liste blanche exclusive pour isoler uniquement le rayon surgelé brut."""
    mots_autorises_surgeles = {
        "pizza", "pizzas", "frites", "frite", "surgelé", "surgelés", "surgelée", "surgelées", 
        "congelé", "congelée", "pépites", "bouchées", "croquettes", "lanières", "boulettes", "poitrines", 
        "ailes", "gaufres", "tourtière", "poulet", "chicken", "saucisse", "pepperoni", "bacon", 
        "viande", "mozzarella", "cheese", "fromage", "champignons", "épinards", "tomates", "ail", 
        "garnie", "deluxe", "spécial", "trois", "3", "2", "x", "mince", "thin", "crispy", "croustillante", 
        "style", "nature", "farcies", "ristorante", "giuseppe", "pizzeria", "delissio", "pinty", 
        "flamingo", "cavendish", "mc", "les", "de", "du", "d", "en", "et", "à", "au", "la", "le", "un", "pour"
    }
    if all(m in mots_autorises_surgeles for m in mots_produit):
        mots_declencheurs = {"pizza", "pizzas", "frites", "frite", "surgelé", "surgelés", "surgelée", "congelé", "pépites", "bouchées", "croquettes", "gaufres", "tourtière"}
        if any(m in mots_declencheurs for m in mots_produit):
            return True
    return False

def verifier_laitier_pur(nom, mots_produit):
    """Filtre de liste blanche exclusive pour isoler uniquement le rayon laitiers et oeufs frais."""
    mots_autorises_laitiers = {
        "yogourt", "yaourt", "yogurt", "skyr", "oikos", "activia", "danone", "iogo", "yoplait", 
        "liberté", "kēfir", "kéfir", "lait", "laitier", "fromage", "fromages", "cheese", "boursin", 
        "philadelphia", "ricotta", "feta", "fêta", "gouda", "havarti", "cheddar", "mozzarella", 
        "parmesan", "camembert", "brie", "oka", "allégro", "beurre", "oeufs", "œufs", "oeuf", "œuf", 
        "blancs", "crème", "creme", "sour", "cream", "quebon", "québon", "natrel", "lactantia", 
        "purfiltre", "riviera", "burnbrae", "silk", "agropur", "armstrong", "président", "quebec", 
        "québec", "canada", "margarine", "fraise", "vanille", "vanilla", "citron", "pêche", "peche", 
        "bleuet", "nature", "sucré", "grec", "greek", "brassé", "crémeux", "tranche", "tranché", 
        "râpé", "râpée", "grain", "bloc", "brique", "0%", "1%", "2%", "35%", "12", "1l", "2l", "454g", 
        "ml", "sans", "lactose", "matières", "grasses", "écrémé", "filtré", "ultra", "pur", "vache", "chèvre", 
        "de", "du", "en", "et", "à", "au", "aux", "la", "le", "les", "un", "une", "pour", "avec"
    }
    if all(m in mots_autorises_laitiers for m in mots_produit):
        mots_declencheurs = {"yogourt", "yaourt", "yogurt", "skyr", "oikos", "activia", "danone", "iogo", "yoplait", "liberté", "kēfir", "lait", "fromage", "cheese", "boursin", "philadelphia", "ricotta", "feta", "gouda", "havarti", "cheddar", "mozzarella", "parmesan", "beurre", "oeufs", "œufs", "oeuf", "crème", "margarine"}
        if any(m in mots_declencheurs for m in mots_produit):
            if any(m in nom for m in ["barres", "biscuit", "biscuits", "chocolat", "chips", "croustilles", "popcorn", "soup", "soupe", "pizza", "oreo"]):
                return False
            return True
    return False

def verifier_boulangerie_pure(nom, mots_produit):
    """Filtre de liste blanche exclusive pour isoler uniquement la boulangerie et pâtisserie."""
    mots_autorises_boulangerie = {
        "céréales", "cereales", "pain", "pains", "bread", "loaf", "baguette", "croissant", "croissants", 
        "muffin", "muffins", "brioche", "brioches", "buns", "bagel", "bagels", "naan", "pita", "tortilla", 
        "wraps", "gruau", "avoine", "oat", "flocons", "flakes", "shreddies", "krispies", "pops", "cheerios", 
        "granola", "farine", "flour", "levure", "biscuit", "biscuits", "cookie", "cookies", "galette", 
        "tarte", "gâteau", "gateau", "brownie", "whippet", "biscotte", "chapelure", "chocolat", "chocolate", 
        "pépites", "chips", "sucre", "cassonade", "miel", "honey", "érable", "vanille", "caramel", "raisin", 
        "bleuet", "pomme", "amandes", "sésame", "blé", "ble", "wheat", "épeautre", "seigle", "sarrasin", 
        "margarine", "beurre", "crème", "cannelle", "italien", "artisan", "kellogg", "quaker", "dare", 
        "oreo", "wonder", "pom", "dempster", "leclerc", "celebration", "première", "moisson", "moelleux", 
        "tendres", "tranché", "tranches", "épais", "mini", "bouchées", "germé", "levain", "grains", 
        "multigrain", "complet", "frais", "doré", "soft", "crunchy", "quick", "assortiment", "sans", "gluten",
        "de", "du", "d", "en", "et", "à", "au", "la", "le", "les", "un", "une", "pour", "avec"
    }
    if all(m in mots_autorises_boulangerie for m in mots_produit):
        mots_declencheurs = {"céréales", "cereales", "pain", "pains", "bread", "loaf", "baguette", "croissant", "muffin", "muffins", "brioche", "buns", "bagel", "bagels", "naan", "pita", "gruau", "flocons", "farine", "flour", "levure", "biscuit", "biscuits", "cookie", "cookies", "galette", "tarte", "gâteau", "gateau", "brownie", "biscotte", "chapelure"}
        if any(m in mots_declencheurs for m in mots_produit):
            if any(m in nom for m in ["viande", "saumon", "poulet", "surgelé"]):
                return False
            return True
    return False
def deviner_categorie(nom_produit):
    nom = str(nom_produit).lower()
    if "heinz" in nom or "kraft" in nom:
        return "🥫 Garde-manger"
        
    mots_stricte_garde_manger = {
        "riz", "basmati", "pâtes", "pasta", "spaghetti", "macaroni", "fusilli", "penne", "linguine",
        "gruau", "flocons d'avoine", "farine", "dés", "broyées", "pois chiches", "haricots noirs", 
        "thon en conserve", "thon pâle", "thon blanc", "bouillon", "bovril", "huile d'olive", 
        "huile de canola", "vinaigre de cidre", "balsamique", "sauce soya", "moutarde", "sel fin", "poivre", 
        "moulu", "poudre d'ail", "poudre d'oignon", "chili", "paprika", "origan", "herbes de provence", 
        "miel", "sirop d'érable", "beurre d'arachide", "beurre de noix"
    }
    
    nom_nettoye = re.sub(r"[()\'’\-,.!\+?|]", " ", nom)
    mots_produit = [m for m in nom_nettoye.split() if m.strip() != ""]
    
    if not mots_produit:
        return "🥫 Garde-manger"

    if any(m in nom for m in mots_stricte_garde_manger):
        if verifier_boisson_pure(nom, mots_produit):
            return "☕ Boissons"
        return "🥫 Garde-manger"

    mots_interceptes_temporaires = {
        "ail", "arugula", "asperge", "avocat", "basilic", "betterave", "brocoli", "carotte", "celeri", 
        "champignon", "chou", "concombre", "coriandre", "courge", "echalote", "epinard", "spinach", 
        "gourganes", "gingembre", "verts", "laitue", "romaine", "mais", "navet", "oignon", "panais", 
        "patate", "persil", "piment", "poireau", "leek", "radis", "tomate", "zucchini", "abricot", 
        "ananas", "apple", "banane", "banana", "bleuet", "cerise", "citron", "clementine", "fraise", 
        "framboise", "fruit", "fruits", "grapefruit", "kiwi", "lime", "mandarine", "melon", "mûre", 
        "orange", "pamplemousse", "cantaloup", "pasteque", "pêche", "poire", "pomme", "prune", "raisin", 
        "yogourt", "yaourt", "skyr", "oikos", "activia", "danone", "lait", "fromage", "cheese", "beurre", 
        "oeufs", "œufs", "oeuf", "crème", "margarine"
    }

    if any(m in mots_produit for m in mots_interceptes_temporaires):
        if verifier_boisson_pure(nom, mots_produit):
            return "☕ Boissons"
        return "📁 À vérifier (Lait, Œufs, Végétaux)"

    if verifier_boisson_pure(nom, mots_produit): return "☕ Boissons"
    if verifier_maraicher_pur(nom, mots_produit): return "🥦 Fruits et légumes"
    if verifier_surgele_pur(nom, mots_produit): return "❄️ Surgelés"
    if verifier_laitier_pur(nom, mots_produit): return "🥛 Produits laitiers et œufs"
    if verifier_boulangerie_pure(nom, mots_produit): return "🍞 Boulangerie et pâtisserie"
        
    return "🥫 Garde-manger"
# Initialisation de la Session State et chargement global
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"

# ==============================================================================
# DESIGN BARRE LATÉRALE (CORRIGÉ AVEC LES VRAIS EN-TÊTES DE LA BASE DE DONNÉES)
# ==============================================================================
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")
# 1. Alignement strict sur l'en-tête exact validé par la photo : 'entreprise_pays'
# 1. Alignement strict sur l'en-tête exact validé par la photo : 'entreprise_pays'
if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p).strip() for p in df['entreprise_pays'].unique() if pd.notna(p) and str(p).strip() != ""])
    choix_pays = st.sidebar.selectbox("Filtrer par Pays propriétaire :", liste_pays)

    # --- APARTÉ : CLASSIFICATION DES PRODUITS EN DIRECT ---
    cats_temp = []
    scats_temp = []
    for nom_prod in df['nom']:
        c, sc = classifier_produit_exact(nom_prod)
        cats_temp.append(c)
        scats_temp.append(sc)
    df['categorie'] = cats_temp
    df['sous_categorie'] = scats_temp

    # --- NOUVEAU : FILTRE 3 - CATÉGORIE PRINCIPALE ---
    liste_categories = ["Tous"] + sorted(list(df['categorie'].unique()))
    choix_cat = st.sidebar.selectbox("Filtrer par Catégorie :", liste_categories)

    # --- NOUVEAU : FILTRE 4 - SOUS-CATÉGORIE EN CASCADE ---
    sous_cats_possibles = CORRESPONDANCE_SOUS_CATEGORIES.get(choix_cat, ["Toutes"])
    choix_sous_cat = st.sidebar.selectbox("Filtrer par Sous-catégorie :", sous_cats_possibles)

    # Application des filtres et création du tableau filtré final
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
    if choix_cat != "Tous":
        df_filtre = df_filtre[df_filtre['categorie'] == choix_cat]
    if choix_sous_cat != "Toutes":
        df_filtre = df_filtre[df_filtre['sous_categorie'] == choix_sous_cat]

    # --- TRAITEMENT ET NETTOYAGE DES PRIX ---
    # Cette section s'exécute pour chaque ligne du tableau filtré pour nettoyer les formats de prix
    for index, row in df_filtre.iterrows():
        for col_key in ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']:
            v_prix = str(row.get(col_key, '')).strip().replace('nan', '').replace('$', '').replace(',', '.').strip()
