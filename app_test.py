import streamlit as st
import requests
import pandas as pd
from geopy.geocoders import Nominatim

# Configuration de la page de test Streamlit
st.set_page_config(page_title="Localisateur d'Épiceries", page_icon="📍")

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Entrez un code postal pour afficher les supermarchés et fruiteries à proximité.")

# --- FONCTIONS DE GÉOLOCALISATION (Mises en cache pour la performance) ---

@st.cache_data(show_spinner=False)
def obtenir_coordonnees_par_cp(code_postal):
    """
    Transforme le code postal en Latitude/Longitude via OpenStreetMap.
    Nettoie et tronque le code postal à 3 caractères pour garantir la compatibilité avec Nominatim.
    """
    # Nettoyage de l'entrée utilisateur (retrait des espaces et mise en majuscules)
    cp_propre = code_postal.strip().replace(" ", "").upper()
    
    # Stratégie de contournement : Si le code fait plus de 3 caractères, on ne garde que les 3 premiers (ex: G5Y)
    # Nominatim gère beaucoup mieux les secteurs généraux canadiens que les codes ultra-précis.
    if len(cp_propre) >= 3:
        cp_propre = cp_propre[:3]
    else:
        return None, None

    geolocator = Nominatim(
        user_agent="localisateur_epiceries_quebec_final_version", 
        timeout=15
    )
    
    try:
        # Requête optimisée pour le Québec
        requete = f"{cp_propre}, Quebec, Canada"
        emplacement = geolocator.geocode(requete)
        if emplacement:
            return emplacement.latitude, emplacement.longitude
    except Exception:
        return None, None
    return None, None

@st.cache_data(show_spinner=False)
def chercher_epiceries_api(lat, lon, rayon_km=5):
    """
    Interroge l'API Overpass d'OpenStreetMap pour extraire 
    les commerces d'alimentation dans le rayon choisi.
    """
    url_overpass = "https://overpass-api.de"
    rayon_metres = rayon_km * 1000
    
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
                e_lat = element.get('lat') or element.get('center', {}).get('lat')
                e_lon = element.get('lon') or element.get('center', {}).get('lon')
                
                if e_lat and e_lon:
                    nom = tags.get('name', 'Épicerie indépendante / Sans nom')
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

# --- INTERFACE UTILISATEUR ---

# Formulaire de saisie du code postal
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3) :", value="G5Y 6H3")
rayon = st.slider("Rayon de recherche (km)", min_value=1, max_value=15, value=5)

if st.button("🔍 Chercher autour de ce code postal", type="primary"):
    if not cp_saisi.strip() or len(cp_saisi.strip()) < 3:
        st.warning("Veuillez entrer un code postal valide d'au moins 3 caractères.")
    else:
        with st.spinner("Localisation du secteur du code postal..."):
            lat, lon = obtenir_coordonnees_par_cp(cp_saisi)
            
        if lat and lon:
            with st.spinner("Recherche des commerces à proximité..."):
                resultats = chercher_epiceries_api(lat, lon, rayon)
                
            if resultats:
                st.success(f"🎉 {len(resultats)} commerces trouvés dans un rayon de {rayon} km autour du secteur {cp_saisi[:3].upper()} !")
                
                # Création du DataFrame requis par st.map
                df = pd.DataFrame(resultats)
                
                # Affichage de la carte interactive
                st.subheader("🗺️ Carte des résultats")
                st.map(df, latitude="latitude", longitude="longitude")
                
                # Affichage du tableau de données complet
                st.subheader("📋 Liste des magasins détectés")
                st.dataframe(df[["Nom", "Adresse"]], use_container_width=True)
            else:
                st.info(f"Aucune épicerie trouvée dans ce rayon autour du secteur {cp_saisi[:3].upper()}. Essayez d'augmenter le rayon.")
        else:
            st.error("Le serveur de géolocalisation gratuit a rejeté la requête ou le code postal est inconnu. Veuillez réessayer.")
