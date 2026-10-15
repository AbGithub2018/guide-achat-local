import streamlit as st
import pandas as pd
import numpy as np
import requests

# Configuration de la page Streamlit
st.set_page_config(page_title="Radar Alimentaire Québec", page_icon="🍲", layout="centered")

st.title("🍲 Radar Alimentaire Québécois")
st.write("Entrez votre code postal pour lister les bannières d'alimentation disponibles à proximité.")

# --- 1. GÉOLOCALISATION ULTRA-FIABLE (API GOUVERNEMENTALE DU CANADA) ---
@st.cache_data(show_spinner=False, ttl=86400) # Garde en cache 24h pour une vitesse éclair
def obtenir_gps_officiel_canada(code_postal):
    """
    Interroge l'API gratuite du Gouvernement du Canada.
    Reconnaît TOUS les codes postaux du Québec et extrait la vraie municipalité.
    """
    cp_propre = code_postal.strip().replace(" ", "").upper()
    url = f"https://geogratis.gc.ca{cp_propre}"
    
    try:
        # L'User-Agent évite d'être bloqué ou considéré comme un robot
        headers = {"User-Agent": "RadarAlimentaireQuebec/1.0 (Contact: appli@test.com)"}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            donnees = response.json()
            if isinstance(donnees, list) and len(donnees) > 0:
                premier_resultat = donnees[0]
                nom_lieu = premier_resultat.get('title', 'Secteur détecté')
                geometry = premier_resultat.get('geometry', {})
                coords = geometry.get('coordinates', [])
                
                if len(coords) >= 2:
                    # GéoGratis retourne la structure [Longitude, Latitude]
                    lon = float(coords[0])
                    lat = float(coords[1])
                    return lat, lon, nom_lieu
    except Exception:
        pass
    return None, None, None

# --- 2. CALCUL MATHÉMATIQUE DE DISTANCE (HAVERSINE) ---
def calculer_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 3. BASE DE DONNÉES DES COMMERCES (EXTRAITE DE VOTRE DOCUMENT GEOJSON) ---
@st.cache_data(show_spinner=False)
def charger_base_commerces():
    """Contient les points cartographiques réels extraits de votre document GeoJSON"""
    return [
        {"Bannière": "IGA Extra", "latitude": 45.4060804, "longitude": -73.4964169, "Site Web": "https://iga.net"},
        {"Bannière": "Metro", "latitude": 45.4459086, "longitude": -73.8156631, "Site Web": "https://metro.ca"},
        {"Bannière": "IGA Extra Châteauguay", "latitude": 45.3596381, "longitude": -73.7334332, "Site Web": "https://iga.net"},
        {"Bannière": "Metro Châteauguay", "latitude": 45.3572064, "longitude": -73.7570174, "Site Web": "https://metro.ca"},
        {"Bannière": "Super C", "latitude": 45.3584805, "longitude": -73.7226325, "Site Web": "https://superc.ca"},
        {"Bannière": "Provigo", "latitude": 45.5088138, "longitude": -73.5717973, "Site Web": "https://provigo.ca"},
        {"Bannière": "PA Nature Supermarché", "latitude": 45.5194351, "longitude": -73.5949644, "Site Web": "https://supermarchepa.com"},
        {"Bannière": "Maxi Pointe-Claire", "latitude": 45.4671133, "longitude": -73.8268437, "Site Web": "https://maxi.ca"},
        {"Bannière": "Maxi La Prairie", "latitude": 45.4216883, "longitude": -73.4866387, "Site Web": "https://maxi.ca"},
        {"Bannière": "Maxi Brossard", "latitude": 45.4604109, "longitude": -73.4679184, "Site Web": "https://maxi.ca"},
        {"Bannière": "Super C Matane", "latitude": 48.8521515, "longitude": -67.5372693, "Site Web": "https://superc.ca"},
        {"Bannière": "Metro Longueuil", "latitude": 45.5010880, "longitude": -73.4260498, "Site Web": "https://metro.ca"},
        {"Bannière": "Maxi Québec", "latitude": 46.8198661, "longitude": -71.3305583, "Site Web": "https://maxi.ca"},
        {"Bannière": "IGA Deschênes Québec", "latitude": 46.8044654, "longitude": -71.2309819, "Site Web": "https://iga.net"},
        {"Bannière": "Metro Québec", "latitude": 46.8046375, "longitude": -71.2268600, "Site Web": "https://metro.ca"},
        {"Bannière": "Walmart Supercentre Trois-Rivières", "latitude": 46.3241616, "longitude": -72.5655232, "Site Web": "https://walmart.ca"},
        {"Bannière": "Super C Sherbrooke", "latitude": 45.3961159, "longitude": -71.8956463, "Site Web": "https://superc.ca"},
        {"Bannière": "Metro Mont-Royal", "latitude": 45.5374033, "longitude": -73.5707588, "Site Web": "https://metro.ca"},
        {"Bannière": "Super C Saint-Georges", "latitude": 46.1329594, "longitude": -70.6981938, "Site Web": "https://superc.ca"},
        {"Bannière": "Magasin Coop de St-Victor", "latitude": 46.1456695, "longitude": -70.9040282, "Site Web": "https://marchestradition.com"}
    ]

# --- 4. INTERFACE UTILISATEUR ---
df_commerces_base = pd.DataFrame(charger_base_commerces())

cp_saisi = st.text_input("Entrez votre code postal (ex: G0M 1G0, G5Y 6H3, H8R 3C2) :", value="G0M 1G0")
rayon_recherche = st.slider("Rayon de recherche maximal (km) :", min_value=1, max_value=50, value=25)

if cp_saisi.strip():
    with st.spinner("Vérification géospatiale auprès du Gouvernement du Canada..."):
        centre_lat, centre_lon, nom_municipalite = obtenir_gps_officiel_canada(cp_saisi)
    
    if centre_lat and centre_lon:
        rta_saisie = cp_saisi.strip().replace(" ", "").upper()[:3]
        
        # Calcul de la distance géospatiale réelle en temps réel
        df_commerces_base['Distance (km)'] = df_commerces_base.apply(
            lambda row: calculer_distance_km(centre_lat, centre_lon, row['latitude'], row['longitude']), axis=1
        )
        
        # Filtrage en fonction du curseur (km)
        df_filtre = df_commerces_base[df_commerces_base['Distance (km)'] <= rayon_recherche].sort_values(by='Distance (km)')
        
        if not df_filtre.empty:
            st.subheader(f"🏬 Enseignes à proximité de : {nom_municipalite}")
            st.write("Cliquez sur la bannière pour ouvrir directement son site internet officiel.")
            
            # Élimination des doublons de bannières pour un affichage propre
            df_affichage = df_filtre.drop_duplicates(subset=["Bannière"])
            
            for index, row in df_affichage.iterrows():
                with st.container():
                    col_info, col_lien = st.columns(2)
                    with col_info:
                        st.markdown(f"**{row['Bannière']}**")
                        st.caption(f"Succursale détectée à environ {round(row['Distance (km)'], 1)} km")
                    with col_lien:
                        st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                    st.markdown(" ")
        else:
            st.info(f"Aucune grande enseigne d'alimentation n'a été trouvée dans un rayon de {rayon_recherche} km autour de {nom_municipalite}.")
    else:
        st.error("Format de code postal invalide ou l'API fédérale ne répond pas. Veuillez réessayer (Ex: G0M 1G0).")
