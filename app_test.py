import streamlit as st
import pandas as pd

# Configuration de la page en mode large
st.set_page_config(page_title="Recherche Codes Postaux QC", layout="wide")

st.title("🇨🇦 Moteur de Recherche - Codes Postaux Québec")
st.write("Ce prototype utilise les données géographiques nettoyées de GeoNames.")

# 1. Chargement des données avec mise en cache
@st.cache_data
def load_data():
    # MODIFICATION ICI : Utilisation du nom exact de votre fichier
    df = pd.read_csv("code_qc.csv")
    return df

try:
    df = load_data()

    # 2. Barre de recherche interactive
    search_query = st.text_input("Rechercher par Code Postal (ex: G5Y) ou par Ville (ex: Saint-Georges) :", "").strip()

    # Application de la recherche dynamique
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["Code postal"].str.contains(search_query, case=False, na=False) |
            filtered_df["Ville"].str.contains(search_query, case=False, na=False)
        ]

    # 3. Affichage du tableau de résultats
    st.subheader(f"📍 Résultats ({len(filtered_df)} correspondances)")
    st.dataframe(filtered_df, use_container_width=True)

    # 4. Affichage de la carte
    if not filtered_df.empty:
        st.subheader("🗺️ Cartographie des zones trouvées")
        map_data = filtered_df[['Latitude', 'Longitude']].dropna()
        map_data.columns = ['latitude', 'longitude']
        st.map(map_data)
    else:
        st.warning("Aucun résultat ne correspond à votre recherche.")

except FileNotFoundError:
    st.error("Erreur : Le fichier 'code_qc.csv' est introuvable sur votre dépôt GitHub. Vérifiez l'orthographe exacte.")
