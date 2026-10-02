import streamlit as st
import pandas as pd
import time
import requests
from streamlit_gsheets import GSheetsConnection

# 1. UNIQUE CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="Acheter Québécois & Canadien", 
    page_icon="📦", 
    layout="wide",
    initial_sidebar_state="expanded"
)

code_upc = "code_upc"

# Injection CSS de sécurité maximale
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

    /* CORRECTIF GLOBAL POUR FORCER LE GROSSISSEMENT DU TITRE */
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
def deviner_categorie(nom_produit):
    nom = str(nom_produit).lower()
    
    # =========================================================================
    # ÉTAPE 1 : LES GRANDES EXCLUSIONS PRIORITAIRES (PRODUITS TRANSFORMÉS)
    # =========================================================================
    
    # A) Boissons (Intercepte Gaillac, Pekoe, Coca, Smoothies, Nectars, Jus...)
    mots_boissons = [
        "moût", "mout", "pétillant", "petillant", "cidre", "cocktail", "drink", "sirop",
        "jus", "juice", "ju ", "boisson", "soda", "liqueur", "eau", "kombucha", "tropicana", 
        "crush", "simply orange", "bio-k", "k+plus", "gaillac", "pekoe", "coca", "smoothie", "nectar"
    ]
    if any(m in nom for m in mots_boissons):
        return "☕ Boissons"

    # B) Viandes, Poissons, Cretons et Escargots (Intercepte Cretons, Escargots, Quiches, Flamingo...)
    mots_viandes_poissons = [
        "boeuf", "bœuf", "poulet", "porc", "bacon", "saucisse", "jambon", "filet", "aiglefin", 
        "saumon", "truite", "morue", "crevette", "pétoncle", "petoncle", "crabe", "homard", 
        "poisson", "thon", "sole", "croquette", "flamingo", "farcis", "quiche", "quiches",
        "cretons", "escargots", "snails"
    ]
    if any(m in nom for m in mots_viandes_poissons):
        return "🥩 Viandes et poissons"

    # C) Produits laitiers et Fromages (Intercepte Boursin, Yogurt, Kéfir, Philadelphia, Skyr...)
    mots_laitiers = [
        "lait", "fromage", "beurre", "butter", "yogourt", "yaourt", "yogurt", "skyr", "kéfir", "kefir", 
        "crème", "creme", "œuf", "oeuf", "philadelphia", "ricotta", "pots vanille", "boursin", "light & free"
    ]
    if any(m in nom for m in mots_laitiers):
        return "🥛 Produits laitiers et œufs"

    # D) Boulangerie, Pâtisserie et Déjeuners (Intercepte Chaussons, Muffins, Granola, Gruau...)
    mots_boulangerie = [
        "pain", "baguette", "croissant", "tortilla", "tarte", "gâteau", "gateau", "boulangerie", 
        "muffin", "gruau", "céréale", "cereale", "cereals", "oat", "flocons", "bran", "granola",
        "chausson", "biscotte", "biscottes", "ostie"
    ]
    if any(m in nom for m in mots_boulangerie):
        return "🍞 Boulangerie et pâtisserie"

    # E) Surgelés et Hors-d'œuvre (Intercepte Bouchées de champignons, Pizzas, Frites...)
    mots_surgeles = ["pizza", "frite", "surgelé", "surgèle", "pépites", "bouchées", "bouchée", "suuuper bouchées"]
    if any(m in nom for m in mots_surgeles):
        return "❄️ Surgelés"

    # F) Épicerie sucrée/salée & Conserves (Bloque le Tofu, Hummus, Trempettes, Ketchup, Popcorn...)
    mots_garde_manger = [
        "tofu", "hummus", "trempette", "trempettes", "gelée", "carrés croustillants", "air heads", "mum-mum", "popcorn", "éclater",
        "biscuit", "galette", "toodle", "collation", "barre", "bars", "snack", "avoine", "trio", 
        "vinaigre", "compote", "pot pour bébé", "baby food", "strained", "sauce", "alfredo", "coulis", "pesto",
        "gummies", "bonbon", "bonbons", "halls", "pastille", "pastilles", "chocolate", "chocolat", "miel", "peanut butter",
        "bouillon", "bouillin", "chips", "croustille", "kettle", "conserve", "canne", "bocal", "peches en bocal",
        "thé", "the", "infusion", "tisane", "chewing-gum", "trident", "gomme", "bicarbonate", "ramen", "nouille", 
        "pâte", "pates", "gnocchi", "gnocchis", "purée", "puree", "olives", "moisson santé",
        "mélange", "melange", "mix", "trail", "poudre", "sel", "sucre", "épice", "epice", "épices", "epices",
        "ketchup", "confiture", "crispy", "minis", "whippet", "soupe", "potage", "orge", "graines", "graine",
        "riz", "grain", "grains", "bistro express", "citron et sésame",
        "secs", "seche", "secher", "séché", "séchée", "sultana", 
        "haricots rouges", "haricots noirs", "petits haricots", "haricots rouge", # Évite les légumineuses sèches/conserves
        "vinta", "huile de"
    ]
    if any(m in nom for m in mots_garde_manger):
        return "🥫 Garde-manger"

    # =========================================================================
    # ÉTAPE 2 : LA LISTE DES VRAIS FRUITS ET LÉGUMES MARAÎCHERS FRAIS
    # =========================================================================
    mots_fruits_legumes = [
        # Légumes roots, bulbes et tiges
        "pomme de terre", "pommes de terre", "carotte", "carottes", "baby carottes", "oignon", "oignons", "ail", "betterave", "navet", "rutabaga", "panais", "radis", "échalote", "echalote", "topinambour", "céleri-rave", "celeri-rave",
        # Feuilles, verdures et herbes
        "laitue", "romaine", "boston", "frisée", "frisee", "mesclun", "épinard", "epinard", "épinards", "chou frisé", "kale", "bette à carde", "roquette", "persil", "coriandre", "basilic", "thym", "thyme", "feuille de thym", "organic thyme",
        # Crucifères, fleurs, tiges
        "brocoli", "chou-fleur", "chou de bruxelles", "chou chinois", "chou vert", "chou rouge", "asperge", "céleri", "celeri", "poireau", "tête de violon", "tete de violon",
        # Légumes-fruits
        "tomate", "tomates", "tomates en dés", "aurora", "concombre", "poivron", "poivrons", "piment", "piments", "jalapeños", "courgette", "zucchini", "aubergine", "aubergines", "maïs", "mais", "courge", "citrouille",
        # Légumineuses fraîches et champignons
        "haricot", "haricots", "haricots verts", "petit pois", "pois mange-tout", "champignon", "champignons", "cremini", "portobello", "shiitake", "pleurote", "enoki",
        # Fruits de verger et petits fruits
        "pomme", "pommes", "paula red", "sunrise", "ginger gold", "poire", "poires", "prune", "prunes", "pêche", "peche", "peches", "sorbet pêche", "nectarine", "abricot", "abricots", "cerise", "fraise", "fraises", "bleuet", "bleuets", "framboise", "framboises", "mûre", "mure", "canneberge", "camerise",
        # Agrumes et melons
        "orange", "clémentine", "clementine", "mandarine", "mandarines", "citron", "citrons", "limes", "lime", "pamplemousse", "melon", "pastèque", "pasteque", "cantaloup",
        # Tropicaux
        "banane", "bananes", "bananas", "avocat", "ananas", "mangue", "kiwi", "raisin", "raisins", "grenade", "figue", "datte", "papaye", "fruit de la passion", "litchi", "fruit du dragon"
    ]

    if any(m in nom for m in mots_fruits_legumes):
        return "🥦 Fruits et légumes"

    # =========================================================================
    # ÉTAPE 3 : LE RESTE PAR DÉFAUT
    # =========================================================================
    return "🥫 Garde-manger"


    # =========================================================================
    # ÉTAPE 2 : LA LISTE DES VRAIS FRUITS ET LÉGUMES MARAÎCHERS FRAIS
    # =========================================================================
    mots_fruits_legumes = [
        # Légumes roots, bulbes et tiges
        "pomme de terre", "pommes de terre", "carotte", "carottes", "oignon", "oignons", "ail", "betterave", "navet", "rutabaga", "panais", "radis", "échalote", "echalote", "topinambour", "céleri-rave", "celeri-rave",
        # Feuilles, verdures et herbes
        "laitue", "romaine", "boston", "frisée", "frisee", "mesclun", "épinard", "epinard", "épinards", "chou frisé", "kale", "bette à carde", "roquette", "persil", "coriandre", "basilic", "thym", "thyme", "organic thyme",
        # Crucifères, fleurs, tiges
        "brocoli", "chou-fleur", "chou de bruxelles", "chou chinois", "chou vert", "chou rouge", "asperge", "céleri", "celeri", "poireau", "tête de violon", "tete de violon",
        # Légumes-fruits
        "tomate", "tomates", "concombre", "poivron", "poivrons", "piment", "piments", "jalapeños", "courgette", "zucchini", "aubergine", "aubergines", "maïs", "mais", "courge", "citrouille",
        # Légumineuses fraîches et champignons (Si non attrapés par l'Étape 1)
        "haricot", "haricots", "haricots verts", "petit pois", "pois mange-tout", "champignon", "cremini", "portobello", "shiitake", "pleurote", "enoki",
        # Fruits de verger et petits fruits
        "pomme", "pommes", "paula red", "sunrise", "ginger gold", "poire", "poires", "prune", "prunes", "pêche", "peche", "peches", "nectarine", "abricot", "abricots", "cerise", "fraise", "fraises", "bleuet", "bleuets", "framboise", "framboises", "mûre", "mure", "canneberge", "camerise",
        # Agrumes et melons
        "orange", "clémentine", "clementine", "mandarine", "mandarines", "citron", "citrons", "lime", "pamplemousse", "melon", "pastèque", "pasteque", "cantaloup",
        # Tropicaux
        "banane", "bananes", "bananas", "avocat", "ananas", "mangue", "kiwi", "raisin", "raisins", "grenade", "figue", "datte", "papaye", "fruit de la passion", "litchi", "fruit du dragon"
    ]

    if any(m in nom for m in mots_fruits_legumes):
        return "🥦 Fruits et légumes"

    # =========================================================================
    # ÉTAPE 3 : LE RESTE PAR DÉFAUT
    # =========================================================================
    return "🥫 Garde-manger"


    # =========================================================================
    # ÉTAPE 2 : LA LISTE DES VRAIS FRUITS ET LÉGUMES MARAÎCHERS FRES
    # =========================================================================
    mots_fruits_legumes = [
        # Légumes roots, bulbes et tiges
        "pomme de terre", "pommes de terre", "carotte", "carottes", "oignon", "ail", "betterave", "navet", "rutabaga", "panais", "radis", "échalote", "echalote", "topinambour", "céleri-rave", "celeri-rave",
        # Feuilles, verdures et herbes
        "laitue", "romaine", "boston", "frisée", "frisee", "mesclun", "épinard", "epinard", "épinards", "chou frisé", "kale", "bette à carde", "roquette", "persil", "coriandre", "basilic", "thym", "thyme",
        # Crucifères, fleurs, tiges
        "brocoli", "chou-fleur", "chou de bruxelles", "chou chinois", "chou vert", "chou rouge", "asperge", "céleri", "celeri", "poireau", "tête de violon", "tete de violon",
        # Légumes-fruits
        "tomate", "tomates", "concombre", "poivron", "poivrons", "piment", "courgette", "zucchini", "aubergine", "maïs", "mais", "courge", "citrouille",
        # Légumineuses fraîches et champignons (Seulement si non attrapés par l'Étape 1)
        "haricot", "haricots", "haricots verts", "petit pois", "pois mange-tout", "champignon", "cremini", "portobello", "shiitake", "pleurote", "enoki",
        # Fruits de verger et petits fruits
        "pomme", "pommes", "poire", "poires", "prune", "prunes", "pêche", "peche", "nectarine", "abricot", "cerise", "fraise", "fraises", "bleuet", "bleuets", "framboise", "framboises", "canneberge", "mûre", "mure", "camerise",
        # Agrumes et melons
        "orange", "clémentine", "clementine", "mandarine", "mandarines", "citron", "lime", "pamplemousse", "melon", "pastèque", "pasteque", "cantaloup",
        # Tropicaux
        "banane", "bananas", "avocat", "ananas", "mangue", "kiwi", "raisin", "raisins", "grenade", "figue", "datte", "papaye", "fruit de la passion", "litchi", "fruit du dragon"
    ]

    # Si le produit contient un de vos mots officiels maraîchers, c'est un fruit ou légume !
    if any(m in nom for m in mots_fruits_legumes):
        return "🥦 Fruits et légumes"

    # =========================================================================
    # ÉTAPE 3 : LE RESTE PAR DÉFAUT
    # =========================================================================
    return "🥫 Garde-manger"


# Initialisation et chargement de la base de données en Session Streamlit
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"
# 2. BARRE LATERALE
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

if "tableau_consommateur" in st.session_state and st.session_state["tableau_consommateur"]["selection"]["rows"]:
    index_ligne = st.session_state["tableau_consommateur"]["selection"]["rows"][0]
    try:
        terme_recherche = st.session_state.get('recherche_cup', '').lower()
        df_affichage_temp = df_filtre[df_filtre['nom'].str.lower().str.contains(terme_recherche, na=False)] if terme_recherche else df_filtre.copy()
        raw_cup = df_affichage_temp.iloc[index_ligne]['code_upc']

        cup_actuel = str(raw_cup).strip().split('.')[0]

        if cup_actuel and cup_actuel != "nan":
            st.sidebar.success(f"📦 Produit détecté : {cup_actuel}")
            with st.sidebar.spinner("Recherche de la photo..."):
                try:
                    url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
                    headers = {"User-Agent": "AchatQuebecApp - Web - Version1.0 - robert.st.jules@gmail.com"}
                    reponse = requests.get(url_api, headers=headers, timeout=5)
                    if reponse.status_code == 200:
                        donnees = reponse.json()
                        if donnees.get("status") == 1 and "product" in donnees and "image_url" in donnees["product"]:
                            lien_photo = donnees["product"]["image_url"]
                            st.sidebar.image(lien_photo, caption="Photo officielle OpenFoodFacts", use_container_width=True)
                        else:
                            st.sidebar.warning("⚠️ Photo non disponible dans la base publique.")
                    else:
                        st.sidebar.error("❌ Serveur d'images indisponible.")
                except Exception as e:
                    st.sidebar.error(f"⚠️ Erreur de connexion : {e}")
        else:
            st.sidebar.warning("code_upc invalide ou vide.")
    except Exception as e:
        st.sidebar.error(f"Erreur de lecture du CUP : {e}")

st.sidebar.markdown("---") 

with st.sidebar.expander("🔑 Administration"):
    if "admin_connecte" not in st.session_state:
        st.session_state["admin_connecte"] = False

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
        
        if st.button("Supprimer définitivement le produit du Nuage", use_container_width=True):
            if cup_a_supprimer:
                df_nettoye = df_actuel[df_actuel[code_upc].astype(str) != str(cup_a_supprimer)]
                conn.update(data=df_nettoye)
                if 'df_produits' in st.session_state:
                    del st.session_state['df_produits']
                st.success("Produit supprimé avec succès !")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Veuillez entrer un code_upc valide.")
# 3. ZONE PRINCIPALE : Entête
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

with st.expander(":blue[**Comment utiliser l'application et économiser ?**] *(Cliquez pour ouvrir)*", icon="ℹ️"):
    st.markdown("""
    ### 🛒 Protégeons notre portefeuille, encourageons l'achat local !
    Bienvenue sur **AchatQuébec**, votre outil citoyen et collaboratif pour dénicher les meilleurs prix à l'épicerie tout en gardant notre argent ici. Ensemble, reprenons le contrôle de notre panier d'épicerie !
    
    #### 🕵️‍♂️ Comment ça fonctionne ?
    1. **Recherchez un produit :** Tapez un mot-clé (ex: *pomme*) ou le code_upc.
    2. **Identifiez la provenance :** Repérez les drapeaux et badges (Québec ⚜️, Canada 🍁).
    3. **Comparez les prix :** Voyez d'un coup d'œil quelle bannière est la moins chère.
    
    #### ✍️ Devenez un consommateur solidaire !
    Vous êtes à l'épicerie ? Cochez le produit, inscrivez le prix trouvé dans le formulaire au bas de l'écran, et cliquez sur **Enregistrer**. Chaque contribution aide la communauté !
    """)

st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")

col_iga, col_maxi = st.columns(2)
if col_iga.button("🔴 IGA", use_container_width=True):
    st.session_state['banniere_active'] = "IGA"
if col_maxi.button("🟡 Maxi", use_container_width=True):
    st.session_state['banniere_active'] = "Maxi"

col_metro, col_super_c = st.columns(2)
if col_metro.button("🟢 Metro", use_container_width=True):
    st.session_state['banniere_active'] = "Metro"
if col_super_c.button("🔵 Super C", use_container_width=True):
    st.session_state['banniere_active'] = "Super_C"

col_walmart, col_tigre = st.columns(2)
if col_walmart.button("🔵 Walmart", use_container_width=True):
    st.session_state['banniere_active'] = "Walmart"
if col_tigre.button("🐯 Tigre Géant", use_container_width=True):
    st.session_state['banniere_active'] = "Tigre_Geant"

col_dollarama, col_provigo, col_tous = st.columns(3)
if col_dollarama.button("💵 Dollarama", use_container_width=True):
    st.session_state['banniere_active'] = "Dollarama"
if col_provigo.button("🟢 Provigo", use_container_width=True):
    st.session_state['banniere_active'] = "Provigo"
if col_tous.button("🔄 Toutes", use_container_width=True):
    st.session_state['banniere_active'] = "Tous"

banniere = st.session_state['banniere_active']

if banniere != "Tous" and 'distribution' in df_filtre.columns:
    nom_banniere_recherche = banniere.replace('_', ' ')
    condition_distribution = df_filtre['distribution'].str.lower().str.contains(nom_banniere_recherche.lower(), na=False)
    df_filtre = df_filtre[condition_distribution]
# 4. ZONE DE RECHERCHE ET SCANNER PHOTO
resultats = None
message_erreur_recherche = None

choix_mode = st.radio(
    "👉 MODE DE RECHERCHE :",
    ["⌨️ Recherche manuelle", "📸 Scanner un Code-Barres"],
    horizontal=True,
    label_visibility="collapsed"
)
saisie_net = ""

if "cup" in st.query_params:
    saisie_net = str(st.query_params["cup"]).strip()
    st.success(f"✅ code_upc détecté : {saisie_net}")

if choix_mode == "⌨️ Recherche manuelle":
    valeur_par_defaut = saisie_net if saisie_net else ""
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN code_upc :", value=valeur_par_defaut, key="recherche_cup")    
    if saisie:
        saisie_net = saisie.strip()
    if "cup" in st.query_params:
        st.query_params.clear()
        
elif choix_mode == "📸 Scanner un Code-Barres":
    st.html("<h2 style='color: #003366; font-size: 28px; font-weight: bold;'>📷 Scanneur Local Haute Performance</h2>")
    st.html("<p style='font-size: 20px; color: #333;'>Prenez une photo nette et horizontale du code-barres avec votre téléphone</p>")
    st.markdown("### 📷 Scanner le code-barres en direct")
    st.write("Présentez le code-barres bien net devant la caméra arrière de votre cellulaire.")
    
    from streamlit_qrcode_scanner import qrcode_scanner
    code_detecte = qrcode_scanner(key="scanner_officiel_live")
    if code_detecte:
        st.success(f"🎉 Code-barres détecté avec succès : {code_detecte}")
        st.session_state['code_barre_input'] = str(code_detecte)
        saisie_net = str(code_detecte)

if saisie_net:
    cup_saisi = saisie_net.strip()
    terme_recherche_minuscule = cup_saisi.lower()

    if 'code_upc' in df_filtre.columns:
        recherche_cup = df_filtre[df_filtre['code_upc'].astype(str).str.strip() == cup_saisi]
        if not recherche_cup.empty:
            df_filtre = recherche_cup
            resultats = recherche_cup
        else:
            conditions = pd.Series(False, index=df_filtre.index)
            if 'nom' in df_filtre.columns:
                conditions |= df_filtre['nom'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
            if 'siege_social' in df_filtre.columns:
                conditions |= df_filtre['siege_social'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
            if 'lieu_usine' in df_filtre.columns:
                conditions |= df_filtre['lieu_usine'].str.lower().str.contains(terme_recherche_minuscule, na=False, regex=False)
                
            recherche_texte = df_filtre[conditions]
            if not recherche_texte.empty:
                df_filtre = recherche_texte
                if len(recherche_texte) == 1:
                    resultats = recherche_texte
            else:
                message_erreur_recherche = f"⚠️ Aucun produit ne correspond à '{saisie_net}' dans cette sélection."
# 5. CONFIGURATION ET RENDU DU TABLEAU INTERACTIF
colonnes_prix_tableau = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'entreprise_proprietaire', 'entreprise_province_etat', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns:
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

if 'df_produits' in st.session_state and not st.session_state['df_produits'].empty:
    categories_disponibles = sorted(list(st.session_state['df_produits']['categorie'].unique()))
    options_menu = ["📁 Toutes les catégories"] + categories_disponibles
    categorie_selectionnee = st.selectbox(
        "📂 Filtrer le catalogue par rayon :",
        options=options_menu,
        index=0
    )
    if categorie_selectionnee != "📁 Toutes les catégories":
        df_affichage = df_affichage[df_affichage['nom'].apply(deviner_categorie) == categorie_selectionnee]

config_colonnes = {
    "code_upc": st.column_config.TextColumn("code_upc", width="medium"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large"),
    "siege_social": st.column_config.TextColumn("Entreprise"),
    "entreprise_province_etat": st.column_config.TextColumn("Province/État"),
    "distribution": st.column_config.TextColumn("Réseau d'épicerie"),
    "prix_iga": st.column_config.TextColumn("Prix IGA"),
    "prix_maxi": st.column_config.TextColumn("Prix Maxi"),
    "prix_metro": st.column_config.TextColumn("Prix Metro"),
    "prix_super_c": st.column_config.TextColumn("Prix Super C")
}

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_affichage)} affichés selon vos bannières et filtres) :")
st.write("💡 Cliquez n'importe où sur la ligne d'un produit pour voir sa fiche complète ci-dessous.")

selection_tableau = None 

if not saisie_net:
    selection_tableau = st.dataframe(
        df_affichage, column_config=config_colonnes, use_container_width=True,
        hide_index=True, selection_mode="single-row", on_select="rerun", key="tableau_consommateur"
    )
elif not df_filtre.empty and len(df_filtre) < len(df):
    selection_tableau = st.dataframe(
        df_affichage, column_config=config_colonnes, use_container_width=True,
        hide_index=True, selection_mode="single-row", on_select="rerun", key="tableau_consommateur"
    )
else:
    if message_erreur_recherche and not saisie_net.strip().isdigit():
        st.warning(message_erreur_recherche)

    if saisie_net.strip().isdigit() and len(saisie_net.strip()) >= 10:
        st.info(f"📦 Le code_upc **{saisie_net}** semble être un nouveau produit pas encore répertorié.")
        st.write("Devenez le premier à l'ajouter pour la communauté Achat Québec ! 🇨🇦")
        
        with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
            nom_nouveau = st.text_input("Nom exact du produit (ex: Fraises du Québec 1L)")
            cup_final = st.text_input("code_upc", value=saisie_net.strip(), disabled=True)
            entreprise = st.text_input("Entreprise propriétaire / Marque (ex: Unico)")
            province = st.text_input("Province / État (ex: Québec)")
            pays = st.text_input("Pays", value="Canada")
            distribution = st.text_input("Réseau d'épicerie (ex: IGA, Maxi, Metro, Super C)")
            
            st.write("---")
            st.write("**Entrez les prix constatés en magasin (optionnel) :**")
            col1, col2, col3, col4 = st.columns(4)
            with col1: prix_iga = st.text_input("Prix IGA ($)", value="")
            with col2: prix_maxi = st.text_input("Prix Maxi ($)", value="")
            with col3: prix_metro = st.text_input("Prix Metro ($)", value="")
            with col4: prix_superc = st.text_input("Prix Super C ($)", value="")
        
            col5, col6, col7, col8 = st.columns(4)
            with col5: prix_walmart = st.text_input("Prix Walmart ($)", value="")
            with col6: prix_tigre = st.text_input("Prix Tigre Géant ($)", value="")
            with col7: prix_dollarama = st.text_input("Prix Dollarama ($)", value="")
            with col8: prix_provigo = st.text_input("Prix Provigo ($)", value="")

            bouton_creer = st.form_submit_button("🚀 Enregistrer le nouveau produit dans le Nuage", type="primary", use_container_width=True)

            if bouton_creer:
                if nom_nouveau:
                    with st.spinner("Enregistrement de la nouvelle fiche produit..."):
                        try:
                            p_iga_val = prix_iga.strip() if prix_iga.strip() else ""
                            p_maxi_val = prix_maxi.strip() if prix_maxi.strip() else ""
                            p_metro_val = prix_metro.strip() if prix_metro.strip() else ""
                            p_super_c_val = prix_superc.strip() if prix_superc.strip() else ""
                            p_walmart_val = prix_walmart.strip() if prix_walmart.strip() else ""
                            p_tigre_val = prix_tigre.strip() if prix_tigre.strip() else ""
                            p_dollarama_val = prix_dollarama.strip() if prix_dollarama.strip() else ""
                            p_provigo_val = prix_provigo.strip() if prix_provigo.strip() else ""
                            
                            nouvelle_ligne = {
                                'code_upc': cup_final,
                                'nom': nom_nouveau.strip(),
                                'siege_social': blueprint.strip() if 'blueprint' in locals() else entreprise.strip(),
                                'lieu_usine': "",
                                'distribution': distribution.strip(),
                                'entreprise_proprietaire': "",
                                'entreprise_province_etat': province.strip(),
                                'entreprise_pays': pays.strip(),
                                'priorite': "",
                                'usine_principale': "",
                                'reseau_distribution': "",
                                'prix_iga': p_iga_val,
                                'prix_maxi': p_maxi_val,
                                'prix_metro': p_metro_val,
                                'prix_super_c': p_super_c_val,
                                'prix_walmart': p_walmart_val,
                                'prix_tigre_geant': p_tigre_val,
                                'prix_dollarama': p_dollarama_val,
                                'prix_provigo': p_provigo_val,
                                'distribution.1': "",
                                'bannieres_disponibles': ""
                            }
                            
                            st.session_state['df_produits'] = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                            
                            if sauvegarder_donnees(st.session_state['df_produits']):
                                st.success(f"🎉 Un grand merci ! Le produit '{nom_nouveau}' a été ajouté avec succès.")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de l'enregistrement : {e}")
                else:
                    st.error("⚠️ Le Nom du produit est obligatoire pour valider la fiche.")

if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
    index_ligne_cliquee = selection_tableau["selection"]["rows"][0]
    if index_ligne_cliquee < len(df_affichage):
        cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
        resultats = df[df['code_upc'] == cup_selectionne]
if resultats is not None and not resultats.empty:
    index_produit_reel = resultats.index
    row = resultats.iloc[0]

    prov = str(row.get('entreprise_province_etat', '')).strip().replace('nan', '')
    pays = str(row.get('entreprise_pays', '')).strip().replace('nan', '')
    compagnie = str(row.get('entreprise_proprietaire', '')).strip().replace('nan', '')
    usine_actuelle = str(row.get('lieu_usine', row.get('usine_principale', 'À déterminer'))).strip().replace('nan', '')
    reseau = str(row.get('distribution', 'Général')).strip().replace('nan', '')
    
    localisation_siege = f"{prov}" if prov else ""
    if pays: localisation_siege += f" ({pays})" if localisation_siege else pays
    if not localisation_siege: localisation_siege = "Non spécifié"

    if "québec" in prov.lower():
        couleur_boite, couleur_texte, badge_html = "#e1f5fe", "#0d47a1", '<span style="background-color: #0d47a1; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px;">⚜️ ACHAT QUÉBÉCOIS</span>'
        verdict = "Ce produit est fièrement ancré au Québec (Décisions et Siège social)."
    elif "canada" in pays.lower() or "canada" in prov.lower():
        couleur_boite, couleur_texte, badge_html = "#e8f5e9", "#1b5e20", '<span style="background-color: #1b5e20; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px;">🍁 ACHAT CANADIEN</span>'
        verdict = "Ce produit encourage l'économie canadienne."
    else:
        couleur_boite, couleur_texte, badge_html = "#f5f5f5", "#424242", '<span style="background-color: #757575; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 14px;">🌍 PROPRIÉTÉ ÉTRANGÈRE</span>'
        verdict = "Les profits de ce produit quittent le pays."

    bannières_config = {
        'prix_iga': ('🔴 IGA', '#d32f2f'),
        'prix_maxi': ('🟡 MAXI', '#f9d71c'),
        'prix_metro': ('🟢 METRO', '#28a745'),
        'prix_super_c': ('🔵 SUPER C', '#0056b3'),
        'prix_walmart': ('🔵 WALMART', '#0071dc'),
        'prix_tigre_geant': ('🐯 TIGRE GÉANT', '#e31837'),
        'prix_dollarama': ('💵 DOLLARAMA', '#006a4e'),
        'prix_provigo': ('🟢 PROVIGO', '#e31b23')
    }

    prix_valides = {}
    for col_key, (label, _) in bannières_config.items():
        v_prix = str(row.get(col_key, '')).strip().replace('nan', '').replace('$', '').replace(',', '.').strip()
        if v_prix and v_prix.lower() != "non inscrit" and v_prix != "":
            try: prix_valides[col_key] = float(v_prix)
            except ValueError: pass

    meilleure_banniere_col = min(prix_valides, key=prix_valides.get) if prix_valides else None

    bloc_prix_html = '<div style="margin: 15px 0; display: flex; gap: 12px; flex-wrap: wrap;">'
    for col_key, (label, color) in bannières_config.items():
        v_prix = str(row.get(col_key, '')).strip().replace('nan', '')
        affichage = f"{v_prix}$" if v_prix and v_prix.lower() != "non inscrit" else "Non inscrit"
        
        if meilleure_banniere_col and col_key == meilleure_banniere_col:
            style_card = 'background-color: #e8f5e9; border: 3px solid #2e7d32; box-shadow: 0px 4px 10px rgba(0,0,0,0.15);'
            label_display = f'🔥 {label}'
        else:
            style_card = 'background-color: #ffffff; border: 1px solid #e0e0e0;'
            label_display = label
            
        bloc_prix_html += f"""
        <div style="padding: 10px 15px; border-radius: 8px; color: #1a1a1a; font-weight: bold; font-size: 15px; min-width: 140px; text-align: center; {style_card}">
            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">{label_display}</div>
            <div style="font-size: 18px; color: #1a1a1a;">{affichage}</div>
        </div>
        """
    bloc_prix_html += '</div>'

    alerte_economie_html = ""
    if meilleure_banniere_col:
        nom_gagnant, _ = bannières_config[meilleure_banniere_col]
        alerte_economie_html = f"""
        <div style="background-color: #e8f5e9; color: #1b5e20; padding: 10px 15px; border-radius: 6px; font-weight: bold; font-size: 16px; margin-bottom: 15px; border-left: 5px solid #2e7d32;">
            💡 ÉCONOMIE : Le meilleur prix actuel est chez <b>{nom_gagnant}</b> ({prix_valides[meilleure_banniere_col]:.2f}$) !
        </div>
        """

    st.html(f"""
<div style="background-color: {couleur_boite}; padding: 25px; border-radius: 12px; border-top: 8px solid {couleur_texte}; margin-bottom: 20px; font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
        <span style="font-size: 13px; color: #555; font-weight: 500;">UPC : {str(row.get('code_upc', ''))}</span>
        {badge_html}
    </div>
    <h2 style="color: #1a1a1a; margin: 0 0 5px 0; font-size: 26px; font-weight: 800;">📦 {row.get('nom', 'Produit sans nom')}</h2>
    <p style="color: {couleur_texte}; font-size: 15px; margin: 0 0 20px 0; font-weight: 500;">{verdict}</p>
    
    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 25px;">
        <span style="background-color: rgba(0,0,0,0.04); color: #444; padding: 6px 12px; border-radius: 6px; font-size: 14px;"><b>🏭 Compagnie :</b> {compagnie if compagnie else 'Non spécifié'}</span>
        <span style="background-color: rgba(0,0,0,0.04); color: #444; padding: 6px 12px; border-radius: 6px; font-size: 14px;"><b>📍 Siège :</b> {localisation_siege}</span>
        <span style="background-color: rgba(0,0,0,0.04); color: #444; padding: 6px 12px; border-radius: 6px; font-size: 14px;"><b>🏪 Usine principale :</b> {usine_actuelle}</span>
        <span style="background-color: rgba(0,0,0,0.04); color: #444; padding: 6px 12px; border-radius: 6px; font-size: 14px;"><b>🛍️ Dispo chez :</b> {reseau}</span>
    </div>
    
    <h4 style="margin: 0 0 10px 0; color: #333; font-size: 16px; font-weight: 700; text-transform: uppercase;">💰 Comparatif des prix en magasin :</h4>
    {alerte_economie_html}
    {bloc_prix_html}
</div>
""")

    st.markdown("#### 📝 Collaborer à la mise à jour des prix en direct au Québec :")
    with st.form("formulaire_prix_epicerie"):
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        def clean_price(val):
            v_str = str(val).strip()
            return "" if v_str.lower() in ["nan", "none", ""] else v_str

        nouveau_iga = col_p1.text_input("Prix IGA ($) :", value=clean_price(row.get('prix_iga', '')), key="edit_iga")
        nouveau_maxi = col_p2.text_input("Prix Maxi ($) :", value=clean_price(row.get('prix_maxi', '')), key="edit_maxi")
        nouveau_metro = col_p3.text_input("Prix Metro ($) :", value=clean_price(row.get('prix_metro', '')), key="edit_metro")
        nouveau_super_c = col_p4.text_input("Prix Super C ($) :", value=clean_price(row.get('prix_super_c', '')), key="edit_super_c")
        
        col_p5, col_p6, col_p7, col_p8 = st.columns(4)
        nouveau_walmart = col_p5.text_input("Prix Walmart ($) :", value=clean_price(row.get('prix_walmart', '')), key="edit_walmart")
        nouveau_tigre = col_p6.text_input("Prix Tigre Géant ($) :", value=clean_price(row.get('prix_tigre_geant', '')), key="edit_tigre")
        nouveau_dollarama = col_p7.text_input("Prix Dollarama ($) :", value=clean_price(row.get('prix_dollarama', '')), key="edit_dollarama")
        nouveau_provigo = col_p8.text_input("Prix Provigo ($) :", value=clean_price(row.get('prix_provigo', '')), key="edit_provigo")
        
                # Injection CSS pour styliser uniquement le bouton de ce formulaire en vert
        st.html("""
        <style>
            div[data-testid="stFormSubmitButton"] button {
                background-color: #2e7d32 !important; /* Un beau vert épicerie / succès */
                color: white !important;
                font-size: 20px !important;
                font-weight: bold !important;
                height: 55px !important;
                border-radius: 10px !important;
                border: none !important;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15) !important;
                transition: all 0.3s ease !important;
                cursor: pointer !important;
            }
            div[data-testid="stFormSubmitButton"] button:hover {
                background-color: #1b5e20 !important; /* Vert plus foncé au survol */
                transform: translateY(-2px) !important;
                box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.2) !important;
            }
        </style>
        """)
        
        date_du_jour = pd.Timestamp.now().strftime("%Y-%m-%d")
        bouton_enregistrer = st.form_submit_button(f"💾 Enregistrer les modifications de prix (Aujourd'hui : {date_du_jour})", type="primary", use_container_width=True)

    if bouton_enregistrer:
        try:
            # Extrait le premier index de la liste pour éviter l'erreur de scalaire
            idx_unique = index_produit_reel[0]
            
            st.session_state['df_produits'].at[idx_unique, 'prix_iga'] = nouveau_iga.strip() if nouveau_iga else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_maxi'] = nouveau_maxi.strip() if nouveau_maxi else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_metro'] = nouveau_metro.strip() if nouveau_metro else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_super_c'] = nouveau_super_c.strip() if nouveau_super_c else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_walmart'] = nouveau_walmart.strip() if nouveau_walmart else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_tigre_geant'] = nouveau_tigre.strip() if nouveau_tigre else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_dollarama'] = nouveau_dollarama.strip() if nouveau_dollarama else ""
            st.session_state['df_produits'].at[idx_unique, 'prix_provigo'] = nouveau_provigo.strip() if nouveau_provigo else ""
         
            # === DÉBUT DU BLOC HISTORIQUE CITOYEN ===
            champs_saisis = {
                'prix_iga': nouveau_iga,
                'prix_maxi': nouveau_maxi,
                'prix_metro': nouveau_metro,
                'prix_super_c': nouveau_super_c,
                'prix_walmart': nouveau_walmart,
                'prix_tigre_geant': nouveau_tigre,
                'prix_dollarama': nouveau_dollarama,
                'prix_provigo': nouveau_provigo
            }
         
            nouvelles_lignes = []
            horodatage_actuel = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            upc_produit = cup_actuel  # Utilise le CUP détecté plus haut
          
            for distribution_enseigne, valeur_prix in champs_saisis.items():
                if valeur_prix and str(valeur_prix).strip() != "":
                    try:
                        prix_propre = float(str(valeur_prix).replace(',', '.').replace('$', '').strip())
                       
                        # 1. DÉFINITION DES ENTÊTES ET DE LEUR UTILITÉ (POUR MÉMOIRE)
                        # explications_colonnes = {
                        #     'horodatage': 'Colonne A - Date et heure de l'entrée',
                        #     'code_upc': 'Colonne B - Code-barres unique',
                        #     'distribution': 'Colonne C - Nom de la bannière',
                        #     'prix': 'Colonne D - Prix numérique en minuscule',
                        #     'source': 'Colonne E - Origine de la donnée'
                        # }
                     
                        nouvelle_ligne = {
                            'horodatage': horodatage_actuel,
                            'code_upc': upc_produit,
                            'distribution': distribution_enseigne,
                            'prix': prix_propre,
                            'source': 'collaboratif'
                        }
                        nouvelles_lignes.append(nouvelle_ligne)
                    except ValueError:
                        pass
                     
            if nouvelles_lignes:
                df_nouvel_historique = pd.DataFrame(nouvelles_lignes)
                sauvegarder_historique(df_nouvel_historique)
            # === FIN DU BLOC HISTORIQUE CITOYEN ===
         
            if sauvegarder_donnees(st.session_state['df_produits']):

                st.success("Base de données collaborative mise à jour avec succès !")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur lors de la mise à jour des prix : {e}")


st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")

