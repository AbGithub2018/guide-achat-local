import streamlit as st
import pandas as pd
import numpy as np

# Configuration générale
st.set_page_config(page_title="Radar Alimentaire Québec", page_icon="🍲", layout="centered")

st.title("🍲 Radar Alimentaire Québécois")
st.write("Entrez votre code postal pour lister les bannières d'alimentation disponibles à proximité.")


# ==============================================================================
# PARTIE 1 : RÉPERTOIRE DES CODES POSTAUX DU QUÉBEC (RTA)
# ==============================================================================
def charger_base_regions_qc():
    """Contient le répertoire complet des codes de Postes Canada pour le Québec"""
    return {
        # --- SÉRIE G (Est du Québec, Beauce, Québec, Saguenay, Rimouski) ---
        "G0A": (46.9000, -71.1500, "Côte-de-Beaupré"), "G0C": (48.1500, -65.5000, "Gaspésie (Sud)"),
        "G0E": (49.1500, -65.5000, "Gaspésie (Nord)"), "G0G": (50.2500, -65.5000, "Basse-Côte-Nord"),
        "G0H": (48.5000, -68.5000, "Rimouski-Neigette"), "G0J": (48.5500, -67.5000, "La Matapédia"),
        "G0K": (48.3000, -69.2000, "Bas-Saint-Laurent"), "G0L": (47.5000, -69.5000, "Témiscouata"),
        "G0R": (46.8000, -70.5000, "Montmagny / L'Islet"), "G0S": (46.4000, -71.3000, "Lotbinière"),
        "G0T": (48.2000, -70.0000, "Charlevoix"), "G0V": (48.4000, -71.0000, "Saguenay"),
        "G0W": (49.0000, -72.5000, "Lac-Saint-Jean"), "G0X": (46.6000, -72.5000, "Mauricie"),
        "G0Y": (46.1000, -71.3000, "Les Appalaches"), "G1B": (46.8700, -71.2000, "Beauport-Nord"),
        "G1C": (46.8500, -71.1800, "Beauport-Sud"), "G1E": (46.8600, -71.2100, "Courville"),
        "G1G": (46.8800, -71.2800, "Charlesbourg-Nord"), "G1H": (46.8500, -71.2600, "Charlesbourg-Sud"),
        "G1J": (46.8300, -71.2200, "Vieux-Limoilou"), "G1K": (46.8139, -71.2222, "Québec (Basse-Ville)"),
        "G1L": (46.8200, -71.2400, "Limoilou-Ouest"), "G1M": (46.8100, -71.2600, "Vanier"),
        "G1N": (46.8000, -71.2500, "Saint-Sauveur"), "G1P": (46.8100, -71.3000, "Les Saules"),
        "G1Q": (46.8500, -71.3500, "Loretteville"), "G1R": (46.8100, -71.2100, "Québec (Haute-Ville)"),
        "G1S": (46.7960, -71.2450, "Québec (Sillery)"), "G1T": (46.7800, -71.2600, "Sainte-Foy-Est"),
        "G1V": (46.7800, -71.2800, "Sainte-Foy-Centre"), "G1W": (46.7600, -71.3200, "Cap-Rouge"),
        "G1X": (46.7700, -71.3500, "Sainte-Foy-Ouest"), "G1Y": (46.7300, -71.2800, "Cap-Rouge-Sud"),
        "G5X": (46.2000, -70.7667, "Beauceville"), "G5Y": (46.1211, -70.6718, "Saint-Georges"),
        
        # --- SÉRIE H (Montréal et Laval) ---
        "H1A": (45.6400, -73.5000, "Pointe-aux-Trembles"), "H1B": (45.6300, -73.5100, "Montréal-Est"),
        "H1C": (45.6600, -73.5300, "Rivière-des-Prairies"), "H1G": (45.6000, -73.6300, "Montréal-Nord"),
        "H1V": (45.5409, -73.5592, "Montréal (Maisonneuve)"), "H2W": (45.5167, -73.5750, "Montréal (Plateau)"),
        "H3B": (45.5017, -73.5667, "Montréal (Centre-Ville)"), "H3S": (45.5032, -73.6363, "Montréal (Côte-des-Neiges)"),
        "H3W": (45.4933, -73.6390, "Montréal (Snowdon)"), "H4L": (45.5237, -73.6917, "Saint-Laurent"),
        "H8R": (45.4297, -73.6349, "Montréal (LaSalle)"), "H9R": (45.4671, -73.8268, "Pointe-Claire"),
        
        # --- SÉRIE J (Lanaudière, Laurentides, Montérégie, Estrie, Abitibi) ---
        "J1H": (45.3961, -71.8956, "Sherbrooke"), "J1L": (45.4052, -71.9569, "Sherbrooke (Portland)"),
        "J2G": (45.4169, -72.7512, "Granby"), "J2W": (45.3426, -73.2727, "Saint-Jean-sur-Richelieu"),
        "J3P": (46.0261, -73.0974, "Sorel-Tracy"), "J4K": (45.5291, -73.5144, "Longueuil"),
        "J4W": (45.4604, -73.4679, "Brossard"), "J6E": (46.0511, -73.4692, "Joliette"),
        "J7K": (45.7221, -73.6192, "Mascouche"), "J8X": (45.4292, -75.7233, "Gatineau (Hull)"),
        "J9T": (48.5667, -78.1167, "Amos"),
    }


# ==============================================================================
# PARTIE 2 : RÉPERTOIRE DES COMMERCES ALIMENTAIRES ET SITES WEB
# ==============================================================================
def charger_base_commerces():
    """Contient les points cartographiques extraits de votre document GeoJSON"""
    return [
        {"Bannière": "IGA Extra", "latitude": 45.4061, "longitude": -73.4964, "Site Web": "https://iga.net"},
        {"Bannière": "Metro", "latitude": 45.4459, "longitude": -73.8156, "Site Web": "https://metro.ca"},
        {"Bannière": "IGA Extra Châteauguay", "latitude": 45.3596, "longitude": -73.7334, "Site Web": "https://iga.net"},
        {"Bannière": "Metro Châteauguay", "latitude": 45.3572, "longitude": -73.7570, "Site Web": "https://metro.ca"},
        {"Bannière": "Super C", "latitude": 45.3584, "longitude": -73.7226, "Site Web": "https://superc.ca"},
        {"Bannière": "Provigo", "latitude": 45.5088, "longitude": -73.5718, "Site Web": "https://provigo.ca"},
        {"Bannière": "PA Nature Supermarché", "latitude": 45.5194, "longitude": -73.5950, "Site Web": "https://supermarchepa.com"},
        {"Bannière": "Maxi Pointe-Claire", "latitude": 45.4671, "longitude": -73.8268, "Site Web": "https://maxi.ca"},
        {"Bannière": "Maxi La Prairie", "latitude": 45.4216, "longitude": -73.4866, "Site Web": "https://maxi.ca"},
        {"Bannière": "Maxi Brossard", "latitude": 45.4604, "longitude": -73.4679, "Site Web": "https://maxi.ca"},
        {"Bannière": "Super C Matane", "latitude": 48.8521, "longitude": -67.5372, "Site Web": "https://superc.ca"},
        {"Bannière": "Metro Longueuil", "latitude": 45.5010, "longitude": -73.4260, "Site Web": "https://metro.ca"},
        {"Bannière": "Maxi Québec", "latitude": 46.8198, "longitude": -71.3305, "Site Web": "https://maxi.ca"},
        {"Bannière": "IGA Deschênes Québec", "latitude": 46.8044, "longitude": -71.2310, "Site Web": "https://iga.net"},
        {"Bannière": "Metro Québec", "latitude": 46.8046, "longitude": -71.2269, "Site Web": "https://metro.ca"},
        {"Bannière": "Walmart Supercentre Trois-Rivières", "latitude": 46.3241, "longitude": -72.5655, "Site Web": "https://walmart.ca"},
        {"Bannière": "Super C Sherbrooke", "latitude": 45.3961, "longitude": -71.8956, "Site Web": "https://superc.ca"},
        {"Bannière": "Metro Mont-Royal", "latitude": 45.5374, "longitude": -73.5707, "Site Web": "https://metro.ca"},
        {"Bannière": "Super C Saint-Georges", "latitude": 46.1329, "longitude": -70.6981, "Site Web": "https://superc.ca"}
    ]


# ==============================================================================
# PARTIE 3 : CALCULS MATHÉMATIQUES ET GÉOSPATIAUX
# ==============================================================================
def calculer_distance_km(lat1, lon1, lat2, lon2):
    """Formule de Haversine pour mesurer les distances à vol d'oiseau"""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


# ==============================================================================
# PARTIE 4 : INTERFACE UTILISATEUR ET RENDER (LOGIQUE STREAMLIT)
# ==============================================================================
# Chargement des données à partir des fonctions d'en-tête
base_regions = charger_base_regions_qc()
df_commerces_base = pd.DataFrame(charger_base_commerces())

# Formulaire de saisie
cp_saisi = st.text_input("Entrez votre code postal (ex: G1K 3A9, H8R 3C2, G5Y 6H3) :", value="G1K 3A9")
rayon_recherche = st.slider("Rayon de recherche maximal (km) :", min_value=1, max_value=50, value=25)

if cp_saisi.strip():
    cp_propre = cp_saisi.strip().replace(" ", "").upper()
    rta_saisie = cp_propre[:3] if len(cp_propre) >= 3 else ""
    
    # Validation et extraction immédiate des coordonnées GPS correspondantes
    if rta_saisie in base_regions:
        centre_lat, centre_lon, nom_municipalite = base_regions[rta_saisie]
        
        # Calcul de proximité réel
        df_commerces_base['Distance (km)'] = df_commerces_base.apply(
            lambda row: calculer_distance_km(centre_lat, centre_lon, row['latitude'], row['longitude']), axis=1
        )
        
        # Filtre sur le rayon choisi
        df_filtre = df_commerces_base[df_commerces_base['Distance (km)'] <= rayon_recherche].sort_values(by='Distance (km)')
        
        if not df_filtre.empty:
            st.subheader(f"🏬 Enseignes à proximité de : {nom_municipalite} ({rta_saisie})")
            st.write("Cliquez sur la bannière pour ouvrir directement son site internet officiel.")
            
            # Éviter les bannières en double dans le rendu
            df_affichage = df_filtre.drop_duplicates(subset=["Bannière"])
            
            for index, row in df_affichage.iterrows():
                with st.container():
                    col_info, col_lien = st.columns(2)
                    with col_info:
                        st.markdown(f"**{row['Bannière']}**")
                        st.caption(f"Magasin le plus proche détecté à {round(row['Distance (km)'], 1)} km")
                    with col_lien:
                        st.link_button(f"🌐 Visiter {row['Bannière']}", row['Site Web'], use_container_width=True)
                    st.markdown(" ")
        else:
            st.info(f"Aucune grande enseigne n'a été trouvée dans un rayon de {rayon_recherche} km autour de {nom_municipalite}.")
    else:
        st.warning("Ce code postal n'est pas répertorié au Québec dans ce test. Veuillez entrer une RTA valide (ex: G1K, H8R, G5Y).")
