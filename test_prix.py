import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Base Officielle Québec", layout="centered")
st.title("🇨🇦 Cartographie Officielle des Aliments du Québec")
st.write("Ce script utilise votre charte officielle pour marquer exclusivement nos fleurons québécois.")

# 1. Connexion en direct sans cache
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Configuration des filtres selon votre charte officielle
st.markdown("### 🔍 Analyseurs du catalogue d'ici")

# Tous les types d'aliments de votre liste
aliments = [
    "lait", "pain", "boulangerie", "boulange", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", "pomme de terre",
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue", "creton",
    "porc", "saucisse", "bacon", "jambon", "fromage", "crotte", "skouik", "volaille", "poulet", "dinde",
    "yogourt", "creme", "erable", "pomme", "bleuet", "fraise", "framboise", "canneberge",
    "tomate", "concombre", "biscuit", "jus", "pates", "spaghetti", "vinaigrette", "sauce", 
    "glace", "creme glacee", "barre", "cereale", "collation", "noix", "graine", "huile", "moutarde", 
    "bouillon", "cidre", "legume", "conserve", "surgele"
]

# TOUTES les marques nationales et sous-marques québécoises de votre charte
marques_quebecoises = [
    # Produits laitiers, fromages et œufs
    "agropur", "natrel", "oka", "iogo", "olympic", "anco",
    "saputo", "armstrong", "alexis de portneuf", "duvillage 1860", "vachon", "dairyland",
    "ferme des voltigeurs", "voltigeurs",
    "nutri", "nutri-oeuf", "oeuf canadien", "seigneurie", "nutrilait", "nutrinor", "boivin", "coaticook",
    # Viandes, charcuteries et prêts-à-manger
    "olymel", "lafleur", "flamingo", "la fernandiere", "fernandiere",
    "dubreton", "exceldor", "lesters", "les aliments ready", "f. menard", "f.menard", "tour eiffel",
    # Épicerie sèche, collations et boulangerie
    "leclerc", "celebration", "praeventia", "go pure",
    "prana", "maison orphee", "orphee", "le grec", "catelli",
    # Boissons, jus et manufacturiers
    "lassonde", "oasis", "rougemont", "allen", "fairlee", "canton", "jus mont-rouge", "mont-rouge",
    # Fruits, légumes, serres et surgelés
    "nortera", "arctic gardens", "fruit d'or", "patience fruit", "patience fruit & co",
    "hydroserre", "gen v", "savoura", "patates dolbec", "dolbec",
    # Marques maison nées au Québec
    "irresistibles", "selection", "compliments"
]

# Exclusions strictes (USA, Canada hors-Québec et multinationales non ciblées)
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name",
    "lactantia"
]

# 3. Bouton de filtrage de votre charte
if st.button("🚀 Lancer le grand marquage officiel du Québec", type="primary"):
    with st.spinner("Application rigoureuse de votre charte québécoise..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : RÈGLE GÉNÉRALE (Aliment + Marques de votre tableau, sans exclusion)
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        filtre_general = (masque_aliments & masque_marques) & ~masque_hors_qc
        
        # 🟢 Étape C : LA RÈGLE ABSOLUE POUR ST-MÉTHODE ET ESKA (Aucun blocage possible)
        mots_absolus = "st-methode|st methode|campagnolo|les grains|la recolte|loulangerie|boulangerie st|eska"
        filtre_absolu = df['nom'].astype(str).str.lower().str.contains(mots_absolus, na=False)
        
        # COMBINAISON FINALE
        masque_final = filtre_general | filtre_absolu
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_final = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Succès retentissant ! Le robot a trouvé et marqué {total_final} produits de votre charte officielle dans votre Google Sheet.")
            
            # Aperçu du catalogue à l'écran
            st.markdown("### 📋 Aperçu de vos nouveaux produits prioritaires 100% Québec :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")

