import streamlit as st
import pandas as pd
import urllib.parse
import time
import requests
import re
import os
import base64
import io
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# Configuration unique de la page
st.set_page_config(
    page_title="Acheter Québécois & Canadien",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# INTERRUPTEUR DE MAINTENANCE (Mettre à True pour bloquer et false pour débloquer l'accès)
# =========================================================
EN_CONSTRUCTION = False

if EN_CONSTRUCTION:
    # 1. Configuration esthétique de la page temporaire
    st.set_page_config(page_title="Maintenance - Épicerie QC", page_icon="🍏", layout="centered")
    
    # 2. Affichage visuel épuré pour vos utilisateurs
    st.title("🇨🇦 Base de Données de l'Épicerie Citoyenne")
    st.markdown("### 🛠️ Mise à jour majeure en cours...")
    
    st.warning("⚠️ **L'application est temporairement suspendue pour maintenance.**")
    
    st.info(
        f"💡 Nous retravaillons actuellement notre algorithme et mettons à jour nos fiches "
        f"pour optimiser la recherche parmi nos **10 500 produits référencés**. "
        "Le service sera de retour très bientôt !"
    )
    
    # Petit indicateur visuel de chargement
    st.spinner("Indexation de la base de données québécoise en cours...")
    
    st.divider()
    st.caption("Merci de votre patience et de votre soutien envers ce projet bénévole québécois. ❤️")
    
    # 3. LE PLUS IMPORTANT : On arrête l'exécution du script ici pour bloquer le reste de l'app
    st.stop()

st.markdown(
    """
    <div style="display: inline-flex; align-items: center; gap: 10px; font-family: sans-serif; margin-bottom: 20px; vertical-align: middle;">
        <a href="https://guide-achat-local-gerer.streamlit.app/" target="_blank" style="display: inline-flex; align-items: center; background-color: #f0f2f6; color: #31333F; border: 1px solid #d3d3d3; padding: 5px 12px; font-size: 14px; border-radius: 4px; text-decoration: none; gap: 6px; white-space: nowrap; font-weight: 500; height: 32px; box-sizing: border-box;">⚙️ Gestion</a>
        <details style="cursor: pointer; position: relative; display: inline-flex; align-items: center; height: 32px;">
            <summary style="list-style: none; display: inline-flex; align-items: center; font-size: 14px; color: #555; outline: none;">
                <span style="font-size: 16px; margin-right: 4px;">ℹ️</span>
                <span style="text-decoration: underline;">Explications</span>
                <span style="font-size: 10px; margin-left: 4px;">▼</span>
            </summary>
            <div style="position: absolute; left: 0; top: 35px; background-color: white; border: 1px solid #d3d3d3; padding: 14px; border-radius: 6px; width: 280px; box-shadow: 0px 4px 12px rgba(0,0,0,0.15); z-index: 99999; font-size: 13px; line-height: 1.5; color: #31333F; cursor: default;">
                Pour protéger la base principale (<strong>10 500 lignes</strong>), les modifications (prix, images, produits) sont envoyées dans un onglet secondaire. Le bouton permet à l'administrateur, de les valider.
            </div>
        </details>
    </div>
    """,
    unsafe_allow_html=True
)

code_upc = "code_upc"
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
    .stLinkButton button, .stLinkButton a, .stLinkButton span, .stLinkButton p {
        background-color: #ff3b30 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        padding: 12px 24px !important;
    }
    .stLinkButton button:hover, .stLinkButton a:hover, .stLinkButton button:hover span {
        background-color: #e0241b !important;
        color: white !important;
    }
    div[data-testid="stColumns"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 10px !important; }
    div[data-testid="column"] { flex: 1 1 calc(33.333% - 10px) !important; min-width: calc(33.333% - 10px) !important; max-width: calc(33.333% - 10px) !important; }
    [data-testid="stExpanderDetails"] summary span, [data-testid="stExpanderDetails"] details summary, .stExpander details summary span {
        font-size: 26px !important; font-weight: bold !important; color: #003366 !important;
    }
</style>
""")
def sauvegarder_historique(df_histoire):
    """Enregistre l'historique des modifications dans l'onglet 'Historique_Prix'."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            df_existant = conn.read(worksheet="Historique_Prix", ttl=0)
        except Exception:
            df_existant = pd.DataFrame(columns=['horodatage', 'code_upc', 'distribution', 'prix', 'source', 'photo'])
        
        df_total = pd.concat([df_existant, df_histoire], ignore_index=True)
        conn.update(worksheet="Historique_Prix", data=df_total)
    except Exception as e:
        st.error(f"⚠️ Impossible de mettre à jour l'historique cloud : {e}")
def charger_donnees():
    """Se connecte au Google Sheet principal."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_initial = conn.read(worksheet="Sheet1", ttl="5m")
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
            # 1. On convertit d'abord en texte brut propre pour l'analyse
            df_initial['entreprise_province_etat'] = df_initial['entreprise_province_etat'].astype(str).str.strip()

            # 2. Détection élargie : cherche "quebec", "qc", "Qc", ou n'importe quel texte contenant ",QC" ou ",Qc"
            mask_quebec = (
                df_initial['entreprise_province_etat'].str.lower().str.contains('québec|quebec', na=False) |
                df_initial['entreprise_province_etat'].str.lower().str.contains(r'\bqc\b', na=False) |
                df_initial['entreprise_province_etat'].str.lower().str.contains(r',\s*qc', na=False)
            )
            
            # On force l'harmonisation pour toutes les lignes détectées comme étant au Québec
            df_initial.loc[mask_quebec, 'entreprise_province_etat'] = 'Québec'
            df_initial.loc[mask_quebec, 'entreprise_pays'] = 'Canada'

            # 3. Nettoyage final pour TOUTES les autres provinces (fusionne "ontario" -> "Ontario")
            df_initial['entreprise_province_etat'] = df_initial['entreprise_province_etat'].str.title()
            df_initial['entreprise_pays'] = df_initial['entreprise_pays'].astype(str).str.strip().str.title()

            # 4. Correction rapide des fautes de frappes et formats restants
            df_initial['entreprise_province_etat'] = df_initial['entreprise_province_etat'].replace({
                'Ontatio': 'Ontario',
                'Etobicoke, Ontario': 'Ontario',
                'Nouveau-Brunswick': 'Nouveau Brunswick',
                'Colombie Britanique': 'Colombie-Britannique'
            })



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
    "Fruits et Légumes": ["Toutes les sous-catégories", "Fruits frais (petits fruits, agrumes, pommes, poires)", "Légumes frais (légumes-feuilles, racines, fines herbes)", "Prêts-à-manger (plateaux de fruits ou légumes coupés)"],
    "Viandes et Volailles": ["Toutes les sous-catégories", "Bœuf, porc, veau et agneau (haché, rôtis, steaks)", "Volaille (poulet, dindon, poitrines, cuisses)", "Charcuterie et saucisses (jambon, bacon, viandes froides)"],
    "Poissons et Fruits de mer": ["Toutes les sous-catégories", "Poissons frais and congelés (saumon, truite, morue)", "Fruits de mer (crevettes, pétoncles, moules, homard)", "Produits fumés ou transformés (saumon fumé, surimi)"],
    "Produits laitiers et Œufs": ["Toutes les sous-catégories", "Laits et crèmes (lait de vache, crèmes à cuisson/café)", "Fromages (fins du Québec, cheddar, mozzarella, crème)", "Yogourts et desserts laitiers (grecs, poudings, kéfir)", "Œufs et succédanés (blancs, bruns, oméga-3, liquides)", "Beurre et margarines (salé/non salé, tartinades)"],
    "Boulangerie et Pâtisserie": ["Toutes les sous-catégories", "Pains de table (pains tranchés, pains miche, artisanaux)", "Pains plats (tortillas, pitas, pains Naan)", "Boulangerie déjeuner (bagels, muffins, croissants, brioches)", "Pâtisseries et desserts (gâteaux, tartes, biscuits frais)"],
    "Épicerie salée et Garde-manger": ["Toutes les sous-catégories", "Pâtes, riz et grains (pâtes, riz blanc/brun, quinoa, couscous)", "Huiles, vinaigres et condiments (huile, vinaigre, mayo, ketchup)", "Sauces et vinaigrettes (sauces à pâtes, sauces BBQ, vinaigrettes)", "Conserves et soupes (légumes en conserve, thon, soupes, bouillons)", "Ingrédients de cuisson (farine, sucre, poudres à lever, pépites)"],
    "Déjeuner et Collations": ["Toutes les sous-catégories", "Céréales et gruaux (céréales pour enfants, granolas, gruau)", "Tartinades (confitures, beurre d'arachide, miel, sirop d'érable)", "Collations salées (croustilles, bretzels, craquelins, maïs soufflé)", "Collations sucrées et confiseries (biscuits emballés, barres, bonbons)", "Noix et graines (arachides, amandes, graines de tournesol)"],
    "Aliments surgelés": ["Toutes les sous-catégories", "Plats cuisinés (pizzas, lasagnes, repas individuels)", "Viandes et poissons surgelés (pépites, burgers, filets panés)", "Fruits et légumes surgelés (mélanges de légumes, frites)", "Crème glacée et desserts surgelés (en pot, barres, gâteaux)"],
    "Boissons (non alcoolisées)": ["Toutes les sous-catégories", "Boissons gazeuses et eaux (colas, eaux pétillantes, de source)", "Jus et nectars (jus d'orange, jus de pomme, boissons aux fruits)", "Café, thé et tisanes (en grains ou moulu, capsules, sachets)", "Boissons végétales (lait d'amande, de soya, d'avoine)"],
    "Bières et Vins (Alcools)": ["Toutes les sous-catégories", "Bières (microbrasseries québécoises, commerciales, cidres)", "Vins (vins rouges, blancs et rosés d'épicerie)"]
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

    if any(m in nom for m in fruits_mots): return ("Fruits et Légumes", "Fruits frais (petits fruits, agrumes, pommes, poires)")
    legumes_mots = ["carotte", "legume", "epinard", "poivron", "ail", "oignon", "salade", "concombre", "chou", "betterave", "patate douce"]
    if any(m in nom for m in legumes_mots): return ("Fruits et Légumes", "Légumes frais (légumes-feuilles, racines, fines herbes)")

    return ("Épicerie salée et Garde-manger", "Toutes les sous-catégories")
if 'df_produits' not in st.session_state:
    st.session_state['df_produits'] = charger_donnees()

df = st.session_state['df_produits']

if 'banniere_active' not in st.session_state:
    st.session_state['banniere_active'] = "Tous"

st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 22px; margin-bottom: 15px;'>🌐 Filtrer les produits par pays d'origine</h2>")

if 'entreprise_pays' in df.columns:
    liste_pays = ["Tous"] + sorted([str(p).strip() for p in df['entreprise_pays'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_pays = st.sidebar.selectbox("Filtrer par pays propriétaire :", liste_pays)
    df_filtre = df[df['entreprise_pays'] == choix_pays] if choix_pays != "Tous" else df.copy()
else:
    df_filtre = df.copy()

if 'entreprise_province_etat' in df_filtre.columns:
    liste_prov = ["Toutes"] + sorted([str(p).strip() for p in df_filtre['entreprise_province_etat'].unique() if pd.notna(p) and str(p).strip() != "" and str(p).lower() != "nan"])
    choix_prov = st.sidebar.selectbox("Filtrer par province ou état :", liste_prov)
    if choix_prov != "Toutes":
        df_filtre = df_filtre[df_filtre['entreprise_province_etat'] == choix_prov]

st.sidebar.markdown("---")
st.sidebar.markdown("<style>[data-testid='stSidebar'] label p { font-size: 16px !important; font-weight: bold !important; color: #1E3A8A !important; }</style>", unsafe_allow_html=True)

categorie_choisie = st.sidebar.selectbox("Filtrer par catégorie d'aliments :", options=list(CATEGORIES_PROJET.keys()), index=0)
sous_cat_disponibles = CATEGORIES_PROJET[categorie_choisie]
sous_categorie_choisie = st.sidebar.selectbox("Filtrer par sous-catégorie :", options=sous_cat_disponibles, index=0)
with open("logo_quebec.png", "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode()

logo_html = f'<img src="data:image/png;base64,{encoded_string}" style="height: clamp(30px, 5vw, 46px); width: auto; flex-shrink: 0;" />'

st.html(f"""
<div style="display: flex; align-items: center; justify-content: center; gap: clamp(8px, 2vw, 15px); margin-bottom: 20px; width: 100%; text-align: center;">
    {logo_html}
    <h1 style="color: #003366; font-family: sans-serif; font-size: clamp(1.3rem, 4.5vw, 2.5rem); margin: 0; padding: 0; line-height: 1.2;">MON GUIDE D'ACHAT LOCAL</h1>
    <span style="font-size: clamp(1.3rem, 4.5vw, 2.5rem); flex-shrink: 0;">🍁</span>
</div>
""")

st.html("""
    <a href="https://streamlit.app" target="_blank" style="text-decoration: none; width: 100%; display: block;">
        <div style="background-color: #FF3B30; color: white; text-align: center; padding: 18px 20px; border-radius: 12px; font-family: sans-serif; line-height: 1.6; box-shadow: 0px 4px 10px rgba(0,0,0,0.15); transition: transform 0.2s ease;">
            <div style="font-size: 20px; font-weight: bold; margin-bottom: 6px;">🛒 Votre panier au plus bas, en direct de vos commerces locaux</div>
            <div style="font-size: 15px; opacity: 0.90; font-weight: 500;">Ouvrir le Planificateur de Budget (circulaires & calcul du panier) ➔</div>
        </div>
    </a>
""")

st.html("<div style='text-align: center; margin-top: 25px; margin-bottom: 25px;'><p style='font-size: 22px; font-weight: bold; color: #2e7d32;'>🔍 Recherchez l'origine d'un produit parmi plus de 10 500 articles !</p></div>")
st.markdown("### 🛒 Sélectionnez votre supermarché habituel :")
st.html("""
    <style>
    [data-testid="stHorizontalBlock"] .stButton button { max-width: 180px !important; margin: 0 auto !important; display: block !important; }
    @media (max-width: 640px) {
        [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 10px !important; }
        [data-testid="stColumn"] { width: 100% !important; flex: 1 1 0% !important; min-width: 0px !important; }
    }
    </style>
""")

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
resultats, message_erreur_recherche = None, None

if "saisie_manuelle" not in st.session_state:
    st.session_state["saisie_manuelle"] = ""

choix_mode = st.radio(
    "👉 Mode de recherche :", 
    ["manuel", "scan"], 
    horizontal=True, 
    label_visibility="collapsed",
    format_func=lambda x: "⌨️ Recherche manuelle ou" if x == "manuel" else "📸 Scanner un code-barres"
)

saisie_net = "" 
if "cup" in st.query_params: 
    saisie_net = str(st.query_params["cup"]).strip()
    st.session_state["saisie_manuelle"] = saisie_net

if choix_mode == "manuel": 
    if "cup_scanne" in st.session_state: 
        st.session_state["cup_scanne"] = ""
    saisie = st.text_input("👉 Saisissez un nom de produit ou un code UPC :", value=st.session_state["saisie_manuelle"], key="recherche_cup") 
    st.session_state["saisie_manuelle"] = saisie.strip()
    saisie_net = st.session_state["saisie_manuelle"]
    if saisie_net and "cup" in st.query_params: 
        st.query_params.clear() 
elif choix_mode == "scan": 
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
if saisie_net and saisie_net.strip() not in ["", "****"]:
    cup_saisi = str(saisie_net).strip()
    
    def enlever_accents(texte):
        t = str(texte).lower()
        remplacements = {"é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "ù": "u", "û": "u", "î": "i", "ï": "i", "ô": "o", "ç": "c"}
        for accent, lettre in remplacements.items(): t = t.replace(accent, lettre)
        return t

    if 'code_upc' in df.columns:
        cup_avec_zero = cup_saisi if cup_saisi.startswith('0') else '0' + cup_saisi
        cup_sans_zero = cup_saisi.lstrip('0')
        recherche_cup = df[df['code_upc'].astype(str).str.strip() == cup_sans_zero]
        if recherche_cup.empty:
            recherche_cup = df[df['code_upc'].astype(str).str.strip() == cup_avec_zero]
            
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
                if len(recherche_texte) == 1: resultats = recherche_texte
            else: 
                message_erreur_recherche = f"⚠️ Aucun produit trouvé."
                df_filtre = pd.DataFrame(columns=df.columns)

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

for c in df_affichage.columns: df_affichage[c] = df_affichage[c].astype(str).replace('nan', '')
df_affichage = df_affichage.reset_index(drop=True)
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
            st.cache_data.clear()
            st.success("Produit supprimé !"), time.sleep(1), st.rerun()
def dms_a_decimal_sidebar(coord_str, est_longitude=False):
    try:
        if pd.isna(coord_str): return None
        chiffres = [float(x) for x in re.findall(r"\d+", str(coord_str))]
        if len(chiffres) >= 3:
            degres, minutes, secondes = chiffres[0], chiffres[1], chiffres[2]
            decimal = degres + (minutes / 60.0) + (secondes / 3600.0)
            if est_longitude: decimal = -decimal
            return decimal
    except Exception: return None
    return None

@st.cache_data
def charger_villes_sidebar():
    try: df_muni = pd.read_csv("municipalités.csv", sep=";", encoding="utf-8")
    except FileNotFoundError:
        try: df_muni = pd.read_csv("municipalites.csv", sep=";", encoding="utf-8")
        except FileNotFoundError: df_muni = pd.read_csv("municipalites.csv", sep=";", encoding="latin-1")
    except Exception: df_muni = pd.read_csv("municipalités.csv", sep=";", encoding="latin-1")
    return df_muni

try:
    df_villes = charger_villes_sidebar()
    df_villes.columns = df_villes.columns.str.strip()
    liste_villes_quebec = sorted(df_villes["Nom de la municipalité"].dropna().unique())
    st.sidebar.markdown("---")
    st.sidebar.html("<h2 style='color: #003366; font-family: sans-serif; font-size: 20px; font-weight: bold;'>🗺️ Épiceries à proximité</h2>")
    st.sidebar.write("Affichez instantanément les supermarchés de votre région :")
    ville_choisie = st.sidebar.selectbox("Sélectionnez votre municipalité :", options=liste_villes_quebec, key="cle_sidebar_municipalite_choisie")

    if ville_choisie:
        infos_commune = df_villes[df_villes["Nom de la municipalité"] == ville_choisie].iloc[0]
        lat = dms_a_decimal_sidebar(infos_commune["Latitude"], est_longitude=False)
        lon = dms_a_decimal_sidebar(infos_commune["Longitude"], est_longitude=True)
        if lat and lon:
            terme_recherche = urllib.parse.quote("épiceries")
            lien_maps = f"https://google.com{terme_recherche}/@{lat},{lon},13z"
            st.sidebar.link_button(f"🚀 Ouvrir Google Maps", lien_maps, use_container_width=True)
        else: st.sidebar.error("Impossible de charger les coordonnées de cette ville.")
except Exception as erreur_carte:
    st.sidebar.warning(f"Le module de recherche géographique est indisponible.")

st.sidebar.markdown("---")
with st.sidebar.expander("⚖️ Mentions légales & Transparence"):
    st.markdown("""
    **Avis de non-responsabilité**
    **Cette application** est une initiative citoyenne bénévole, indépendante et sans but lucratif destinée à soutenir les consommateurs québécois.
• **Propriété des marques et des images** : Les marques de commerce, logos, noms de produits et images présentés dans cette application sont la propriété exclusive de leurs détenteurs respectifs. Leur affichage est fait à des fins purement descriptives, informatives et d'évaluation, sans aucune intention de contrefaçon ni d'association commerciale avec les marques citées.
• **Exactitude des informations** : Les données sur les produits (ingrédients, valeurs nutritionnelles, visuels) proviennent de contributions citoyennes ou de bases de données ouvertes. Bien que nous fermions des efforts pour assurer leur exactitude, nous ne pouvons en garantir l'actualisation en temps réel. Les consommateurs sont invités à toujours vérifier l'emballage réel du produit en magasin..
    """)
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
        height=300, 
        key="tableau_consommateur"
    )

    if selection_tableau and "rows" in selection_tableau["selection"] and selection_tableau["selection"]["rows"] and 'code_upc' in df_affichage.columns:
        index_ligne_cliquee = selection_tableau["selection"]["rows"][0]  # <-- Correction ici avec le [0]
        if index_ligne_cliquee < len(df_affichage):
            cup_selectionne = str(df_affichage.iloc[index_ligne_cliquee]['code_upc']).strip()
            resultats = df[df['code_upc'] == cup_selectionne]

image_cam = None
cup_actif = ""
if resultats is not None and not resultats.empty:
    cup_actif = str(resultats.iloc[0].get('code_upc', '')).strip() # <-- Ajout du .iloc[0] de sécurité
elif saisie_net and saisie_net.strip() not in ["", "****"]:
    cup_actif = saisie_net.strip()

if cup_actif and cup_actif != "nan":
    st.markdown(f"#### 📸 Ajouter ou remplacer la photo de ce produit (UPC: {cup_actif})")
    image_cam = st.camera_input("Prenez le produit en photo (Face avant bien visible)", key=f"cam_globale_{cup_actif}")

if image_cam:
    try:
        with st.spinner("Envoi et sauvegarde définitive de la photo sur GitHub..."):
            nom_fichier_image = f"{cup_actif}.jpg"
            img = Image.open(image_cam)
            img.thumbnail((800, 800))
            tampon_memoire = io.BytesIO()
            img.save(tampon_memoire, format="JPEG", quality=70, optimize=True)
            contenu_image = tampon_memoire.getvalue()
            
            UTILISATEUR_GH = "abgithub2018"
            DEPOT_GH = "guide-achat-local"
            TOKEN_GH = st.secrets["GITHUB_TOKEN"]
            
            url_api_github = f"https://github.com{UTILISATEUR_GH}/{DEPOT_GH}/contents/images_stockees/{nom_fichier_image}"
            headers_gh = {"Authorization": f"token {TOKEN_GH}", "Accept": "application/vnd.github.v3+json"}
            
            reponse_get = requests.get(url_api_github, headers=headers_gh)
            sha_fichier = None
            if reponse_get.status_code == 200: sha_fichier = reponse_get.json().get("sha")
            
            image_base64 = base64.b64encode(contenu_image).decode("utf-8")
            donnees_envoi = {"message": f"📷 Ajout de la photo pour le produit {cup_actif} via mobile", "content": image_base64}
            if sha_fichier: donnees_envoi["sha"] = sha_fichier
            
            envoi_gh = requests.put(url_api_github, headers=headers_gh, json=donnees_envoi)
            if envoi_gh.status_code != 200 and envoi_gh.status_code != 201: raise Exception(f"GitHub a répondu avec le code {envoi_gh.status_code}")

            horodatage_actuel = pd.Timestamp.now(tz='America/Toronto').tz_localize(None).strftime("%Y-%m-%d %H:%M")
            lien_public_github = f"https://githubusercontent.com{UTILISATEUR_GH}/{DEPOT_GH}/main/images_stockees/{nom_fichier_image}"
            
            ligne_photo_h = pd.DataFrame([{
                'horodatage': horodatage_actuel,
                'code_upc': str(cup_actif).strip(),
                'distribution': '',
                'prix': '',
                'source': 'modification_photo_cell',
                'photo': lien_public_github
            }])
            sauvegarder_historique(ligne_photo_h)
            
            for key in list(st.session_state.keys()):
                if "cam" in key or "photo" in key:
                    try: del st.session_state[key]
                    except KeyError: pass

            st.success("🎉 Succès ! La photo a été enregistrée dans l'historique Sheets pour validation.")
            time.sleep(1.5)
            st.rerun()
    except Exception as e: st.error(f"Erreur lors de la sauvegarde sur GitHub : {e}")

st.markdown("---")

if resultats is None or resultats.empty:
    if message_erreur_recherche: st.warning(message_erreur_recherche)
    type_saisie = "Le code-barres" if (saisie_net and saisie_net.isdigit()) else "Le produit"
    st.info(f"📦 {type_saisie} **{saisie_net}** semble être un nouveau produit pas encore répertorié.")

    with open("drapeau_qc.png", "rb") as f: img_data = base64.b64encode(f.read()).decode("utf-8")
    st.html(f"<p style='font-family: sans-serif; font-size: 19px; margin: 0;'>Devenez le premier à l'ajouter pour la communauté Achat Québec ! <img src='data:image/png;base64,{img_data}' style='height: 46px; width: auto; vertical-align: middle; margin-left: 5px; border: 1px solid #e0e0e0; border-radius: 2px; display: inline-block;'></p>")
    
    with st.form(key="formulaire_nouveau_produit", clear_on_submit=True):
        nom_nouveau = st.text_input("Nom exact du produit (ex: Fraises du Québec 1L)")
        cup_final = st.text_input("code_upc", value=saisie_net.strip() if saisie_net else "", disabled=True)
        entreprise = st.text_input("Entreprise propriétaire / Marque (ex: Agropur)")
        province = st.text_input("Province / État (ex: Québec)")
        pays = st.text_input("Pays", value="Canada")
        distribution = st.text_input("Réseau d'épicerie (ex: IGA, Maxi, Metro, Super C)")
        
        st.write("---")
        st.write("**Entrez les prix constatés en magasin (optionnel) :**")
        col1, col2, col3 = st.columns(3)
        with col1: prix_iga = st.text_input("Prix IGA ($)", value="")
        with col2: prix_maxi = st.text_input("Prix Maxi ($)", value="")
        with col3: prix_metro = st.text_input("Prix Metro ($)", value="")
        col4, col5, col6 = st.columns(3)
        with col4: prix_superc = st.text_input("Prix Super C ($)", value="")
        with col5: prix_walmart = st.text_input("Prix Walmart ($)", value="")
        with col6: prix_tigre = st.text_input("Prix Tigre Géant ($)", value="")
        col7, col8 = st.columns(2)
        with col7: prix_dollarama = st.text_input("Prix Dollarama ($)", value="")
        with col8: prix_provigo = st.text_input("Prix Provigo ($)", value="")

        bouton_creer = st.form_submit_button("🚀 Envoyer la proposition de nouveau produit", type="primary", use_container_width=True)

        if bouton_creer:
            if nom_nouveau:
                with st.spinner("Envoi de votre proposition au modérateur..."):
                    try:
                        horodatage_actuel = pd.Timestamp.now(tz='America/Toronto').tz_localize(None).strftime("%Y-%m-%d %H:%M")
                        infos_compil = f"PROPOSITION_NOUVEAU: {nom_nouveau.strip()} | Marque: {entreprise.strip()} | Province: {province.strip()} | Pays: {pays.strip()}"
                        premier_prix = prix_iga.strip() or prix_maxi.strip() or prix_metro.strip() or prix_superc.strip() or "0"
                        
                        ligne_creation_h = pd.DataFrame([{
                            'horodatage': horodatage_actuel,
                            'code_upc': str(cup_final).strip(),
                            'distribution': distribution.strip() or 'Multi',
                            'prix': premier_prix,
                            'source': infos_compil,
                            'photo': ''
                        }])
                        
                        sauvegarder_historique(ligne_creation_h)
                        st.success("🎉 **Merci !** Votre proposition a été envoyée à notre file de modération bénévole. Elle sera ajoutée au catalogue après vérification par l'administrateur.")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e: st.error(f"Erreur d'envoi : {e}")
            else: st.error("⚠️ Le Nom du produit est obligatoire.")
if resultats is not None and not resultats.empty:
    index_produit_reel = resultats.index[0]  # <-- Correction ici avec .index[0]
    row = resultats.iloc[0]                  # <-- Correction ici avec .iloc[0]

    prov = str(row.get('entreprise_province_etat', '')).strip().replace('nan', '')
    pays = str(row.get('entreprise_pays', '')).strip().replace('nan', '')
    compagnie = str(row.get('entreprise_proprietaire', '')).strip().replace('nan', '')
    localisation_siege = f"{prov}" + (f" ({pays})" if pays else "") if prov else pays or "Non spécifié"

    if "québec" in prov.lower():
        import base64
        import os

        # 1. Extraction robuste par code UPC (Gestion du format texte brut et numérique)
        chiffre_nettoye = 0
        try:
            valeur_brute = None
            
            # Recherche dans le tableau principal 'df'
            if 'df' in locals() and 'code_upc' in df.columns and 'emplois_quebec' in df.columns and 'code_upc' in locals():
                # On nettoie le code_upc recherché pour enlever les décimales s'il a été lu comme un nombre (ex: 59749979573.0 -> 59749979573)
                upc_recherche = str(code_upc).split('.')[0].strip()
                
                # On compare les deux colonnes converties textuellement et nettoyées
                ligne_produit = df[df['code_upc'].astype(str).str.split('.').str[0].str.strip() == upc_recherche]
                
                if not ligne_produit.empty:
                    valeur_brute = ligne_produit['emplois_quebec'].values[0]

            # Sécurités de secours si la variable est déjà présente dans la mémoire de la ligne
            if valeur_brute is None:
                if 'row' in locals() and 'emplois_quebec' in row:
                    valeur_brute = row['emplois_quebec']
                elif 'produit' in locals() and 'emplois_quebec' in produit:
                    valeur_brute = produit['emplois_quebec']

            # Extraction et nettoyage final du nombre d'emplois (colonne Z)
            if valeur_brute is not None and str(valeur_brute).strip() != "" and str(valeur_brute).lower() != "nan":
                texte_brut = str(valeur_brute).replace(" ", "").replace("\xa0", "").replace("\u202f", "")
                chiffre_nettoye = int(float(texte_brut))
        except Exception:
            chiffre_nettoye = 0

        # 2. Encodage de votre fleur de lys transparente (Base64)
        chemin_img = "images_stockees/logo_quebec.png"
        src_image = ""
        if os.path.exists(chemin_img):
            with open(chemin_img, "rb") as f:
                data_base64 = base64.b64encode(f.read()).decode("utf-8")
                src_image = f"data:image/png;base64,{data_base64}"
        else:
            src_image = "https://githubusercontent.com"

        couleur_boite, couleur_texte, badge_html = "#e1f5fe", "#0d47a1", f"""<span style="display: inline-flex; align-items: center; background-color: #0d47a1; color: #ffffff; padding: 12px 24px; border-radius: 50px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-weight: bold; font-size: 18px; letter-spacing: 0.5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"><div style="width: 54px; height: 32px; display: inline-flex; align-items: center; margin-right: 14px;"><img src="{src_image}" style="height: 100%; width: auto; display: block;" alt="⚜"></div>Emploi au Québec Confirmé</span>"""
        
        # 3. Verdict
        if chiffre_nettoye > 0:
            format_emplois = f"{chiffre_nettoye:,}".replace(",", " ")
            verdict = f"Ce produit est fabriqué dans une usine locale générant aussi environ <b>{format_emplois}</b> emplois directs au Québec."
        else:
            verdict = "Ce produit est fabriqué dans une usine locale au Québec."


    elif "canada" in pays.lower() or "canada" in prov.lower():
        couleur_boite, couleur_texte, badge_html = "#e8f5e9", "#1b5e20", '<span style="background-color: #1b5e20; color: white; padding: 4px 10px; border-radius: 4px;">Canada</span>'
        verdict = "Ce produit encourage l'économie canadienne."
        
    else:
        couleur_boite, couleur_texte, badge_html = "#f5f5f5", "#424242", '<span style="background-color: #757575; color: white; padding: 4px 10px; border-radius: 4px;">Autre</span>'
        verdict = "Les profits de ce produit quittent le pays."



    bannières_config = {
        'prix_iga': ('🔴 IGA', '#d32f2f'), 'prix_maxi': ('🟡 MAXI', '#f9d71c'), 'prix_metro': ('🟢 METRO', '#28a745'), 'prix_super_c': ('🔵 SUPER C', '#0056b3'),
        'prix_walmart': ('🔵 WALMART', '#0071dc'), 'prix_tigre_geant': ('🐯 TIGRE GÉANT', '#ffcc00'), 'prix_dollarama': ('💵 DOLLARAMA', '#00843d'), 'prix_provigo': ('🟢 PROVIGO', '#ff5a00')
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
        
        texte_barre = "💾 Envoyer la mise à jour des prix"
        if "dernier_horodatage" in st.session_state:
            texte_barre = f"💾 Envoyer la mise à jour des prix (Fait le : {st.session_state['dernier_horodatage']})"
        bouton_enregistrer = st.form_submit_button(texte_barre, use_container_width=True)
        
    if bouton_enregistrer:
        try:
            with st.spinner("Envoi des prix suggérés pour validation..."):
                horodatage_actuel = pd.Timestamp.now(tz='America/Toronto').tz_localize(None).strftime("%Y-%m-%d %H:%M")
                nouvelles_lignes = []
                upc_produit = str(row.get('code_upc', '')).strip()
                champs_saisis = {
                    'prix_iga': nouveau_iga, 
                    'prix_maxi': nouveau_maxi, 
                    'prix_metro': nouveau_metro, 
                    'prix_super_c': nouveau_super_c,  # <-- Remettez les deux tirets ici !
                    'prix_walmart': nouveau_walmart, 
                    'prix_tigre_geant': nouveau_tigre, 
                    'prix_dollarama': nouveau_dollarama, 
                    'prix_provigo': nouveau_provigo
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
                                'source': 'PROPOSITION_PRIX',
                                'photo': ''
                            }
                            nouvelles_lignes.append(nouvelle_ligne)
                        except ValueError: pass

                if nouvelles_lignes:
                    df_nouvel_historique = pd.DataFrame(nouvelles_lignes)
                    sauvegarder_historique(df_nouvel_historique)
                    
                st.session_state['dernier_horodatage'] = horodatage_actuel
                st.success("👍 **Proposition enregistrée !** Les prix ont été envoyés pour vérification. Ils seront mis à jour publiquement dès que l'administrateur aura le temps de les valider.")
                time.sleep(1.5)
                st.rerun()
        except Exception as e: st.error(f"❌ Erreur lors de l'envoi : {e}")

banniere_a_afficher = st.session_state.get('banniere_active', 'Tous')
st.caption(f"Filtre d'affichage actif : Enseigne sélectionnée -> **{banniere_a_afficher.upper()}**")
