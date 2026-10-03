import streamlit as st
import pandas as pd
import time
import requests
import re
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
    
    .stRadio label p { font-size: 26px !important; font-weight: bold !important; color: #111111 !important; }
    div[data-testid="stRadioHorizontal"] { gap: 40px !important; }
    
    div[data-testid="stColumns"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
    }
    div[data-testid="column"] {
        flex: 1 1 calc(33.333% - 10px) !important;
        min-width: calc(33.333% - 10px) !important;
        max-width: calc(33.333% - 10px) !important;
    }

    [data-testid="stExpanderDetails"] summary span,
    [data-testid="stExpanderDetails"] details summary,
    .stExpander details summary span {
        font-size: 26px !important;
        font-weight: bold !important;
        color: #003366 !important;
    }
</style>
""")
def charger_donnees():
    """Se connecte automatiquement au Google Sheet grâce aux secrets de Streamlit Cloud."""
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
        
        colonnes_prix = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']
        for col_prix in colonnes_prix:
            if col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].fillna("").astype(str).str.strip().replace("nan", "")
            
        if 'distribution' not in df_initial.columns and 'reseau_distribution' in df_initial.columns:
            df_initial['distribution'] = df_initial['reseau_distribution']
        elif 'distribution' not in df_initial.columns:
            df_initial['distribution'] = ""
            
        df_initial['distribution'] = df_initial['distribution'].replace('nan', '').str.strip() 
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

# DESIGN BARRE LATÉRALE
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")

if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p) for p in df['entreprise_pays'].unique() if pd.notna(p) and p != ""])
    choix_pays = st.sidebar.selectbox("Filtrer par Pays propriétaire :", liste_pays)
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
else:
    df_filtre = df.copy()

if 'entreprise_province_etat' in df_filtre.columns:
    liste_prov = ["Toutes"] + sorted([str(p) for p in df_filtre['entreprise_province_etat'].unique() if pd.notna(p) and p != ""])
    choix_prov = st.sidebar.selectbox("Filtrer par Province / État :", liste_prov)
    if choix_prov != "Toutes":
        df_filtre = df_filtre[df_filtre['entreprise_province_etat'] == choix_prov]

st.sidebar.markdown("---") 
st.sidebar.subheader("Aperçu du produit")

# CORRECTIF DE SYNCHRONISATION INDEXATION : Alignement parfait de l'image de la Sidebar
cup_actuel = "nan"
if "tableau_consommateur" in st.session_state and st.session_state["tableau_consommateur"]["selection"]["rows"]:
    try:
        index_ligne_affiche = st.session_state["tableau_consommateur"]["selection"]["rows"][0]
        df_affichage_temp = df_filtre.copy()
        
        if st.session_state.get('recherche_cup'):
            df_affichage_temp = df_affichage_temp[df_affichage_temp['nom'].str.lower().str.contains(st.session_state['recherche_cup'].lower(), na=False)]
        
        cat_choisie = st.session_state.get('cat_selector', "📁 Toutes les catégories")
        if cat_choisie != "📁 Toutes les catégories":
            df_affichage_temp = df_affichage_temp[df_affichage_temp['nom'].apply(deviner_categorie) == cat_choisie]
            
        df_affichage_temp = df_affichage_temp.reset_index(drop=True)
        raw_cup = df_affichage_temp.iloc[index_ligne_affiche]['code_upc']
        cup_actuel = str(raw_cup).strip().split('.')[0]

        if cup_actuel and cup_actuel != "nan":
            st.sidebar.success(f"📦 Produit détecté : {cup_actuel}")
            with st.sidebar.spinner("Recherche de la photo..."):
                url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecApp - Web - Version1.0 - robert.st.jules@gmail.com"}
                reponse = requests.get(url_api, headers=headers, timeout=5)
                if reponse.status_code == 200:
                    donnees = reponse.json()
                    if donnees.get("status") == 1 and "product" in donnees and "image_url" in donnees["product"]:
                        st.sidebar.image(donnees["product"]["image_url"], caption="Photo officielle OpenFoodFacts", use_container_width=True)
                    else:
                        st.sidebar.warning("⚠️ Photo non disponible dans la base publique.")
                else:
                    st.sidebar.error("❌ Serveur d'images indisponible.")
    except Exception as e:
        st.sidebar.error(f"Erreur Sidebar CUP : {e}")
with st.sidebar.expander("🔑 Administration"):
    if "admin_connecte" not in st.session_state: st.session_state["admin_connecte"] = False
    if not st.session_state["admin_connecte"]:
        mot_de_passe = st.text_input("Entrez le mot de passe de gestion", type="password", key="sidebar_mdp_secret")
        if mot_de_passe == st.secrets["admin"]["password"]:
            st.session_state["admin_connecte"] = True
            st.rerun()
    else:
        st.success("🟢 Mode Admin Actif")
        if st.button("Se déconnecter", type="primary", use_container_width=True):
            st.session_state["admin_connecte"] = False
            st.rerun()
        st.markdown("---")
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_actuel = conn.read(ttl=0)
        cup_a_supprimer = st.text_input("code_upc du produit à supprimer", key="cup_delete_input")
        if st.button("Supprimer le produit du Nuage", use_container_width=True) and cup_a_supprimer:
            df_nettoye = df_actuel[df_actuel[code_upc].astype(str) != str(cup_a_supprimer)]
            conn.update(data=df_nettoye)
            if 'df_produits' in st.session_state: del st.session_state['df_produits']
            st.success("Produit supprimé !"), time.sleep(1), st.rerun()

# 3. ZONE PRINCIPALE : Entête et Guide
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
c_iga, c_maxi = st.columns(2)
if c_iga.button("🔴 IGA", use_container_width=True): st.session_state['banniere_active'] = "IGA"
if c_maxi.button("🟡 Maxi", use_container_width=True): st.session_state['banniere_active'] = "Maxi"
c_met, c_sup = st.columns(2)
if c_met.button("🟢 Metro", use_container_width=True): st.session_state['banniere_active'] = "Metro"
if c_sup.button("🔵 Super C", use_container_width=True): st.session_state['banniere_active'] = "Super_C"
c_wal, c_tig = st.columns(2)
if c_wal.button("🔵 Walmart", use_container_width=True): st.session_state['banniere_active'] = "Walmart"
if c_tig.button("🐯 Tigre Géant", use_container_width=True): st.session_state['banniere_active'] = "Tigre_Geant"
c_dol, c_pro, c_all = st.columns(3)
if c_dol.button("💵 Dollarama", use_container_width=True): st.session_state['banniere_active'] = "Dollarama"
if c_pro.button("🟢 Provigo", use_container_width=True): st.session_state['banniere_active'] = "Provigo"
if c_all.button("🔄 Toutes", use_container_width=True): st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']
if banniere != "Tous" and 'distribution' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['distribution'].str.lower().str.contains(banniere.replace('_', ' ').lower(), na=False)]

# 4. ZONE DE RECHERCHE ET SCANNER
resultats, message_erreur_recherche = None, None
choix_mode = st.radio("👉 MODE DE RECHERCHE :", ["⌨️ Recherche manuelle", "📸 Scanner un Code-Barres"], horizontal=True, label_visibility="collapsed")
saisie_net = ""

if "cup" in st.query_params: saisie_net = str(st.query_params["cup"]).strip()

if choix_mode == "⌨️ Recherche manuelle":
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN code_upc :", value=saisie_net if saisie_net else "", key="recherche_cup")    
    if saisie: saisie_net = saisie.strip()
    if "cup" in st.query_params: st.query_params.clear()
elif choix_mode == "📸 Scanner un Code-Barres":
    from streamlit_qrcode_scanner import qrcode_scanner
    code_detecte = qrcode_scanner(key="scanner_officiel_live")
    if code_detecte: saisie_net = str(code_detecte)

if saisie_net:
    cup_saisi = saisie_net.strip()
    if 'code_upc' in df_filtre.columns:
        recherche_cup = df_filtre[df_filtre['code_upc'].astype(str).str.strip() == cup_saisi]
        if not recherche_cup.empty:
            df_filtre, resultats = recherche_cup, recherche_cup
        else:
            cond = df_filtre['nom'].str.lower().str.contains(cup_saisi.lower(), na=False)
            recherche_texte = df_filtre[cond]
            if not recherche_texte.empty:
                df_filtre = recherche_texte
                if len(recherche_texte) == 1: resultats = recherche_texte
            else: message_erreur_recherche = f"⚠️ Aucun produit trouvé."
# 5. CONFIGURATION ET RENDU DU TABLEAU INTERACTIF
colonnes_prix_tableau = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns: df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

if 'df_produits' in st.session_state and not st.session_state['df_produits'].empty:
    categories_disponibles = sorted(list(st.session_state['df_produits']['categorie'].unique()))
    categorie_selectionnee = st.selectbox("📂 Filtrer le catalogue par rayon :", options=["📁 Toutes les catégories"] + categories_disponibles, index=0, key="cat_selector")
    if categorie_selectionnee != "📁 Toutes les catégories":
        df_affichage = df_affichage[df_affichage['nom'].apply(deviner_categorie) == categorie_selectionnee]

config_colonnes = {
    "code_upc": st.column_config.TextColumn("code_upc", width="medium"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large")
}

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_affichage)} affichés) :")

# FIX CRUCIAL ET ABSOLU DU SCRIPT : On réinitialise l'index d'affichage pour éliminer le décalage !
df_affichage = df_affichage.reset_index(drop=True)
selection_tableau = None 

if not saisie_net or (not df_filtre.empty and len(df_filtre) < len(df)):
    selection_tableau = st.dataframe(
        df_affichage, column_config=config_colonnes, use_container_width=True,
        hide_index=True, selection_mode="single-row", on_select="rerun", key="tableau_consommateur"
    )

# INTERCEPTION SÉCURISÉE DU CLIC UTILISATEUR : Extraction par valeur UPC réelle unique
if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    if index_ligne_cliquee < len(df_affichage):
        cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
        resultats = df[df['code_upc'] == cup_selectionne]
if resultats is not None and not resultats.empty:
    index_produit_reel = resultats.index[0]
    row = resultats.iloc[0]

    prov = str(row.get('entreprise_province_etat', '')).strip().replace('nan', '')
    pays = str(row.get('entreprise_pays', '')).strip().replace('nan', '')
    compagnie = str(row.get('entreprise_proprietaire', '')).strip().replace('nan', '')
    
    localisation_siege = f"{prov}" + (f" ({pays})" if pays else "") if prov else pays or "Non spécifié"

    if "québec" in prov.lower():
        couleur_boite, couleur_texte, badge_html = "#e1f5fe", "#0d47a1", '<span style="background-color: #0d47a1; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold;">⚜️ ACHAT QUÉBÉCOIS</span>'
        verdict = "Ce produit est fièrement ancré au Québec (Décisions et Siège social)."
    elif "canada" in pays.lower() or "canada" in prov.lower():
        couleur_boite, couleur_texte, badge_html = "#e8f5e9", "#1b5e20", '<span style="background-color: #1b5e20; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold;">🍁 ACHAT CANADIEN</span>'
        verdict = "Ce produit encourage l'économie canadienne."
    else:
        couleur_boite, couleur_texte, badge_html = "#f5f5f5", "#424242", '<span style="background-color: #757575; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold;">🌍 PROPRIÉTÉ ÉTRANGÈRE</span>'
        verdict = "Les profits de ce produit quittent le pays."

    bannières_config = {
        'prix_iga': ('🔴 IGA', '#d32f2f'), 'prix_maxi': ('🟡 MAXI', '#f9d71c'), 'prix_metro': ('🟢 METRO', '#28a745'), 'prix_super_c': ('🔵 SUPER C', '#0056b3')
    }

    prix_valides = {}
    for col_key, _ in bannières_config.items():
        v_prix = str(row.get(col_key, '')).strip().replace('nan', '').replace('$', '').replace(',', '.').strip()
        if v_prix and v_prix.lower() != "non inscrit" and v_prix != "":
            try: prix_valides[col_key] = float(v_prix)
            except ValueError: pass

    meilleure_banniere_col = min(prix_valides, key=prix_valides.get) if prix_valides else None

    bloc_prix_html = '<div style="margin: 15px 0; display: flex; gap: 12px; flex-wrap: wrap;">'
    for col_key, (label, _) in bannières_config.items():
        v_prix = str(row.get(col_key, '')).strip().replace('nan', '')
        affichage = f"{v_prix}$" if v_prix and v_prix.lower() != "non inscrit" else "Non inscrit"
        style_card = 'background-color: #e8f5e9; border: 3px solid #2e7d32;' if col_key == meilleure_banniere_col else 'background-color: #ffffff; border: 1px solid #e0e0e0;'
        bloc_prix_html += f'<div style="padding: 10px 15px; border-radius: 8px; font-weight: bold; min-width: 140px; text-align: center; {style_card}"><div style="font-size: 12px; color: #666;">{label}</div><div style="font-size: 18px;">{affichage}</div></div>'
    bloc_prix_html += '</div>'

    st.html(f'<div style="background-color: {couleur_boite}; padding: 25px; border-radius: 12px; border-top: 8px solid {couleur_texte}; font-family: sans-serif;"><div style="display: flex; justify-content: space-between;"><span>UPC : {row.get("code_upc", "")}</span>{badge_html}</div><h2>📦 {row.get("nom", "Produit sans nom")}</h2><p style="color: {couleur_texte}; font-weight: 500;">{verdict}</p>{bloc_prix_html}</div>')

    st.markdown("#### 📝 Collaborer à la mise à jour des prix en direct au Québec :")
    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        def clean_price(val): return "" if str(val).strip().lower() in ["nan", "none", ""] else str(val).strip()
        nouveau_iga = col_p1.text_input("Prix IGA ($) :", value=clean_price(row.get('prix_iga', '')), key="form_iga")
        nouveau_maxi = col_p2.text_input("Prix Maxi ($) :", value=clean_price(row.get('prix_maxi', '')), key="form_maxi")
        nouveau_metro = col_p3.text_input("Prix Metro ($) :", value=clean_price(row.get('prix_metro', '')), key="form_metro")
        nouveau_super_c = col_p4.text_input("Prix Super C ($) :", value=clean_price(row.get('prix_super_c', '')), key="form_super_c")
        
        st.html("<style>div[data-testid='stFormSubmitButton'] button { background-color: #2e7d32 !important; color: white !important; font-size: 20px !important; font-weight: bold !important; height: 55px !important; border-radius: 10px !important; }</style>")
        bouton_enregistrer = st.form_submit_button(f"💾 Enregistrer les modifications de prix", use_container_width=True)

    if bouton_enregistrer:
        try:
            st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()
            
            if sauvegarder_donnees(st.session_state['df_produits']):
                st.success("Données collaboratives enregistrées !")
                time.sleep(0.5)
                st.rerun()
        except Exception as e: st.error(f"❌ Erreur : {e}")

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")
