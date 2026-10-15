import streamlit as st
import pandas as pd
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

# --- 3. CHARGEMENT EMBEDDÉ DES DONNÉES DE VOTRE DOCUMENT ---
@st.cache_data(show_spinner=False)
def charger_commerces_directs():
    """Données extraites directement de votre document cartographique fournissant les points GPS réels"""
    donnees_extraites = [
        {"Bannière": "Super C", "Adresse": "8585 Boulevard Lacroix, Saint-Georges", "Site Web": "https://superc.ca", "latitude": 46.1329594, "longitude": -70.6981938},
        {"Bannière": "IGA Extra", "Adresse": "Montréal", "Site Web": "https://iga.net", "latitude": 45.4060804, "longitude": -73.4964169},
        {"Bannière": "Metro", "Adresse": "Montréal", "Site Web": "https://metro.ca", "latitude": 45.4459086, "longitude": -73.8156631},
        {"Bannière": "IGA Extra", "Adresse": "90 Boulevard d'Anjou, Châteauguay", "Site Web": "https://iga.net", "latitude": 45.3596381, "longitude": -73.7334332},
        {"Bannière": "Metro", "Adresse": "105 Rue Principale, Châteauguay", "Site Web": "https://metro.ca", "latitude": 45.3572064, "longitude": -73.7570174},
        {"Bannière": "Super C", "Adresse": "Châteauguay", "Site Web": "https://superc.ca", "latitude": 45.3584805, "longitude": -73.7226325},
        {"Bannière": "Provigo", "Adresse": "Montréal", "Site Web": "https://provigo.ca", "latitude": 45.5088138, "longitude": -73.5717973},
        {"Bannière": "Maxi", "Adresse": "6381 Route Transcanadienne, Pointe-Claire", "Site Web": "https://maxi.ca", "latitude": 45.4671133, "longitude": -73.8268437},
        {"Bannière": "Maxi", "Adresse": "Boulevard Taschereau, La Prairie", "Site Web": "https://maxi.ca", "latitude": 45.4216883, "longitude": -73.4866387},
        {"Bannière": "Maxi", "Adresse": "7200 Boulevard Taschereau, Brossard", "Site Web": "https://maxi.ca", "latitude": 45.4604109, "longitude": -73.4679184},
        {"Bannière": "Walmart Supercentre", "Adresse": "Trois-Rivières", "Site Web": "https://walmart.ca", "latitude": 46.3241616, "longitude": -72.5655232},
        {"Bannière": "Dollarama", "Adresse": "Sherbrooke", "Site Web": "https://dollarama.com", "latitude": 45.3994984, "longitude": -71.9182897},
        {"Bannière": "Tigre Géant", "Adresse": "Québec", "Site Web": "https://gianttiger.com", "latitude": 46.8150849, "longitude": -71.2236292}
    ]
    return pd.DataFrame(donnees_extraites)

df_global_commerces = charger_commerces_directs()

# --- INTERFACE UTILISATEUR ---
cp_saisi = st.text_input("Entrez votre code postal (ex: G5Y 6H3 ou H2W 1A2) :", value="G5Y 6H3")
rayon_recherche = st.slider("Rayon de recherche maximal (km) :", min_value=1, max_value=25, value=15)

if cp_saisi.strip() and not df_global_commerces.empty:
    # 1. Obtenir le centre géographique du secteur
    (centre_lat, centre_lon, nom_municipalite) = obtenir_gps_secteur(cp_saisi)
    rta_saisie = cp_saisi.strip().replace(" ", "").upper()[:3]
    
    # 2. Calculer les distances réelles
    df_global_commerces['Distance (km)'] = df_global_commerces.apply(
        lambda row: calculer_distance_km(centre_lat, centre_lon, row['latitude'], row['longitude']), axis=1
    )
    
    # 3. Filtrer par rayon
    df_resultats = df_global_commerces[df_global_commerces['Distance (km)'] <= rayon_recherche].sort_values(by='Distance (km)')
    
    if not df_resultats.empty:
        st.subheader(f"🏬 Enseignes à proximité de {nom_municipalite} ({rta_saisie}) :")
        st.write("Cliquez sur la bannière pour ouvrir directement son site web.")
        
        # Filtrer pour n'afficher qu'une seule fois chaque grande enseigne trouvée dans la zone
        df_affichage = df_resultats.drop_duplicates(subset=["Bannière"])
        
        for index, row in df_affichage.iterrows():
            with st.container():
                # CORRECTION ICI : Ajout du chiffre 2 pour spécifier le nombre de colonnes
                col_info, col_lien = st.columns(2)
                with col_info:
                    st.markdown(f"**{row['Bannière']}**")
                    st.caption(f"Succursale trouvée dans votre rayon de recherche.")
                with col_lien:
                    st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                st.markdown(" ")
    else:
        st.info(f"Aucune bannière de notre liste n'a été répertoriée dans un rayon de {rayon_recherche} km autour de {nom_municipalite}.")
