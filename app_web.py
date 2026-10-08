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
    """Se connecte automatiquement au Google Sheet, harmonise le pays Québec et pré-calcule les catégories."""
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
            mask_quebec = df_initial['entreprise_province_etat'].str.lower().str.contains('québec|quebec', na=False)
            df_initial.loc[mask_quebec, 'entreprise_province_etat'] = 'Québec'
            df_initial.loc[mask_quebec, 'entreprise_pays'] = 'Québec'

        # ==============================================================================
        # 🚀 NETTOYAGE CHIRURGICAL DES NOMS D'ENTREPRISES
        # ==============================================================================
        if 'entreprise_proprietaire' in df_initial.columns:
            def epurer_nom_entreprise(nom):
                if pd.isna(nom) or str(nom).lower() in ['nan', 'none', '']:
                    return ""
                nom_propre = str(nom).split(',')[0]
                motifs_suffixes = r'\b(inc\b\.?|limitée\b|limitee\b|ltd\b\.?|company\b|cie\b\.?)'
                nom_propre = re.sub(motifs_suffixes, '', nom_propre, flags=re.IGNORECASE)
                return nom_propre.strip()

            df_initial['entreprise_proprietaire'] = df_initial['entreprise_proprietaire'].apply(epurer_nom_entreprise)

        # ==============================================================================
        # 🚀 INJECTION ET CALCUL SÉCURISÉ DES CATÉGORIES EN AMONT
        # ==============================================================================
        if 'nom' in df_initial.columns:
            triage_initial = df_initial['nom'].apply(deviner_categorie)
            df_initial['categorie_maitresse'] = [c[0] if isinstance(c, tuple) else "Épicerie salée et Garde-manger" for c in triage_initial]
            df_initial['sous_categorie_maitresse'] = [c[1] if isinstance(c, tuple) else "Toutes les sous-catégories" for c in triage_initial]
        else:
            df_initial['categorie_maitresse'] = "Épicerie salée et Garde-manger"
            df_initial['sous_categorie_maitresse'] = "Toutes les sous-catégories"

        return df_initial
    except Exception as e:
        st.error(f"❌ Erreur de lecture : {e}")
        return pd.DataFrame()



# =====================================================================
# STRUCTURE OFFICIELLE DES CATÉGORIES ET SOUS-CATÉGORIES
# =====================================================================
CATEGORIES_PROJET = {
    "Toutes les catégories": ["Toutes les sous-catégories"],
    "Fruits et Légumes": [
        "Toutes les sous-catégories",
        "Fruits frais (petits fruits, agrumes, pommes, poires)",
        "Légumes frais (légumes-feuilles, racines, fines herbes)",
        "Prêts-à-manger (plateaux de fruits ou légumes coupés)"
    ],
    "Viandes et Volailles": [
        "Toutes les sous-catégories",
        "Bœuf, porc, veau et agneau (haché, rôtis, steaks)",
        "Volaille (poulet, dindon, poitrines, cuisses)",
        "Charcuterie et saucisses (jambon, bacon, viandes froides)"
    ],
    "Poissons et Fruits de mer": [
        "Toutes les sous-catégories",
        "Poissons frais et congelés (saumon, truite, morue)",
        "Fruits de mer (crevettes, pétoncles, moules, homard)",
        "Produits fumés ou transformés (saumon fumé, surimi)"
    ],
    "Produits laitiers et Œufs": [
        "Toutes les sous-catégories",
        "Laits et crèmes (lait de vache, crèmes à cuisson/café)",
        "Fromages (fins du Québec, cheddar, mozzarella, crème)",
        "Yogourts et desserts laitiers (grecs, poudings, kéfir)",
        "Œufs et succédanés (blancs, bruns, oméga-3, liquides)",
        "Beurre et margarines (salé/non salé, tartinades)"
    ],
    "Boulangerie et Pâtisserie": [
        "Toutes les sous-catégories",
        "Pains de table (pains tranchés, pains miche, artisanaux)",
        "Pains plats (tortillas, pitas, pains Naan)",
        "Boulangerie déjeuner (bagels, muffins, croissants, brioches)",
        "Pâtisseries et desserts (gâteaux, tartes, biscuits frais)"
    ],
    "Épicerie salée et Garde-manger": [
        "Toutes les sous-catégories",
        "Pâtes, riz et grains (pâtes, riz blanc/brun, quinoa, couscous)",
        "Huiles, vinaigres et condiments (huile, vinaigre, mayo, ketchup)",
        "Sauces et vinaigrettes (sauces à pâtes, sauces BBQ, vinaigrettes)",
        "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)",
        "Ingrédients de cuisson (farine, sucre, poudres à lever, pépites)"
    ],
    "Déjeuner et Collations": [
        "Toutes les sous-catégories",
        "Céréales et gruaux (céréales pour enfants, granolas, gruau)",
        "Tartinades (confitures, beurre d'arachide, miel, sirop d'érable)",
        "Collations salées (croustilles, bretzels, craquelins, maïs soufflé)",
        "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)",
        "Noix et graines (arachides, amandes, graines de tournesol)"
    ],
    "Aliments surgelés": [
        "Toutes les sous-catégories",
        "Plats cuisinés (pizzas, lasagnes, repas individuels)",
        "Viandes et poissons surgelés (pépites, burgers, filets panés)",
        "Fruits et légumes surgelés (mélanges de légumes, frites)",
        "Crème glacée et desserts surgelés (en pot, barres, gâteaux)"
    ],
    "Boissons (non alcoolisées)": [
        "Toutes les sous-catégories",
        "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)",
        "Jus et nectars (jus d'orange, jus de pomme, boissons aux fruits)",
        "Café, thé et tisanes (en grains ou moulu, capsules, sachets)",
        "Boissons végétales (lait d'amande, de soya, d'avoine)"
    ],
    "Bières et Vins (Alcools)": [
        "Toutes les sous-catégories",
        "Bières (microbrasseries québécoises, commerciales, cidres)",
        "Vins (vins rouges, blancs et rosés d'épicerie)"
    ]
}

def deviner_categorie(nom_produit):
    nom = str(nom_produit).lower()
    nom = nom.replace("é", "e").replace("à", "a").replace("'", " ").replace("’", " ")
    nom_isole = f" {nom} "

    if "ginger" in nom:
        if any(x in nom for x in ["tea", "thé", "snap", "cookie", "biscuits", "chews", "apple", "pomme", "dressing"]):
            pass  
        else:
            return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")
    
    if any(m in nom for m in ["fraise", "pomme", "bleuet", "clementine", "ananas", "framboise", "peche", "fruit", "baies", "melon d'eau", "asperges", "poireaux", "avocat"]):
        if not any(x in nom for x in ["surgelé", "congelé", "ice cream", "compote", "confiture", "spread", "sauce", "boisson", "jus", "water", "soda", "eau"]):
            return ("Fruits et Légumes", "Fruits frais (petits fruits, agrumes, pommes, poires)")
    if any(m in nom for m in ["carotte", "legume", "légume", "epinard", "poivron", "ail", "oignon", "salade", "concombre", "chou", "betterave"]):
        if not any(x in nom for x in ["surgelé", "congelé", "soupe", "bouillon", "crème de", "creme de"]):
            return ("Fruits et Légumes", "Légumes frais (légumes-feuilles, racines, fines herbes)")

    if any(m in nom for m in ["lait", "creme", "cream", "cremeur"]) and not any(x in nom for x in ["amande", "soya", "soy", "avoine", "vegetal", "chocolat noir"]):
        return "Produits laitiers et Œufs", "Laits et crèmes (lait de vache, crèmes à cuisson/café)"
    if any(m in nom for m in ["fromage", "cheese", "cheddar", "mozzarella", "ricotta", "feta", "fêta", "philadelphia", "parmesan"]):
        return "Produits laitiers et Œufs", "Fromages (fins du Québec, cheddar, mozzarella, crème)"
    if any(m in nom for m in ["yogourt", "yogurt", "yagourt", "pouding", "pudding", "kefir", "kéfir"]):
        return "Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)"
    if "oeuf" in nom or "œufs" in nom or "egg" in nom:
        return "Produits laitiers et Œufs", "Œufs et succédanés (blancs, bruns, oméga-3, liquides)"
    if "beurre" in nom or "margarine" in nom or "becel" in nom:
        if not any(x in nom for x in ["chocolat", "cacao", "amande", "peanut"]):
            return "Produits laitiers et Œufs", "Beurre et margarines (salé/non salé, tartinades)"

    if "bagel" in nom or "muffin" in nom or "croissant" in nom or "brioche" in nom or "chocolatine" in nom:
        return "Boulangerie et Pâtisserie", "Boulangerie déjeuner (bagels, muffins, croissants, brioches)"
    if "tortilla" in nom or "pita" in nom or "naan" in nom or "wrap" in nom:
        return "Boulangerie et Pâtisserie", "Pains plats (tortillas, pitas, pains Naan)"
    if "pain" in nom or "bread" in nom or "miche" in nom or "baguette" in nom:
        return "Boulangerie et Pâtisserie", "Pains de table (pains tranchés, pains miche, artisanaux)"
    if "gateau" in nom or "gâteau" in nom or "tarte" in nom or "pie" in nom or "pâtisserie" in nom:
        if not any(x in nom for x in ["surgelé", "congelé", "deep'n"]):
            return "Boulangerie et Pâtisserie", "Pâtisseries et desserts (gâteaux, tartes, biscuits frais)"

    if any(m in nom for m in ["tuna", "thon", "sardines", "maquereau"]):
        return ("Épicerie salée et Garde-manger", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)")
    if "crackers" in nom or "craquelin" in nom or "biscuits" in nom:
        if "soda" in nom or "water" in nom:
            return ("Déjeuner et Collations", "Collations salées (croustilles, bretzels, craquelins, maïs soufflé)")
    if any(m in nom for m in ["riz", "rice", "pate", "pâtes", "spaghetti", "macaroni", "quinoa", "couscous", "fusilli", "penne"]):
        if not any(x in nom for x in ["surgelé", "congelé"]):
            return ("Épicerie salée et Garde-manger", "Pâtes, riz et grains (pâtes, riz blanc/brun, quinoa, couscous)")
    if any(m in nom for m in ["huile", "oil", "vinaigre", "vinegar", "mayonnaise", "mayo", "ketchup", "moutarde", "mustard"]):
        return ("Épicerie salée et Garde-manger", "Huiles, vinaigres et condiments (huile, vinaigre, mayo, ketchup)")
    if "sauce" in nom or "vinaigrette" in nom or "pesto" in nom:
        return ("Épicerie salée et Garde-manger", "Sauces et vinaigrettes (sauces à pâtes, sauces BBQ, vinaigrettes)")
    if any(m in nom for m in ["soupe", "soup", "bouillon", "broth", "conserve", "boite", "boîte"]):
        return ("Épicerie salée et Garde-manger", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)")
    if any(m in nom for m in ["farine", "flour", "sucre", "sugar", "poudre à pâte", "baking"]):
        return ("Épicerie salée et Garde-manger", "Ingrédients de cuisson (farine, sucre, poudres à lever, pépites)")

    if "céréale" in nom or "cereal" in nom or "gruau" in nom or "oat" in nom or "avoine" in nom or "flakes" in nom:
        return "Déjeuner et Collations", "Céréales et gruaux (céréales pour enfants, granolas, gruau)"
    if any(m in nom for m in ["miel", "honey", "sirop", "syrup", "confiture", "jam", "peanut butter", "beurre d'arachide"]):
        return "Déjeuner et Collations", "Tartinades (confitures, beurre d'arachide, miel, sirop d'érable)"
    if any(m in nom for m in ["croustilles", "chips", "bretzel", "pretzel", "popcorn", "maïs soufflé", "craquelins"]):
        return "Déjeuner et Collations", "Collations salées (croustilles, bretzels, craquelins, maïs soufflé)"
    if any(m in nom for m in ["biscuits", "cookie", "barre tendre", "granola bar", "chocolat", "chocolate", "bonbon", "candy", "mars", "snickers"]):
        return "Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)"
    if "noix" in nom or "nut" in nom or "amande" in nom or "arachide" in nom or "graine" in nom or "seed" in nom:
        return "Déjeuner et Collations", "Noix et graines (arachides, amandes, graines de tournesol)"

    if "pizza" in nom or "lasagne" in nom or "repas" in nom or "stromboli" in nom:
        return "Aliments surgelés", "Plats cuisinés (pizzas, lasagnes, repas individuels)"
    if any(m in nom for m in ["pépites", "nuggets", "burger", "pané", "fries", "frites", "hashbrown"]):
        return "Aliments surgelés", "Viandes et poissons surgelés (pépites, burgers, filets panés)"
    if "surgelé" in nom or "congelé" in nom or "frozen" in nom:
        return "Aliments surgelés", "Fruits et légumes surgelés (mélanges de légumes, frites)"
    if any(m in nom for m in ["crème glacée", "ice cream", "sorbet", "bâtonnet", "drumstick", "magnum", "gelato"]):
        return "Aliments surgelés", "Crème glacée et desserts surgelés (en pot, barres, gâteaux)"

    mots_boissons = ["cola", "coke", "pepsi", "7up", "soda", "eau", "water", "perrier", "eska", "montellier", "bubly", "dasani", "schweppes", "rickey", "mousse", "juice", "jus", "nectar", "vitaminwater", "smart water", "flow", "liquid water enhancer", "aromatisant", "mio", "café", "coffee", "thé", "tea", "tisane", "infusion"]
    
    nom_espace = f" {nom} "
    a_mots_boissons = any(m in nom for m in mots_boissons) or " eau " in nom_espace or " l eau " in nom_espace
    
    if a_mots_boissons:
        intrus_boissons = [
            "veau", "agneau", "poulet", "cretonnade", "merguez", "saucisse", "boulettes", 
            "tuna", "thon", "maquereau", "sardines", "shrimp", "crackers", "craquelin", 
            "biscuits", "snaps", "roll", "rouleau", "pruneaux", "châtaignes", 
            "crepes", "gaufres", "salsa", "cheveux", "poireau", "leek", "asperge", "avocat", 
            "pamplemousse", "ruby red", "morceaux", "choco", "milk", "lactantia", "vin ", 
            "bordeaux", "beer", "st-ambroise", "ipeautre", "epeautre", "crisps", "réglisse", "reglisse", "cacao"
        ]
        
        if any(c in nom for c in ["café", "coffee", "thé", "tea", "tisane", "infusion"]):
            if any(x in nom for x in ["steak", "burrito", "steamers", "marinara"]):
                pass
            elif any(x in nom for x in ["crisps", "crisp", "biscuit", "buiscuit", "cookie", "cakes", "social tea", "thé social", "glacée", "glacé au café", "almond"]):
                if "boisson" in nom or "instant iced" in nom:
                    return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")
                else:
                    pass
            elif any(x in nom for x in ["crème à café", "creme a cafe", "cremette", "crème 15%", "coffee-mate", "coffee mate", "colorant à café", "rehausseur", "whitener"]):
                pass
            elif any(x in nom for x in ["coke diet", "racinette"]):
                return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")
            elif any(g in nom for g in ["glacé", "glace", "iced", "nestea", "arizona", "brisk", "peace tea", "sanpellegrino", "frappé", "twisted", "snapple", "good drink"]):
                if "twisted tea" in nom:
                    return ("Bières et Vins (Alcools)", "Bières (microbrasseries québécoises, commerciales, cidres)")
                else:
                    return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")
            else:
                return ("Boissons (non alcoolisées)", "Café, thé et tisanes (en grains ou moulu, capsules, sachets)")
            
        if any(l in nom for l in ["amand", "soya", "soy", "avoin", "oat", "silk", "nice", "coco"]):
            intrus_laits = ["biscuit", "barre", "granola", "ice cream", "crème glacée", "creme glacee", "haagen-dazs", "chocolat en tablette"]
            if not any(x in nom for x in intrus_laits):
                return ("Boissons (non alcoolisées)", "Boissons végétales (lait d'amande, de soya, d'avoine)")

        nom_espace_jus = f" {nom} "
        est_un_jus = any(j in nom for j in ["juice", "nectar", "fruitopia", "oasis", "sunrype", "watermelon"]) or " jus " in nom_espace_jus
        
        if est_un_jus and not any(k in nom for k in ["kombucha", "vivaloe"]):
            return ("Boissons (non alcoolisées)", "Jus et nectars (jus d'orange, jus de pomme, boissons aux fruits)")
        else:
            return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")

    mots_bieres = ["bière", "biere", "cidre", "st-ambroise", "molson", "labatt", "boréale", "sleeman", "alexander keith"]
    if any(m in nom for m in mots_bieres) or " ale " in nom_isole or " ipa " in nom_isole:
        intrus = ["vitamine", "barre", "galette", "dumpling", "chèvre", "pancetta", "red bull", "énergisante", "ginger"]
        if not any(x in nom for x in intrus):
            return "Bières et Vins (Alcools)", "Bières (microbrasseries québécoises, commerciales, cidres)"
            
    if " vin " in nom_isole or " wine" in nom or "bordeaux" in nom:
        if not any(x in nom for x in ["vitamine", "barre", "galette", "dumpling", "vinaigre", "cracker", "vinta", "krunch", "vindaloo"]):
            return "Bières et Vins (Alcools)", "Vins (vins rouges, blancs et rosés d'épicerie)"

    if "poulet" in nom or "chicken" in nom or "dindon" in nom or "volaille" in nom:
        return "Viandes et Volailles", "Volaille (poulet, dindon, poitrines, cuisses)"
    if any(m in nom for m in ["bœuf", "beef", "porc", "veau", "agneau", "steak", "rôti", "biftek", "merguez", "boulettes"]):
        return "Viandes et Volailles", "Bœuf, porc, veau et agneau (haché, rôtis, steaks)"
    if any(m in nom for m in ["jambon", "ham", "bacon", "saucisse", "salami", "pepperoni", "charcuterie", "cretonnade"]):
        return "Viandes et Volailles", "Charcuterie et saucisses (jambon, bacon, viandes froides)"
    if any(m in nom for m in ["saumon", "salmon", "truite", "morue", "aiglefin", "filet"]):
        return "Poissons et Fruits de mer", "Poissons frais et congelés (saumon, truite, morue)"
    if any(m in nom for m in ["crevette", "shrimp", "pétoncle", "moule", "homard"]):
        return "Poissons et Fruits de mer", "Fruits de mer (crevettes, pétoncles, moules, homard)"

    return "Épicerie salée et Garde-manger", "Toutes les sous-catégories"
       
# Initialisation de la Session State et chargement global
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"
# ==============================================================================
# DESIGN BARRE LATÉRALE (FILTRES DES POPUPS ET RAYONS)
# ==============================================================================
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")

# 1. Alignement strict sur le filtre pays
if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p).strip() for p in df['entreprise_pays'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_pays = st.sidebar.selectbox("Filtrer par Pays propriétaire :", liste_pays)
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
else:
    df_filtre = df.copy()

# 2. Filtrage par Province / État
if 'entreprise_province_etat' in df_filtre.columns:
    liste_prov = ["Toutes"] + sorted([str(p).strip() for p in df_filtre['entreprise_province_etat'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_prov = st.sidebar.selectbox("Filtrer par Province / État :", liste_prov)
    if choix_prov != "Toutes":
        df_filtre = df_filtre[df_filtre['entreprise_province_etat'] == choix_prov]

st.sidebar.markdown("---")

# 3. Boîtes de sélection des rayons d'aliments
categorie_choisie = st.sidebar.selectbox(
    "Filtrer par Catégorie d'aliments :",
    options=list(CATEGORIES_PROJET.keys()),
    index=0
)

sous_cat_disponibles = CATEGORIES_PROJET[categorie_choisie]
sous_categorie_choisie = st.sidebar.selectbox(
    "Filtrer par Sous-catégorie :",
    options=sous_cat_disponibles,
    index=0
)

# 4. Filtrage par bannière active
banniere = st.session_state['banniere_active']
if banniere != "Tous" and 'distribution' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['distribution'].str.lower().str.contains(banniere.replace('_', ' ').lower(), na=False)]

# =====================================================================
# ETAPE CORRECTIVE : CONSTRUCTION ET FILTRAGE DE L'AFFICHAGE EN AMONT
# =====================================================================
colonnes_prix_tableau = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns: 
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

# Application immédiate du filtre de catégories sur le catalogue d'affichage
if categorie_choisie != "Toutes les catégories":
    if not df_affichage.empty and "nom" in df_affichage.columns:
        triage_interne = df_affichage["nom"].apply(deviner_categorie)
        
        df_affichage["_MainCat"] = [c[0] for c in triage_interne]
        df_affichage["_SubCat"] = [c[1] for c in triage_interne]
        
        df_affichage = df_affichage[df_affichage["_MainCat"] == categorie_choisie]
        
        if sous_categorie_choisie != "Toutes les sous-catégories":
            choix_clean = str(sous_categorie_choisie).lower()
            if "boissons" in choix_clean or "amande" in choix_clean:
                df_affichage = df_affichage[df_affichage["_SubCat"].str.lower().str.contains("amande|soya|avoine|végétales|vegetales", na=False)]
            else:
                racine_choix = str(sous_categorie_choisie)[:15].lower().strip()
                df_affichage["_SubShort"] = df_affichage["_SubCat"].str.lower().str[:15].str.strip()
                df_affichage = df_affichage[df_affichage["_SubShort"] == racine_choix]
                df_affichage = df_affichage.drop(columns=["_SubShort"])

        df_affichage = df_affichage.drop(columns=["_MainCat", "_SubCat"])

# Réinitialisation propre de l'index visuel pour détruire le décalage de sélection
df_affichage = df_affichage.reset_index(drop=True)
# =====================================================================
# =====================================================================
# APERÇU DE L'IMAGE DANS LA BARRE LATÉRALE (URL EXACTE INTEGRÉE)
# =====================================================================
st.sidebar.subheader("Aperçu du produit")

cup_actuel = "nan"
if "tableau_consommateur" in st.session_state and st.session_state["tableau_consommateur"]["selection"]["rows"]:
    try:
        # Récupération sécurisée du premier index sélectionné
        liste_lignes = st.session_state["tableau_consommateur"]["selection"]["rows"]
        if liste_lignes:
            index_ligne_affiche = liste_lignes[0]  # <-- Le [0] règle le bogue
            
            # Vérification stricte par rapport à la taille du tableau affiché
            if index_ligne_affiche < len(df_affichage):
                raw_cup = df_affichage.iloc[index_ligne_affiche]['code_upc']
                cup_nettoye = str(raw_cup).strip().split('.')[0]
                cup_actuel = cup_nettoye.zfill(12) if (cup_nettoye.isdigit() and len(cup_nettoye) < 12) else cup_nettoye

        if cup_actuel and cup_actuel != "nan":
            st.sidebar.success(f"📦 Produit détecté : {cup_actuel}")
            
        extensions_possibles = [".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"]
        chemin_image_locale = None
        cup_sans_zero = cup_actuel.lstrip('0')

        for ext in extensions_possibles:
            chemin_test_exact = os.path.join("images", f"{cup_actuel}{ext}")
            chemin_test_sans_zero = os.path.join("images", f"{cup_sans_zero}{ext}")

            if os.path.exists(chemin_test_exact):
                chemin_image_locale = chemin_test_exact
                break
            elif os.path.exists(chemin_test_sans_zero):
                chemin_image_locale = chemin_test_sans_zero
                break

        if chemin_image_locale:
            st.sidebar.image(chemin_image_locale, caption="Photo : Source Locale (Achat Québec)", use_container_width=True)
        else:
            with st.sidebar.spinner("Recherche de la photo sur Open Food Facts..."):
                # Utilisation de votre lien exact validé
                url_api = f"https://openfoodfacts.org/api/v0/product/{cup_actuel}.json"
                headers = {"User-Agent": "AchatQuebecApp - Web - Version1.0"}
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

# =====================================================================
# ZONE PRINCIPALE : RENDU DES TITRES ET CHOIX DE BANNIÈRES
# =====================================================================
st.html("<h1 style='text-align: center; color: #003366; font-family: sans-serif;'>⚜️ MON GUIDE D'ACHAT LOCAL 🍁</h1>")
st.html("<p style='text-align: center; font-size: 16px; color: #666;'>Scannez un code-barres pour valider l'origine et gérer vos prix d'épicerie.</p>")

st.markdown("### 🏪 Choix rapide de votre bannière d'épicerie :")
c_iga, c_maxi = st.columns(2)
if c_iga.button("🔴 IGA", use_container_width=True): st.session_state['banniere_active'] = "IGA"; st.rerun()
if c_maxi.button("🟡 Maxi", use_container_width=True): st.session_state['banniere_active'] = "Maxi"; st.rerun()
c_met, c_sup = st.columns(2)
if c_met.button("🟢 Metro", use_container_width=True): st.session_state['banniere_active'] = "Metro"; st.rerun()
if c_sup.button("🔵 Super C", use_container_width=True): st.session_state['banniere_active'] = "Super_C"; st.rerun()
c_wal, c_tig = st.columns(2)
if c_wal.button("🔵 Walmart", use_container_width=True): st.session_state['banniere_active'] = "Walmart"; st.rerun()
if c_tig.button("🐯 Tigre Géant", use_container_width=True): st.session_state['banniere_active'] = "Tigre_Geant"; st.rerun()
c_dol, c_pro, c_all = st.columns(3)
if c_dol.button("💵 Dollarama", use_container_width=True): st.session_state['banniere_active'] = "Dollarama"; st.rerun()
if c_pro.button("🟢 Provigo", use_container_width=True): st.session_state['banniere_active'] = "Provigo"; st.rerun()
if c_all.button("🔄 Toutes", use_container_width=True): st.session_state['banniere_active'] = "Tous"; st.rerun()
# =====================================================================
# ZONE DE RECHERCHE ET SCANNER
# =====================================================================
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
            else: 
                message_erreur_recherche = f"⚠️ Aucun produit trouvé."
                df_filtre = pd.DataFrame(columns=df_filtre.columns)

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_affichage)} affichés) :")

config_colonnes = {
    "code_upc": st.column_config.TextColumn("code_upc", width="medium"),
    "nom": st.column_config.TextColumn("Nom du produit", width="large")
}

selection_tableau = None 
if not df_affichage.empty:
    selection_tableau = st.dataframe(
        df_affichage, 
        column_config=config_colonnes, 
        use_container_width=True,
        hide_index=True, 
        selection_mode="single-row", 
        on_select="rerun", 
        key="tableau_consommateur"
    )

    # CORRECTION DU TYPEERROR (INDEXATION STREAMLIT)
    if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
        # Extraction sécurisée de l'entier unique à l'intérieur de la liste de sélection
        index_ligne_cliquee = selection_tableau["selection"]["rows"][0]  # <-- Le [0] est ajouté ici
        
        if index_ligne_cliquee < len(df_affichage):
            cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
            resultats = df[df['code_upc'] == cup_selectionne]


else:
    if message_erreur_recherche:
        st.warning(message_erreur_recherche)

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
                            'siege_social': entreprise.strip(),
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
                        st.success(f"🎉 Un grand merci ! Le produit '{nom_nouveau}' a été ajouté avec succès.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement : {e}")
            else:
                st.error("⚠️ Le Nom du produit est obligatoire pour valider la fiche.")

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
        bloc_prix_html = '<div style="margin: 15px 0; display: flex; gap: 12px; flex-wrap: wrap;">'
    for col_key, (label, _) in bannières_config.items():
        v_prix = str(row.get(col_key, '')).strip().replace('nan', '')
        affichage = f"{v_prix}$" if v_prix and v_prix.lower() != "non inscrit" else "Non inscrit"
        style_card = 'background-color: #e8f5e9; border: 3px solid #2e7d32;' if col_key == meilleure_banniere_col else 'background-color: #ffffff; border: 1px solid #e0e0e0;'
        bloc_prix_html += f'<div style="padding: 10px 15px; border-radius: 8px; font-weight: bold; min-width: 140px; text-align: center; {style_card}"><div style="font-size: 12px; color: #666;">{label}</div><div style="font-size: 18px;">{affichage}</div></div>'
    bloc_prix_html += '</div>'

    # Rendu final de la grande fiche produit colorée (Achat Québécois / Canadien / Étranger)
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
        
        # Gestion dynamique du texte du bouton d'enregistrement
        texte_barre = "💾 Enregistrer les modifications de prix"
        if "dernier_horodatage" in st.session_state:
            texte_barre = f"💾 Enregistrer les modifications de prix (Fait le : {st.session_state['dernier_horodatage']})"

        bouton_enregistrer = st.form_submit_button(texte_barre, use_container_width=True)
    if bouton_enregistrer:
        try:
            # 1. Mise à jour en mémoire du tableau principal des produits
            st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()

            # 2. Préparation des données d'historique (Fuseau horaire du Québec)
            nouvelles_lignes = []
            horodatage_actuel = pd.Timestamp.now(tz='America/Toronto').tz_localize(None).strftime("%Y-%m-%d %H:%M")
            upc_produit = st.session_state['df_produits'].at[index_produit_reel, 'code_upc']

            champs_saisis = {
                'prix_iga': nouveau_iga,
                'prix_maxi': nouveau_maxi,
                'prix_metro': nouveau_metro,
                'prix_super_c': nouveau_super_c
            }

            for distribution_enseigne, valeur_prix in champs_saisis.items():
                if valeur_prix and str(valeur_prix).strip() != "":
                    try:
                        prix_propre = float(str(valeur_prix).replace(',', '.').replace('$', '').strip())
                        
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

            # 3. Tentative d'enregistrement de l'historique dans le nuage
            if nouvelles_lignes:
                df_nouvel_historique = pd.DataFrame(nouvelles_lignes)
                try:
                    sauvegarder_historique(df_nouvel_historique)
                except NameError:
                    pass

            # 4. Mémorisation de l'heure du succès pour la barre verte et rafraîchissement
            st.session_state['dernier_horodatage'] = horodatage_actuel
            time.sleep(0.5)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde : {e}")

# Mention informative finale tout en bas du script central
st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")

