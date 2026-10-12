import streamlit as st

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Sélectionnez votre région pour ouvrir la carte de vos commerces locaux.")

# 1. Base de données des régions
REGIONS = {
    "Beauce / Saint-Georges": {"lat": 46.116, "lon": -70.672, "zoom": 12},
    "Québec (Ville)": {"lat": 46.813, "lon": -71.207, "zoom": 12},
    "Montréal": {"lat": 45.501, "lon": -73.567, "zoom": 12},
    "Sherbrooke / Estrie": {"lat": 45.401, "lon": -71.892, "zoom": 12},
    "Saguenay / Lac-Saint-Jean": {"lat": 48.428, "lon": -71.062, "zoom": 11}
}

# 2. Menu déroulant Streamlit
region_choisie = st.selectbox("Choisissez une région :", list(REGIONS.keys()))

# 3. Récupération des coordonnées
config = REGIONS[region_choisie]

# 4. Génération du lien Google Maps
lien_maps = f"https://google.com@{config['lat']},{config['lon']},{config['zoom']}z"

# 5. Bouton d'action pour le consommateur
st.link_button("🚀 Ouvrir la carte de la région", lien_maps)
