import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="🤖 Auto-Priorité Grand Québec", layout="centered")
st.title("🇨🇦 Liste des Fleurons Québécois (Avec Eska et St-Méthode)")
st.write("Ce script intègre l'eau Eska et règle l'affichage de la boulangerie St-Méthode d'Adstock.")

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
    "lait", "pain", "boulangerie", "boulange", "oeuf", "beurre", "riz", "mouchoir", "kleenex", 
    "essuie-tout", "essuietout", "eau", "savon", "patate", "carotte", 
    "arachide", "peanut", "poisson", "saumon", "salade", "laitue",
    "porc", "saucisse", "bacon", "jambon", "fromage", "crotte", "skouik",
    "yogourt", "creme", "erable", "pomme", "bleuet", "fraise", "framboise",
    "tomate", "concombre", "creton", "biscuit", "jus", "pates", "spaghetti",
    "vinaigrette", "sauce", "glace", "creme glacee"
]

# Vos entreprises d'ici (St-Méthode et Eska ajoutés)
marques_quebecoises = [
    "leclerc", "agropur", "lassonde", "oasis", "nutri", "nutrilait", 
    "boivin", "catelli", "natrel", "exceldor", "saputo", "multi vert", 
    "multivert", "lesters", "olymel", "quebon", "riviera", "le grec", 
    "lafleur", "tour eiffel", "irresistibles", "selection", "compliments", 
    "bens original", "bistro express", "nutrinor", "coaticook",
    "st-methode", "st methode", "campagnolo", "les grains", "la recolte",
    "eska"  # 🟢 Ajout de l'eau Eska
]

# Exclusions strictes : USA, hors-Québec, Lactantia
exclusions_hors_quebec = [
    "usa", "u.s.", "united states", "import", "kraft", "kellogg", 
    "campbell", "folgers", "jif", "heinz", "oscar mayer",
    "sans nom", "le choix du president", "pc", "no name",
    "lactantia"
]

# 3. Bouton de filtrage québécois
if st.button("🚀 Re-calculer la liste avec Eska et St-Méthode dans le Nuage", type="primary"):
    with st.spinner("Analyse et inclusion des fleurons..."):
        
        # Étape A : On vide l'ancienne sélection par sécurité
        df['priorite'] = ""
        
        # Étape B : On cherche les aliments ciblés
        masque_aliments = df['nom'].astype(str).str.lower().str.contains("|".join(aliments), na=False)
        
        # Étape C : On cherche vos marques québécoises
        masque_marques = df['nom'].astype(str).str.lower().str.contains("|".join(marques_quebecoises), na=False)
        
        # Étape D : On identifie les produits à bannir (USA, Lactantia...)
        masque_hors_qc = df['nom'].astype(str).str.lower().str.contains("|".join(exclusions_hors_quebec), na=False)
        
        # Étape E : RÈGLE SPÉCIALE D'EXCEPTION POUR ST-MÉTHODE ET ESKA
        # On force l'acceptation pour ces marques québécoises quoi qu'il arrive
        masque_exception_locales = df['nom'].astype(str).str.lower().str.contains("st-methode|st methode|campagnolo|les grains|la recolte|eska", na=False)
        
        # COMBINAISON : L'aliment doit appartenir aux marques québécoises ET ne pas être exclu, SAUF si c'est St-Méthode ou Eska !
        masque_final = (masque_aliments & masque_marques) & (~masque_hors_qc | masque_exception_locales)
        
        # On applique le "Oui"
        df.loc[masque_final, 'priorite'] = "Oui"
        total_final = len(df[df['priorite'] == "Oui"])
        
        try:
            # Envoi automatique vers votre Google Sheets
            conn.update(worksheet="Sheet1", data=df)
            st.cache_data.clear()
            
            st.balloons()
            st.success(f"🎉 Filtrage réussi ! Le robot a trouvé et marqué {total_final} produits 100% Québec (incluant Eska et Boulangerie St-Méthode).")
            
            # Aperçu du catalogue épuré à l'écran
            st.markdown("### 📋 Aperçu de vos produits prioritaires 100% Québec :")
            st.dataframe(df[df['priorite'] == "Oui"][['code_upc', 'nom', 'priorite']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement : {e}")
