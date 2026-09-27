import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité Grand Québec", layout="centered")
st.title("🇨🇦 Aliments et Fleurons du Québec")
st.write("Ce script élargit la sélection aux catégories phares de l'agroalimentaire québécois.")

# 1. Connexion en direct sans cache
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Configuration des filtres élargis 100% Québec
st.markdown("### 🔍 Paramètres du filtre élargi")

# Aliments de base et spécialités locales du Québec
aliments = [
    "lait", "pain", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", 
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue",
    "porc", "saucisse", "bacon", "jambon", "fromage", "crotte", "skouik",
    "yogourt", "creme", "erable", "pomme", "bleuet", "fraise", "framboise",
    "tomate", "concombre", "creton"
]

# Les grands fleurons et distributeurs de chez nous
marques_quebecoises = [
    "quebon", "natrel", "lactantia", "olymel", "exceldor", "st-hubert", 
    "st hubert", "lafleur", "tour eiffel", "irresistibles", "selection", 
    "compliments", "bens original", "bistro express", "nutrinor", "agropur",
    "riviera", "dubreton", "f. menard", "f.menard", "cordon bleu", "clark",
    "ready", "patates dolbec", "savoura"
]

# Exclusions des marques américaines et canadiennes hors-Québec
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name"
]

# 3. Bouton de filtrage québécois
if st.button("🚀 Mettre à jour la grande liste québécoise dans le Nuage", type="primary"):
    with st.spinner("Analyse et sélection exclusive des marques d'ici..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : On cherche les aliments ciblés
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        
        # Étape C : On cherche les marques québécoises
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        
        # Étape D : On identifie les produits hors-Québec à bannir
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        # COMBINAISON : L'aliment doit être d'une marque québécoise ET ne pas faire partie des exclusions
        masque_final = (masque_aliments & masque_marques) & ~masque_hors_qc
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_quebec_large = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Filtrage réussi ! Le robot a maintenant retenu {total_quebec_large} produits fièrement québécois.")
            
            # Aperçu du nouveau catalogue épuré
            st.markdown("### 📋 Aperçu de vos produits 100% Québécois :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")
