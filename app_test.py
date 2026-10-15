import streamlit as st
import requests
import pandas as pd

# Configuration de la page Streamlit
st.set_page_config(page_title="Localisateur d'Épiceries", page_icon="📍")

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Entrez un code postal pour afficher les supermarchés et fruiteries à proximité.")

# --- FONCTIONS DE GÉOLOCALISATION VIA L'API GOUVERNEMENTALE CANADIENNE ---

@st.cache_data(show_spinner=False)
def obtenir_coordonnees_canada(code_postal):
    """
    Trouve les coordonnées GPS exactes en interrogeant l'API gratuite du Gouvernement du Canada.
    Cette API accepte les codes à 6 caractères sans aucun blocage.
    """
    # Nettoyage du code postal (MAJUSCULES et retrait des espaces)
    cp_propre = code_postal.strip().replace(" ", "").upper()
    
    # URL du service de géocodage public du gouvernement canadien
    url = f"https://geogratis.gc.ca{cp_propre}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            donnees = response.json()
            if donnees and len(donnees) > 0:
                # Récupération des coordonnées dans la réponse géospatiale
                coords = donnees[0].get('geometry', {}).get('coordinates', [])
                if len(coords) >= 2:
                    # L'API GeoGratis retourne [Longitude, Latitude]
                    return coords[1], coords[0]
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
                    nom = tags.get('name', 'Épicerie indépendante')
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

# Formulaire de saisie du code postal (Accepte les codes complets à 6 caractères)
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H7) :", value="G5Y 6H7")
rayon = st.slider("Rayon de recherche (km)", min_value=1, max_value=15, value=5)

if st.button("🔍 Chercher autour de ce code postal", type="primary"):
    if not cp_saisi.strip() or len(cp_saisi.strip()) < 3:
        st.warning("Veuillez entrer un code postal canadien valide.")
    else:
        with st.spinner("Localisation par l'API du Canada..."):
            lat, lon = obtenir_coordonnees_canada(cp_saisi)
            
        if lat and lon:
            with st.spinner("Recherche des commerces à proximité..."):
                resultats = chercher_epiceries_api(lat, lon, rayon)
                
            if resultats:
                st.success(f"🎉 {len(resultats)} commerces trouvés dans un rayon de {rayon} km autour de {cp_saisi.upper()} !")
                
                df = pd.DataFrame(resultats)
                
                # Affichage de la carte interactive
                st.subheader("🗺️ Carte des résultats")
                st.map(df, latitude="latitude", longitude="longitude")
                
                # Affichage du tableau de données
                st.subheader("📋 Liste des magasins détectés")
                st.dataframe(df[["Nom", "Adresse"]], use_container_width=True)
            else:
                st.info(f"Aucune épicerie trouvée dans un rayon de {rayon} km autour de ce point.")
        else:
            st.error("Le code postal est introuvable ou l'API gouvernementale ne répond pas. Vérifiez le format.")
