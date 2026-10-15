import streamlit as st
import pandas as pd
import json
import numpy as np
import requests

# Configuration de la page Streamlit
st.set_page_config(page_title="Radar Alimentaire Québec", page_icon="🍲", layout="centered")

st.title("🍲 Radar Alimentaire Québécois")
st.write("Entrez votre code postal pour lister les enseignes alimentaires disponibles à proximité.")

# --- 1. GÉOLOCALISATION DYNAMIQUE VIA L'API DU GOUVERNEMENT DU CANADA ---
@st.cache_data(show_spinner=False)
def obtenir_gps_gouvernement(code_postal):
    """
    Interroge l'API officielle de Ressources naturelles Canada pour trouver
    la latitude, la longitude et le nom de la municipalité de n'importe quel code postal.
    """
    cp_propre = code_postal.strip().replace(" ", "").upper()
    url = f"https://geogratis.gc.ca{cp_propre}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            donnees = response.json()
            if isinstance(donnees, list) and len(donnees) > 0:
                # Extraction du premier résultat le plus précis
                premier = donnees[0]
                nom_lieu = premier.get('title', 'Secteur inconnu')
                geometry = premier.get('geometry', {})
                coords = geometry.get('coordinates', [])
                
                if len(coords) >= 2:
                    # GéoGratis renvoie [Longitude, Latitude]
                    return float(coords[1]), float(coords[0]), nom_lieu
    except Exception:
        pass
    # Fallback par défaut si l'API ne répond pas (Saint-Georges)
    return 46.1211, -70.6718, "Saint-Georges (Mode Secours)"

# --- 2. CALCUL MATHÉMATIQUE DE PROXIMITÉ (HAVERSINE) ---
def calculer_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 3. CHARGEMENT DYNAMIQUE DE VOTRE FICHIER GEOJSON ---
@st.cache_data(show_spinner=False)
def charger_commerces_du_fichier(chemin_fichier):
    """Lit votre fichier GeoJSON et extrait les bannières avec leurs coordonnées réelles"""
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        liste_commerces = []
        for feature in geojson_data.get('features', []):
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coords = geometry.get('coordinates', [])
            
            if len(coords) >= 2:
                # Format GeoJSON : [Longitude, Latitude]
                lon = float(coords[0])
                lat = float(coords[1])
                
                # Récupération de l'enseigne
                nom = properties.get('brand') or properties.get('name') or "Commerce alimentaire"
                
                # Détermination automatique du site internet
                nom_lower = nom.lower()
                url_site = "https://google.com"
                if "maxi" in nom_lower: url_site = "https://maxi.ca"
                elif "super c" in nom_lower: url_site = "https://superc.ca"
                elif "iga" in nom_lower: url_site = "https://iga.net"
                elif "metro" in nom_lower: url_site = "https://metro.ca"
                elif "dollarama" in nom_lower: url_site = "https://dollarama.com"
                elif "walmart" in nom_lower: url_site = "https://walmart.ca"
                elif "provigo" in nom_lower: url_site = "https://provigo.ca"
                
                liste_commerces.append({
                    "Bannière": nom,
                    "Site Web": url_site,
                    "latitude": lat,
                    "longitude": lon
                })
        return pd.DataFrame(liste_commerces)
    except Exception as e:
        st.error(f"Fichier de données manquant ou invalide : {e}")
        return pd.DataFrame()

# Chargement initial des données
df_global_commerces = charger_commerces_du_fichier("commerces.geojson")

# --- INTERFACE UTILISATEUR ---
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3, H8R 3C2, H2W 1A2) :", value="H8R 3C2")
rayon_recherche = st.slider("Rayon de recherche maximal (km) :", min_value=1, max_value=25, value=15)

if cp_saisi.strip() and not df_global_commerces.empty:
    # 1. Appel à l'API gouvernementale pour trouver la vraie municipalité et ses coordonnées GPS
    with st.spinner("Recherche de la municipalité officielle..."):
        centre_lat, centre_lon, nom_municipalite = obtenir_gps_gouvernement(cp_saisi)
    
    rta_saisie = cp_saisi.strip().replace(" ", "").upper()[:3]
    
    # 2. Calcul des distances réelles par rapport à cette vraie localisation
    df_global_commerces['Distance (km)'] = df_global_commerces.apply(
        lambda row: calculer_distance_km(centre_lat, centre_lon, row['latitude'], row['longitude']), axis=1
    )
    
    # 3. Filtrer pour extraire uniquement les magasins dans le rayon
    df_resultats = df_global_commerces[df_global_commerces['Distance (km)'] <= rayon_recherche].sort_values(by='Distance (km)')
    
    if not df_resultats.empty:
        st.subheader(f"🏬 Enseignes à proximité de {nom_municipalite} ({rta_saisie}) :")
        st.write("Cliquez sur la bannière pour ouvrir directement son site web.")
        
        # Regrouper par enseigne unique pour éviter les doublons dans la liste
        df_affichage = df_resultats.drop_duplicates(subset=["Bannière"])
        
        for index, row in df_affichage.iterrows():
            with st.container():
                col_info, col_lien = st.columns(2)
                with col_info:
                    st.markdown(f"**{row['Bannière']}**")
                    st.caption(f"Succursale la plus proche détectée à {round(row['Distance (km)'], 1)} km")
                with col_lien:
                    st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                st.markdown(" ")
    else:
        st.info(f"Aucune enseigne de notre base de données n'a été détectée dans un rayon de {rayon_recherche} km autour de {nom_municipalite}.")
