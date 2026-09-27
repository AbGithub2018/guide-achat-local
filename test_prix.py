import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité 100% Québec", layout="centered")
st.title("🇨🇦 Aliments et Marques du Québec")
st.write("Ce script élimine les produits américains et canadiens hors-Québec pour l'achat local.")

# 1. Connexion en direct sans cache
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Sheet1", ttl=0)
    df.columns = [c.strip().lower() for c in df.columns]
    st.success("✅ Connexion à la base de données réussie.")
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# 2. Configuration des filtres (Inclusions strictes Québec vs Exclusions USA/Canada)
st.markdown("### 🔍 Paramètres du filtre Aliments du Québec")

# Aliments de base recherchés
aliments = [
    "lait", "pain", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", 
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue"
]

# Uniquement des fleurons de l'agroalimentaire ou bannières nées au Québec
marques_quebecoises = [
    "quebon", "natrel", "lactantia", "olymel", "exceldor", "st-hubert", 
    "st hubert", "lafleur", "tour eiffel", "irresistibles", "selection", 
    "compliments", "bens original", "bistro express", "nutrinor", "agropur"
]

# Exclusions strictes des USA ET des marques canadiennes hors-Québec (ex: Loblaws Ontario)
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name"
]

# 3. Bouton de filtrage québécois
if st.button("🚀 Filtrer et mettre à jour l'achat québécois dans le Nuage", type="primary"):
    with st.spinner("Analyse et sélection exclusive des marques d'ici..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : On cherche les aliments de base
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        
        # Étape C : On cherche les marques québécoises d'ici
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        
        # Étape D : On identifie les produits USA et canadiens hors-Québec à bannir
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        # COMBINAISON : Il faut que ce soit un aliment ET une marque québécoise, et SURTOUT PAS hors-Québec
        masque_final = (masque_aliments & masque_marques) & ~masque_hors_qc
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_quebec_strict = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Filtrage réussi ! Le robot a retenu {total_quebec_strict} produits fièrement québécois.")
            
            # Aperçu du nouveau catalogue épuré
            st.markdown("### 📋 Aperçu de vos produits 100% Québécois :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")
