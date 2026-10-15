import streamlit as st
import pandas as pd
import json
import numpy as np

# Configuration de la page Streamlit
st.set_page_config(page_title="Radar Alimentaire Québec", page_icon="🍲", layout="centered")

st.title("🍲 Radar Alimentaire Québécois")
st.write("Entrez votre code postal pour lister les enseignes alimentaires disponibles à proximité.")

# --- 1. BASE DE DONNÉES LOCALES DES CODES POSTAUX (POSTES CANADA) ---
BASE_COORDONNEES_QC = {
    "G5Y": (46.1211, -70.6718, "Saint-Georges"),
    "G5X": (46.2000, -70.7667, "Beauceville"),
    "G6B": (45.5833, -70.8833, "Lac-Mégantic"),
    "G6E": (46.4333, -71.0333, "Sainte-Marie"),
    "G1K": (46.8139, -71.2222, "Québec Centre"),
    "H2W": (45.5167, -73.5750, "Montréal (Plateau)"),
    "H3B": (45.5017, -73.5667, "Montréal Centre"),
    "J1H": (45.4000, -71.8900, "Sherbrooke"),
    "J9T": (48.5667, -78.1167, "Amos"),
}

def obtenir_gps_secteur(code_postal):
    cp_propre = code_postal.strip().replace(" ", "").upper()
    if len(cp_propre) >= 3:
        rta = cp_propre[:3]
        if rta in BASE_COORDONNEES_QC:
            return BASE_COORDONNEES_QC[rta]
    # Par défaut pour le test : Saint-Georges
    return BASE_COORDONNEES_QC["G5Y"]

# --- 2. CALCUL MATHÉMATIQUE DE PROXIMITÉ (HAVERSINE) ---
def calculer_distance_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en km
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 3. CHARGEMENT ET PARSING DE VOTRE FICHIER GEOJSON ---
@st.cache_data(show_spinner=False)
def charger_commerces_du_fichier(chemin_fichier):
    """Lit le fichier GeoJSON fourni et le convertit en tableau utilisable"""
    try:
        with open(chemin_pdf, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        liste_commerces = []
        for feature in geojson_data.get('features', []):
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coords = geometry.get('coordinates', [])
            
            if len(coords) >= 2:
                # Dans le GeoJSON, c'est stocké sous forme [Longitude, Latitude]
                lon = float(coords[0])
                lat = float(coords[1])
                
                # Récupération du nom ou de la marque
                nom = properties.get('brand') or properties.get('name') or "Commerce alimentaire"
                type_boutique = properties.get('shop', 'supermarket')
                
                # Extraction de l'adresse textuelle si présente
                ville_doc = properties.get('addr:city', '')
                rue_doc = properties.get('addr:street', '')
                num_doc = properties.get('addr:housenumber', '')
                adresse_complete = f"{num_doc} {rue_doc}, {ville_doc}".strip() if rue_doc else "Adresse non spécifiée"
                
                # Détermination de l'URL du site officiel en fonction de la bannière
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
                    "Adresse": adresse_complete,
                    "Site Web": url_site,
                    "latitude": lat,
                    "longitude": lon
                })
        return pd.DataFrame(liste_commerces)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier data : {e}")
        return pd.DataFrame()

# --- INITIALISATION DE L'APPLICATION ---
# Enregistrez le contenu de votre texte dans un fichier nommé 'commerces.geojson' à côté de votre script
df_global_commerces = charger_commerces_du_fichier("commerces.geojson")

# --- INTERFACE UTILISATEUR ---
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3 ou H2W 1A2) :", value="G5Y 6H3")
rayon_recherche = st.slider("Rayon de recherche maximal (km) :", min_value=1, max_value=25, value=15)

if cp_saisi.strip() and not df_global_commerces.empty:
    # 1. Calculer le centre GPS du code postal
    (centre_lat, centre_lon, nom_municipalite) = obtenir_gps_secteur(cp_saisi)
    rta_saisie = cp_saisi.strip().replace(" ", "").upper()[:3]
    
    # 2. Calculer la distance de chaque commerce du fichier par rapport au code postal
    df_global_commerces['Distance (km)'] = df_global_commerces.apply(
        lambda row: calculer_distance_km(centre_lat, centre_lon, row['latitude'], row['longitude']), axis=1
    )
    
    # 3. Filtrer selon le rayon
    df_resultats = df_global_commerces[df_global_commerces['Distance (km)'] <= rayon_recherche].sort_values(by='Distance (km)')
    
    if not df_resultats.empty:
        st.subheader(f"🏬 Enseignes à proximité de {nom_municipalite} ({rta_saisie}) :")
        st.write("Cliquez sur le bouton d'une bannière pour visiter son site internet officiel.")
        
        # Élimination des doublons de bannières pour n'afficher qu'une seule fois chaque site web par secteur
        df_affichage = df_resultats.drop_duplicates(subset=["Bannière"])
        
        for index, row in df_affichage.iterrows():
            with st.container():
                col_info, col_lien = st.columns([2, 1])
                with col_info:
                    st.markdown(f"**{row['Bannière']}**")
                    st.caption(f"Plus proche succursale détectée à environ : {round(row['Distance (km)'], 1)} km")
                with col_lien:
                    st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                st.markdown(" ")
    else:
        st.info(f"Aucun commerce alimentaire du fichier n'est présent dans un rayon de {rayon_recherche} km autour de ce secteur.")
