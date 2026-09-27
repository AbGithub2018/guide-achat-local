import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité Grand Québec", layout="centered")
st.title("🇨🇦 Liste des Fleurons Québécois (Avec Coaticook)")
st.write("Ce script intègre Québon et la crème glacée Coaticook tout en excluant Lactantia.")

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

# Aliments de base, spécialités locales et desserts glacés du Québec
aliments = [
    "lait", "pain", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", 
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue",
    "porc", "saucisse", "bacon", "jambon", "fromage", "crotte", "skouik",
    "yogourt", "creme", "erable", "pomme", "bleuet", "fraise", "framboise",
    "tomate", "concombre", "creton", "biscuit", "jus", "pates", "spaghetti",
    "vinaigrette", "sauce", "glace", "creme glacee"
]

# Vos entreprises d'ici (Québon et Coaticook bien verrouillés)
marques_quebecoises = [
    "leclerc", "agropur", "lassonde", "oasis", "nutri", "nutrilait", 
    "boivin", "st-methode", "st methode", "catelli", "natrel", "exceldor", 
    "saputo", "multi vert", "multivert", "lesters", "olymel", "quebon", 
    "riviera", "le grec", "lafleur", "tour eiffel", "irresistibles", 
    "selection", "compliments", "bens original", "bistro express", "nutrinor",
    "coaticook"  # 🟢 Ajout de la laiterie Coaticook
]

# Exclusions strictes : USA, marques canadiennes hors-Québec ET Lactantia
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name",
    "lactantia"
]

# 3. Bouton de filtrage québécois
if st.button("🚀 Mettre à jour la liste avec Coaticook dans le Nuage", type="primary"):
    with st.spinner("Analyse et marquage de vos fleurons québécois..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : On cherche les aliments ciblés
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        
        # Étape C : On cherche vos marques québécoises
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        
        # Étape D : On identifie les produits à bannir
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        # COMBINAISON : L'aliment doit appartenir à vos marques québécoises ET ne pas être exclu
        masque_final = (masque_aliments & masque_marques) & ~masque_hors_qc
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_final = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Filtrage réussi ! La liste inclut maintenant la crème glacée Coaticook et le lait Québon.")
            
            # Aperçu du catalogue épuré à l'écran
            st.markdown("### 📋 Aperçu de vos produits prioritaires 100% Québec :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")
