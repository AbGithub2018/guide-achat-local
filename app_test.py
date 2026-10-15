import streamlit as st
import requests
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Configuration de la page Streamlit
st.set_page_config(page_title="Trouve ton Épicerie", page_icon="🛒", layout="centered")

st.title("🛒 Recherche d'épiceries par Code Postal")
st.write("Une application de test 100% gratuite et open-source pour les consommateurs.")

# --- FONCTIONS TECHNIQUES ---
@st.cache_data(show_spinner=False)
def obtenir_coordonnees(code_postal, pays):
    """Convertit le code postal en Lat/Lng (mis en cache pour éviter les requêtes répétitives)"""
    geolocator = Nominatim(user_agent="mon_app_streamlit_gratuite_v1")
    try:
        requete = f"{code_postal}, {pays}"
        emplacement = geolocator.geocode(requete)
        if emplacement:
            return emplacement.latitude, emplacement.longitude
    except GeocoderTimedOut:
        return None, None
    return None, None

@st.cache_data(show_spinner=False)
def chercher_commerces_proximite(lat, lon, rayon_metres):
    """Cherche les commerces autour des coordonnées via l'API Overpass"""
    url_overpass = "https://overpass-api.de"
    requete_overpass = f"""
    [out:json][timeout:25];
    (
      node["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      way["shop"="supermarket"](around:{rayon_metres},{lat},{lon});
      node["shop"="grocery"](around:{rayon_metres},{lat},{lon});
      way["shop"="grocery"](around:{rayon_metres},{lat},{lon});
    );
    out body center;
    """
    try:
        response = requests.post(url_overpass, data={'data': requete_overpass})
        if response.status_code == 200:
            donnees = response.json()
            commerces = []
            
            for element in donnees.get('elements', []):
                tags = element.get('tags', {})
                
                # Récupération des coordonnées (gère les nodes et les géométries complexes 'ways')
                e_lat = element.get('lat') or element.get('center', {}).get('lat')
                e_lon = element.get('lon') or element.get('center', {}).get('lon')
                
                if e_lat and e_lon:
                    nom = tags.get('name', 'Épicerie indépendante / sans nom')
                    rue = tags.get('addr:street', '')
                    numero = tags.get('addr:housenumber', '')
                    adresse = f"{numero} {rue}".strip() if rue else "Adresse non renseignée"
                    
                    commerces.append({
                        "Nom": nom, 
                        "Adresse": adresse,
                        "latitude": float(e_lat),
                        "longitude": float(e_lon)
                    })
            return commerces
    except Exception:
        return []
    return []

# --- INTERFACE UTILISATEUR (UI) ---
col1, col2 = st.columns(2)
with col1:
    pays = st.selectbox("Pays", ["Canada", "France", "Belgique", "Suisse"], index=0)
with col2:
    code_postal = st.text_input("Code Postal", value="G5Y 7W1" if pays == "Canada" else "75001")

rayon_km = st.slider("Rayon de recherche (en km)", min_value=1, max_value=15, value=5)

if st.button("🔍 Rechercher les commerces", type="primary"):
    if not code_postal.strip():
        st.warning("Veuillez entrer un code postal valide.")
    else:
        with st.spinner("Géolocalisation du code postal..."):
            lat, lon = obtenir_coordonnees(code_postal, pays)
            
        if lat and lon:
            with st.spinner("Recherche des commerces sur OpenStreetMap..."):
                resultats = chercher_commerces_proximite(lat, lon, rayon_km * 1000)
                
            if resultats:
                st.success(f"🎉 {len(resultats)} commerces trouvés dans un rayon de {rayon_km} km !")
                
                # Conversion en DataFrame Pandas pour affichage
                df = pd.DataFrame(resultats)
                
                # Affichage de la carte Streamlit
                st.subheader("🗺️ Carte des commerces")
                st.map(df, latitude="latitude", longitude="longitude")
                
                # Affichage de la liste de résultats
                st.subheader("📋 Liste des magasins")
                st.dataframe(df[["Nom", "Adresse"]], use_container_width=True)
            else:
                st.info("Aucun commerce trouvé dans cette zone avec les critères sélectionnés.")
        else:
            st.error("Impossible de localiser ce code postal. Vérifiez le format ou le pays sélectionné.")
