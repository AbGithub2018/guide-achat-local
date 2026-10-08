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

        # Gestion stricte des colonnes de prix (prix_tiger_giant harmonisé en prix_tigre_geant pour le Sheet réel)
        colonnes_prix = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']
        for col_prix in colonnes_prix:
            if col_prix not in df_initial.columns and col_prix == 'prix_tigre_geant' and 'prix_tiger_giant' in df_initial.columns:
                df_initial['prix_tigre_geant'] = df_initial['prix_tiger_giant']
            elif col_prix not in df_initial.columns:
                df_initial[col_prix] = ""
            df_initial[col_prix] = df_initial[col_prix].fillna("").astype(str).str.strip().replace(["nan", "0", "0.0", "0,00"], "")
            
        if 'distribution' not in df_initial.columns and 'reseau_distribution' in df_initial.columns:
            df_initial['distribution'] = df_initial['reseau_distribution']
        elif 'distribution' not in df_initial.columns:
            df_initial['distribution'] = ""
            
        df_initial['distribution'] = df_initial['distribution'].replace('nan', '').str.strip() 
        if 'entreprise_province_etat' in df_initial.columns and 'entreprise_pays' in df_initial.columns:
            mask_quebec = df_initial['entreprise_province_etat'].str.lower().str.contains('québec|quebec', na=False)
            df_initial.loc[mask_quebec, 'entreprise_province_etat'] = 'Québec'
            df_initial.loc[mask_quebec, 'entreprise_pays'] = 'Québec'

        if 'entreprise_proprietaire' in df_initial.columns:
            def epurer_nom_entreprise(nom):
                if pd.isna(nom) or str(nom).lower() in ['nan', 'none', '']:
                    return ""
                nom_propre = str(nom).split(',')[0]
                motifs_suffixes = r'\b(inc\b\.?|limitée\b|limitee\b|ltd\b\.?|company\b|cie\b\.?)'
                nom_propre = re.sub(motifs_suffixes, '', nom_propre, flags=re.IGNORECASE)
                return nom_propre.strip()

            df_initial['entreprise_proprietaire'] = df_initial['entreprise_proprietaire'].apply(epurer_nom_entreprise)

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
        "Poissons frais and congelés (saumon, truite, morue)",
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
    nom = nom.replace("é", "e").replace("è", "e").replace("à", "a").replace("'", " ").replace("’", " ")
    nom_isole = f" {nom} "

    if any(m in nom for m in ["bicarbonate", "levure", "similac", "tofu", "edulcorant"]):
        return ("Épicerie salée et Garde-manger", "Ingrédients de cuisson (farine, sucre, poudres à lever, pépites)")

    motifs_patate = ["pomme de terre", "pommes de terre", "gnocchi", "pierogo", "frites", "hashbrown", "tasti taters", "rissoles", "pate alimentaire", "pates alimentaire", "capelli", "basmari", "riz "]
    if any(p in nom for p in motifs_patate):
        if "surgelé" in nom or "congelé" in nom or "mccain" in nom or "cavendish" in nom:
            return ("Aliments surgelés", "Fruits et légumes surgelés (mélanges de légumes, frites)")
        return ("Épicerie salée et Garde-manger", "Pâtes, riz et grains (pâtes, riz blanc/brun, quinoa, couscous)")

    mots_boissons = ["cola", "coke", "pepsi", "7up", "soda", "eau", "water", "perrier", "eska", "montellier", "bubly", "jus", "juice", "nectar", "fruitopia", "oasis", "sunrype", "cafe", "coffee", "the ", "tea", "tisane", "infusion", "punch", "moût", "mout ", "breezer", "smirnoff", "powerade", "hydra fruit", "fruit2o", "fizz", "drink", "cocktail", "boisson", "limonade", "redbull", "mate ", "pommersby", "smoothie", "latte", "limeade", "tropicana", "tradition", "codre", "cidre"]
    if any(m in nom for m in mots_boissons) or " juice " in nom_isole or " jus " in nom_isole or " the " in nom_isole or " punch " in nom_isole or " drink " in nom_isole or " latte " in nom_isole:
        if any(c in nom for c in ["cafe", "coffee", "the ", "tea", "tisane", "infusion", "latte"]):
            return ("Boissons (non alcoolisées)", "Café, thé et tisanes (en grains ou moulu, capsules, sachets)")
        if any(l in nom for l in ["amand", "soya", "soy", "avoin", "oat", "silk", "coco"]):
            return ("Boissons (non alcoolisées)", "Boissons végétales (lait d'amande, de soya, d'avoine)")
        if any(j in nom for j in ["jus", "juice", "nectar", "fruitopia", "oasis", "sunrype", "minut", "maide", "mout", "moût", "cocktail", "limonade", "tropicana", "tradition"]) or " jus " in nom_isole:
            return ("Boissons (non alcoolisées)", "Jus et nectars (jus d'orange, jus de pomme, boissons aux fruits)")
        return ("Boissons (non alcoolisées)", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)")

    if any(m in nom for m in ["yogourt", "yogurt", "yaourt", "skyr", "iogo", "source", "activia", "oikos", "liberte", "kefir", "cheese", "cream cheese", "philadelphia", "fondants bio", "milk", "lait", "creme", "fromage", "camembert", "feta", "oeufs", "œufs", "tubes"]):
        if any(m in nom for m in ["fromage", "cheese", "cheddar", "mozzarella", "parmesan", "philadelphia", "camembert", "feta"]):
            return ("Produits laitiers et Œufs", "Fromages (fins du Québec, cheddar, mozzarella, crème)")
        return ("Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)")
    
    if "bio- k+" in nom or "soygo" in nom:
        return ("Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)")
    motifs_tartinades = ["confiture", "jam", "spread", "marmelade", "gelee", "gele ", "double fruit", "kraft", "mott", "fruitsation", "squeez", "compote", "puree", "chutney", "sauce fruit", "fruit sauce", "beurre de pomme", "sirop", "tartinade", "peanut butter", "salsa", "sauce piquante", "chili", "tostitos", "doritos", "trempette", "sauce", "ketchup"]
    if any(m in nom for m in motifs_tartinades):
        return ("Déjeuner et Collations", "Tartinades (confitures, beurre d'arachide, miel, sirop d'érable)")

    if any(m in nom for m in ["vinaigre", "vinegar", "vinaigrette", "mayonnaise", "mayo", "moutarde", "mustard", "triscuit", "poivre noir", "huile d olive", "margarine", "beurre"]):
        if "margarine" in nom or "beurre" in nom:
             return ("Produits laitiers et Œufs", "Beurre et margarines (salé/non salé, tartinades)")
        return ("Épicerie salée et Garde-manger", "Huiles, vinaigres et condiments (huile, vinaigre, mayo, ketchup)")
    if "miel" in nom:
        return ("Déjeuner et Collations", "Tartinades (confitures, beurre d'arachide, miel, sirop d'érable)")

    if any(m in nom for m in ["graine", "seed", "noix", "nut", "amande", "arachide", "wildtoots", "baies cotieres", "montagnard", "seche", "dried"]):
        return ("Déjeuner et Collations", "Noix et graines (arachides, amandes, graines de tournesol)")

    motifs_collations = ["barre", "bar ", "bars", "snack", "collation", "biscuit", "cookie", "bonbon", "candy", "gummies", "realfruit", "chews", "gourde", "sour", "whippet", "patte d", "pattes d", "roule au", "roll up", "fruit o long", "fruit to go", "fruitsource", "jello", "jell-o", "chocolat", "excellence", "starburs", "nerds", "strudel", "choux", "lulu", "kettle", "chips", "croustilles", "biscottes", "rusks", "mum-mum", "puffies", "crisps", "melona", "gelato", "freeyumm", "little bites", "craquelin", "cracker", "croustade", "patience", "carres croustillants", "nutri-grain", "nutri grain", "go pure", "halls", "praeventia", "vital fruits", "juicy fruit", "fruitfull"]
    if any(m in nom for m in motifs_collations):
        return ("Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)")

    if any(m in nom for m in ["avoine", "oat", "cereale", "cereal", "gruau", "flakes", "granola", "muesli", "special k", "muslix", "toodle", "cheerios", "croquant pomme", "croque matin", "dejeuner pomme", "super grains", "hearty medleys"]):
        return ("Déjeuner et Collations", "Céréales et gruaux (céréales pour enfants, granolas, gruau)")

    if any(m in nom for m in ["tarte", "muffin", "scone", "trottor", "trottoir", "gateau", "cake", "pie", "pain", "bagel", "chausson", "banana bread", "genoise"]):
        return ("Boulangerie et Pâtisserie", "Pâtisseries et desserts (gâteaux, tartes, biscuits frais)")
    if any(m in nom for m in ["soupe", "soup", "bouillon", "bol ", "repas", "saucisse", "tajine", "champignons", "bebe", "baby", "gerber", "love child", "aliment pour", "snack melts"]):
        return ("Épicerie salée et Garde-manger", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)")

    if "congelé" in nom or "congele" in nom or "surgelé" in nom or "frozen" in nom or "sorbet" in nom:
        if "sorbet" in nom:
            return ("Aliments surgelés", "Crème glacée et desserts surgelés (en pot, barres, gâteaux)")
        return ("Aliments surgelés", "Fruits et légumes surgelés (mélanges de légumes, frites)")
    if any(m in nom for m in ["pate alimentaire", "pates alimentaire", "semoule", "capelli"]):
        return ("Épicerie salée et Garde-manger", "Pâtes, riz et grains (pâtes, riz blanc/brun, quinoa, couscous)")
        
    if any(m in nom for m in ["kombucha", "yop", "smoothie", "latte", "drink", "cocktail", "fizz", "thé", "tea"]):
        return ("Boissons (non alcoolisées)", "Toutes les sous-catégories")
        
    if any(m in nom for m in ["biscuit", "cookie", "whippet", "barre", "chocolat", "reglisse", "gaufrette"]):
        return ("Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)")
        
    if any(m in nom for m in ["tartinade", "sauce", "salsa", "vinaigrette", "margarine", "beurre"]):
        return ("Épicerie salée et Garde-manger", "Huiles, vinaigres et condiments (huile, vinaigre, mayo, ketchup)")

    fruits_mots = ["fraise", "pomme", "bleuet", "clementine", "ananas", "framboise", "peche", "fruit", "baies", "grenade", "banan", "avocat", "lime", "mangue", "grapefruit", "kiwi", "melon", "rhubarbe", "poire", "citrouille"]
    nom_clean = " " + nom + " "
    
    if any(m in nom_clean for m in [" gaufrette ", " gaufrettes ", " biscuit ", " biscuits ", " barre ", " barres ", " galette ", " galettes ", " roules ", " roule "]):
        return ("Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)")
        
    if any(m in nom_clean for m in [" yogourt ", " yogurt ", " yaourt ", " skyr ", " iogo ", " oikos ", " activia ", " free ", " lacteo ", " yop ", " dairy "]):
        return ("Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)")
        
    if any(m in nom_clean for m in [" kombucha ", " bierre ", " biere ", " cidre ", " codre ", " madjack ", " jus ", " juice ", " tea ", " thé ", " boisson ", " drink "]):
        return ("Boissons (non alcoolisées)", "Toutes les sous-catégories")
        
    if any(m in nom_clean for m in [" pate ", " pates ", " sauce ", " salsa ", " vinaigrette ", " margarine ", " beurre "]):
        return ("Épicerie salée et Garde-manger", "Toutes les sous-catégories")

    # CORRECTION ICI : Extraction sécurisée du texte sans créer de liste dysfonctionnelle
    upc_propre = str(nom_produit).strip().split('.')[0].lstrip('0')
    upc_boissons = ["701648010221", "623682117653"]
    upc_collations = ["063348004369", "063348004482", "058716970766"]
    upc_produits_laitiers = ["056800027099"]
    upc_conserves_et_transformes = [
        "061483055963", "061308100069", "628619200057", "058779717476", "771665516068",
        "067275001118", "059749942164", "026043814000", "065250041746", "096619614752",
        "894357002059", "060383691219", "055989069661", "667888156788", "060000132606",
        "057961028147", "695058031207", "060383988098", "871454036187", "059749929127",
        "065633134188", "816983020290", "661815001882", "057961018070", "069848058536"
    ]

    if upc_propre in upc_boissons: return ("Boissons (non alcoolisées)", "Toutes les sous-catégories")
    if upc_propre in upc_collations: return ("Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)")
    if upc_propre in upc_produits_laitiers: return ("Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)")
    if upc_propre in upc_conserves_et_transformes: return ("Épicerie salée et Garde-manger", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)")

    if any(m in nom for m in fruits_mots):
        return ("Fruits et Légumes", "Fruits frais (petits fruits, agrumes, pommes, poires)")
        
    legumes_mots = ["carotte", "legume", "epinard", "poivron", "ail", "oignon", "salade", "concombre", "chou", "betterave", "patate douce"]
    if any(m in nom for m in legumes_mots):
        return ("Fruits et Légumes", "Légumes frais (légumes-feuilles, racines, fines herbes)")

    return ("Épicerie salée et Garde-manger", "Toutes les sous-catégories")


    upc_propre = str(nom_produit).strip().split('.').lstrip('0')
    upc_boissons = ["701648010221", "623682117653"]
    upc_collations = ["063348004369", "063348004482", "058716970766"]
    upc_produits_laitiers = ["056800027099"]
    upc_conserves_et_transformes = [
        "061483055963", "061308100069", "628619200057", "058779717476", "771665516068",
        "067275001118", "059749942164", "026043814000", "065250041746", "096619614752",
        "894357002059", "060383691219", "055989069661", "667888156788", "060000132606",
        "057961028147", "695058031207", "060383988098", "871454036187", "059749929127",
        "065633134188", "816983020290", "661815001882", "057961018070", "069848058536"
    ]

    if upc_propre in upc_boissons: return ("Boissons (non alcoolisées)", "Toutes les sous-catégories")
    if upc_propre in upc_collations: return ("Déjeuner et Collations", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)")
    if upc_propre in upc_produits_laitiers: return ("Produits laitiers et Œufs", "Yogourts et desserts laitiers (grecs, poudings, kéfir)")
    if upc_propre in upc_conserves_et_transformes: return ("Épicerie salée et Garde-manger", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)")

    if any(m in nom for m in fruits_mots):
        return ("Fruits et Légumes", "Fruits frais (petits fruits, agrumes, pommes, poires)")
        
    legumes_mots = ["carotte", "legume", "epinard", "poivron", "ail", "oignon", "salade", "concombre", "chou", "betterave", "patate douce"]
    if any(m in nom for m in legumes_mots):
        return ("Fruits et Légumes", "Légumes frais (légumes-feuilles, racines, fines herbes)")

    return ("Épicerie salée et Garde-manger", "Toutes les sous-catégories")
# Initialisation de la Session State et chargement global
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"

# DESIGN BARRE LATÉRALE
st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px;'>🌐 Filtrer les produits par pays d'origine</h2>")

if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p).strip() for p in df['entreprise_pays'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_pays = st.sidebar.selectbox("Filtrer par Pays propriétaire :", liste_pays)
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
else:
    df_filtre = df.copy()

if 'entreprise_province_etat' in df_filtre.columns:
    liste_prov = ["Toutes"] + sorted([str(p).strip() for p in df_filtre['entreprise_province_etat'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_prov = st.sidebar.selectbox("Filtrer par Province / État :", liste_prov)
    if choix_prov != "Toutes":
        df_filtre = df_filtre[df_filtre['entreprise_province_etat'] == choix_prov]

st.sidebar.markdown("---")

categorie_choisie = st.sidebar.selectbox("Filtrer par Catégorie d'aliments :", options=list(CATEGORIES_PROJET.keys()), index=0)
sous_cat_disponibles = CATEGORIES_PROJET[categorie_choisie]
sous_categorie_choisie = st.sidebar.selectbox("Filtrer par Sous-catégorie :", options=sous_cat_disponibles, index=0)

banniere = st.session_state['banniere_active']
if banniere != "Tous" and 'distribution' in df_filtre.columns:
    df_filtre = df_filtre[df_filtre['distribution'].str.lower().str.contains(banniere.replace('_', ' ').lower(), na=False)]
# ZONE PRINCIPALE : RENDU DES TITRES ET CHOIX DE BANNIÈRES
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

if "cup" in st.query_params: 
    saisie_net = str(st.query_params["cup"]).strip()

if choix_mode == "⌨️ Recherche manuelle":
    if "cup_scanne" in st.session_state: 
        st.session_state["cup_scanne"] = ""  # Nettoie le scanner invisible
    saisie = st.text_input("👉 TAPEZ UN NOM DE PRODUIT OU UN code_upc :", value=saisie_net if saisie_net else "", key="recherche_cup")    
    if saisie: 
        saisie_net = saisie.strip()
    if "cup" in st.query_params: 
        st.query_params.clear()
        
elif choix_mode == "📸 Scanner un Code-Barres":
    from streamlit_qrcode_scanner import qrcode_scanner
    if "cup_scanne" not in st.session_state:
        st.session_state["cup_scanne"] = ""
        
    code_detecte = qrcode_scanner(key="scanner_officiel_live")
    if code_detecte and str(code_detecte).strip() != st.session_state["cup_scanne"]:
        st.session_state["cup_scanne"] = str(code_detecte).strip()
        st.rerun()
        
    if st.session_state["cup_scanne"]:
        saisie_net = st.session_state["cup_scanne"]
        if st.button("🔄 Effacer le scan actuel"):
            st.session_state["cup_scanne"] = ""
            st.rerun()
# RECHERCHE AMÉLIORÉE ET INTEGRATION DES FILTRES
if saisie_net and saisie_net.strip() not in ["", "****"]:
    cup_saisi = str(saisie_net).strip()
    
    def enlever_accents(texte):
        t = str(texte).lower()
        remplacements = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "ù": "u", "û": "u", "î": "i", "ï": "i", "ô": "o", "ç": "c"}
        for accent, lettre in remplacements.items():
            t = t.replace(accent, lettre)
        return t

    if 'code_upc' in df.columns:
        recherche_cup = df[df['code_upc'].astype(str).str.strip() == cup_saisi]
        if not recherche_cup.empty:
            df_filtre = recherche_cup
            resultats = recherche_cup
        else:
            saisie_propre = enlever_accents(cup_saisi)
            noms_sans_accents = df['nom'].apply(enlever_accents)
            cond = noms_sans_accents.str.contains(saisie_propre, na=False)
            recherche_texte = df[cond]
            if not recherche_texte.empty:
                df_filtre = recherche_texte
                if len(recherche_texte) == 1: 
                    resultats = recherche_texte
            else: 
                message_erreur_recherche = f"⚠️ Aucun produit trouvé."
                df_filtre = pd.DataFrame(columns=df.columns)

# Application stricte des catégories de la barre latérale uniquement si aucune recherche n'est active
if 'saisie_net' not in locals() or not saisie_net or saisie_net.strip() in ["", "****"]:
    if categorie_choisie != "Toutes les catégories" and not df_filtre.empty and "categorie_maitresse" in df_filtre.columns:
        df_filtre = df_filtre[df_filtre["categorie_maitresse"] == categorie_choisie]
        
        if sous_categorie_choisie != "Toutes les sous-catégories":
            choix_clean = str(sous_categorie_choisie).lower()
            if "boissons" in choix_clean or "amande" in choix_clean:
                df_filtre = df_filtre[df_filtre["sous_categorie_maitresse"].str.lower().str.contains("amande|soya|avoine|végétales|vegetales", na=False)]
            else:
                racine_choix = str(sous_categorie_choisie)[:15].lower().strip()
                df_filtre["_SubShort"] = df_filtre["sous_categorie_maitresse"].str.lower().str[:15].str.strip()
                df_filtre = df_filtre[df_filtre["_SubShort"] == racine_choix]
                df_filtre = df_filtre.drop(columns=["_SubShort"])

st.markdown("---")
st.markdown(f"### 📋 Liste des produits ({len(df_filtre)} affichés) :")

colonnes_prix_tableau = ['prix_iga', 'prix_maxi', 'prix_metro', 'prix_super_c', 'prix_walmart', 'prix_tigre_geant', 'prix_dollarama', 'prix_provigo']
colonnes_dispo = [c for c in ['code_upc', 'nom', 'distribution'] if c in df_filtre.columns]
df_affichage = df_filtre[colonnes_dispo + [c for c in colonnes_prix_tableau if c in df_filtre.columns]].copy()

for c in df_affichage.columns: 
    df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')

df_affichage = df_affichage.reset_index(drop=True)
# =====================================================================
# APERÇU DE L'IMAGE DANS LA BARRE LATÉRALE (URL EXACTE INTEGRÉE)
# =====================================================================
st.sidebar.subheader("Aperçu du produit")

cup_actuel = "nan"
if "tableau_consommateur" in st.session_state and st.session_state["tableau_consommateur"]["selection"]["rows"]:
    try:
        liste_lignes = st.session_state["tableau_consommateur"]["selection"]["rows"]
        if liste_lignes:
            index_ligne_affiche = liste_lignes[0]
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
                url_api = f"https://openfoodfacts.org{cup_actuel}.json"
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

    if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
        index_ligne_cliquee = selection_tableau["selection"]["rows"]
        if index_ligne_cliquee < len(df_affichage):
            cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
            resultats = df[df['code_upc'] == cup_selectionne]
else:
    if message_erreur_recherche:
        st.warning(message_erreur_recherche)

    type_saisie = "Le code-barres" if (saisie_net and saisie_net.isdigit()) else "Le produit"
    st.info(f"📦 {type_saisie} **{saisie_net}** semble être un nouveau produit pas encore répertorié.")
    st.write("Devenez le premier à l'ajouter pour la communauté Achat Québec ! 🇨🇦")
    
    with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
        nom_nouveau = st.text_input("Nom exact du produit (ex: Fraises du Québec 1L)")
        cup_final = st.text_input("code_upc", value=saisie_net.strip() if saisie_net else "", disabled=True)
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
                            'prix_iga': prix_iga.strip(),
                            'prix_maxi': prix_maxi.strip(),
                            'prix_metro': prix_metro.strip(),
                            'prix_super_c': prix_superc.strip(),
                            'prix_walmart': prix_walmart.strip(),
                            'prix_tigre_geant': prix_tigre.strip(),
                            'prix_dollarama': prix_dollarama.strip(),
                            'prix_provigo': prix_provigo.strip(),
                            'distribution.1': "",
                            'bannieres_disponibles': ""
                        }
                        
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        df_total = pd.concat([st.session_state['df_produits'], pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=df_total)
                        st.session_state['df_produits'] = df_total
                        
                        st.success(f"🎉 Un grand merci ! Le produit '{nom_nouveau}' a été ajouté avec succès.")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'enregistrement : {e}")
            else:
                st.error("⚠️ Le Nom du produit est obligatoire pour valider la fiche.")
if resultats is not None and not resultats.empty:
    index_produit_reel = resultats.index[0]  # 🚀 CORRECTION : Force l'utilisation du premier index unique
    row = resultats.iloc[0]                  # 🚀 CORRECTION : Force l'extraction de l'unique ligne de produit

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
        'prix_iga': ('🔴 IGA', '#d32f2f'), 
        'prix_maxi': ('🟡 MAXI', '#f9d71c'), 
        'prix_metro': ('🟢 METRO', '#28a745'), 
        'prix_super_c': ('🔵 SUPER C', '#0056b3'),
        'prix_walmart': ('🔵 WALMART', '#0071dc'),
        'prix_tigre_geant': ('🐯 TIGRE GÉANT', '#ffcc00'),
        'prix_dollarama': ('💵 DOLLARAMA', '#00843d'),
        'prix_provigo': ('🟢 PROVIGO', '#ff5a00')
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
        bloc_prix_html += f'<div style="padding: 10px 15px; border-radius: 8px; font-weight: bold; min-width: 135px; text-align: center; {style_card}"><div style="font-size: 11px; color: #666;">{label}</div><div style="font-size: 17px;">{affichage}</div></div>'
    bloc_prix_html += '</div>'

    st.html(f'<div style="background-color: {couleur_boite}; padding: 25px; border-radius: 12px; border-top: 8px solid {couleur_texte}; font-family: sans-serif;"><div style="display: flex; justify-content: space-between;"><span>UPC : {row.get("code_upc", "")}</span>{badge_html}</div><h2>📦 {row.get("nom", "Produit sans nom")}</h2><p style="color: {couleur_texte}; font-weight: 500;">{verdict}</p>{bloc_prix_html}</div>')
    st.markdown("#### 📝 Collaborer à la mise à jour des prix en direct au Québec :")
    with st.form("formulaire_prix_epicerie"):
        upc_dynamique = str(row.get('code_upc', 'sans_upc'))
        def clean_price(val): return "" if str(val).strip().lower() in ["nan", "none", ""] else str(val).strip()
        
        c1, c2, c3, c4 = st.columns(4)
        nouveau_iga = c1.text_input("Prix IGA ($) :", value=clean_price(row.get('prix_iga', '')), key=f"form_iga_{upc_dynamique}")
        nouveau_maxi = c2.text_input("Prix Maxi ($) :", value=clean_price(row.get('prix_maxi', '')), key=f"form_maxi_{upc_dynamique}")
        nouveau_metro = c3.text_input("Prix Metro ($) :", value=clean_price(row.get('prix_metro', '')), key=f"form_metro_{upc_dynamique}")
        nouveau_super_c = c4.text_input("Prix Super C ($) :", value=clean_price(row.get('prix_super_c', '')), key=f"form_super_c_{upc_dynamique}")
        
        c5, c6, c7, c8 = st.columns(4)
        nouveau_walmart = c5.text_input("Prix Walmart ($) :", value=clean_price(row.get('prix_walmart', '')), key=f"form_wal_{upc_dynamique}")
        nouveau_tigre = c6.text_input("Prix Tigre Géant ($) :", value=clean_price(row.get('prix_tigre_geant', '')), key=f"form_tig_{upc_dynamique}")
        nouveau_dollarama = c7.text_input("Prix Dollarama ($) :", value=clean_price(row.get('prix_dollarama', '')), key=f"form_dol_{upc_dynamique}")
        nouveau_provigo = c8.text_input("Prix Provigo ($) :", value=clean_price(row.get('prix_provigo', '')), key=f"form_provigo_{upc_dynamique}")
        
        st.html("<style>div[data-testid='stFormSubmitButton'] button { background-color: #2e7d32 !important; color: white !important; font-size: 20px !important; font-weight: bold !important; height: 55px !important; border-radius: 10px !important; }</style>")
        
        texte_barre = "💾 Enregistrer les modifications de prix"
        if "dernier_horodatage" in st.session_state:
            texte_barre = f"💾 Enregistrer les modifications de prix (Fait le : {st.session_state['dernier_horodatage']})"

        bouton_enregistrer = st.form_submit_button(texte_barre, use_container_width=True)
        
    if bouton_enregistrer:
        try:
            # Enregistrement individuel par étiquette d'index pour éviter le bogue de classe str
            st.session_state['df_produits'].at[index_produit_reel, 'prix_iga'] = nouveau_iga.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_maxi'] = nouveau_maxi.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_metro'] = nouveau_metro.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_super_c'] = nouveau_super_c.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_walmart'] = nouveau_walmart.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_tigre_geant'] = nouveau_tigre.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_dollarama'] = nouveau_dollarama.strip()
            st.session_state['df_produits'].at[index_produit_reel, 'prix_provigo'] = nouveau_provigo.strip()

            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(worksheet="Sheet1", data=st.session_state['df_produits'])

            horodatage_actuel = pd.Timestamp.now(tz='America/Toronto').tz_localize(None).strftime("%Y-%m-%d %H:%M")
            st.session_state['dernier_horodatage'] = horodatage_actuel
            st.success("Mise à jour de vos 8 bannières synchronisée !")
            time.sleep(0.5)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erreur lors de la sauvegarde : {e}")

st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere.upper()}**")
