import streamlit as st
import pandas as pd

# 1. Configuration de l'interface
st.set_page_config(page_title="Recherche Commerces", layout="wide")
st.title("🍎 Recherche de commerces d'alimentation au Québec")

# 2. Chargement direct du fichier local
@st.cache_data
def load_data():
    try:
        # Lecture directe du fichier présent dans votre dossier
        df = pd.read_csv("disponibilite_magasins.csv")
        # Nettoyage des espaces et mise en majuscules pour éviter les erreurs de frappe
        if 'Code_Postal' in df.columns:
            df['Code_Postal'] = df['Code_Postal'].astype(str).str.replace(" ", "").str.upper()
        return df
    except Exception as e:
        st.error(f"Impossible de lire le fichier csv local : {e}")
        return pd.DataFrame()

df_magasins = load_data()

# 3. Formulaire de recherche dans la barre latérale
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G5Y 1V3)", "").replace(" ", "").upper()

# 4. Filtrage et affichage instantané
if user_postal:
    if len(user_postal) >= 3:
        # Extraction des 3 premiers caractères (la RTA, ex: G5Y)
        rta_utilisateur = user_postal[:3]
        
        # Recherche directe des commerces partageant la même zone de code postal
        df_resultats = df_magasins[df_magasins['Code_Postal'].str.startswith(rta_utilisateur, na=False)].copy()
        
        if not df_resultats.empty:
            st.success(f"🎉 {len(df_resultats)} commerces trouvés dans la zone {rta_utilisateur} !")
            
            # Affichage du tableau avec vos colonnes exactes
            colonnes_visibles = ['Nom_Commerce', 'Adresse_Rue', 'Municipalite', 'Code_Postal']
            st.dataframe(df_resultats[[c for c in colonnes_visibles if c in df_resultats.columns]], use_container_width=True)
        else:
            st.warning(f"Aucun commerce trouvé dans la zone {rta_utilisateur} dans votre fichier.")
    else:
        st.error("Le code postal doit contenir au moins 3 caractères.")
else:
    st.info("💡 Entrez un code postal dans la barre latérale pour afficher les commerces correspondants.")
