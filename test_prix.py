import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité Grand Québec", layout="centered")
st.title("🇨🇦 Règle Absolue : Boulangerie St-Méthode & Eska")
st.write("Ce script force l'inclusion de TOUS les produits St-Méthode et Eska, sans exception.")

# 1. Connexion en direct sans cache
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Configuration des filtres 100% Québec
st.markdown("### 🔍 Paramètres du filtre agroalimentaire")

# Aliments de base et spécialités locales du Québec (Règle générale)
aliments = [
    "lait", "pain", "boulangerie", "boulange", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", 
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue",
    "porc", "saucisse", "bacon", "jambon", "fromage", "crotte", "skouik",
    "yogourt", "creme", "erable", "pomme", "bleuet", "fraise", "framboise",
    "tomate", "concombre", "creton", "biscuit", "jus", "pates", "spaghetti",
    "vinaigrette", "sauce", "glace", "creme glacee"
]

# Vos entreprises d'ici (Règle générale)
marques_quebecoises = [
    "leclerc", "agropur", "lassonde", "oasis", "nutri", "nutrilait", 
    "boivin", "catelli", "natrel", "exceldor", "saputo", "multi vert", 
    "multivert", "lesters", "olymel", "quebon", "riviera", "le grec", 
    "lafleur", "tour eiffel", "irresistibles", "selection", "compliments", 
    "bens original", "bistro express", "nutrinor", "coaticook"
]

# Exclusions strictes : USA, hors-Québec, Lactantia
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name",
    "lactantia"
]

# 3. Bouton de filtrage québécois
if st.button("🚀 Forcer l'inclusion absolue de St-Méthode et Eska", type="primary"):
    with st.spinner("Application des règles absolues sur votre catalogue..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : RÈGLE GÉNÉRALE (Aliment + Marque d'ici, sans exclusion)
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        filtre_general = (masque_aliments & masque_marques) & ~masque_hors_qc
        
        # 🟢 Étape C : LA RÈGLE ABSOLUE IMMUNITAIRE (St-Méthode, Eska et variantes de fautes de frappe)
        # Si la ligne contient une de ces écritures, elle passe DIRECTEMENT à "Oui", peu importe le nom
        mots_absolus = "st-methode|st methode|campagnolo|les grains|la recolte|loulangerie|boulangerie st|eska"
        filtre_absolu = df['nom'].astype(str).str.lower().str.contains(mots_absolus, na=False)
        
        # COMBINAISON : On accepte les produits du filtre général OU de la règle absolue
        masque_final = filtre_general | filtre_absolu
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_final = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Terminé ! Le robot a trouvé et marqué {total_final} produits. Tout St-Méthode et Eska est maintenant inclus d'office.")
            
            # Aperçu du catalogue épuré à l'écran
            st.markdown("### 📋 Aperçu de vos produits prioritaires 100% Québec :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")
