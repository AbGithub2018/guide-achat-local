import pandas as pd
import streamlit as st
import numpy as np

st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Ajustez le curseur de distance (0 à 50 km) pour trouver les bannières d'alimentation les plus proches.")

# --- FORMULE DE CALCUL DE DISTANCE GPS ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. BASE DE DONNÉES INTERNE DES CODES POSTAUX ---
@st.cache_data
def chercher_coordonnees_code_postal(code_recherche):
    code_nettoye = str(code_recherche).replace(" ", "").upper()
    base_codes_postaux = {
        "G0M1G0": {"Ville": "La Guadeloupe", "Latitude": 45.9652, "Longitude": -70.9395},
        "G0M0A1": {"Ville": "Saint-Philibert", "Latitude": 46.1264, "Longitude": -70.5820},
        "G0M0A2": {"Ville": "Saint-Théophile", "Latitude": 45.9389, "Longitude": -70.4819},
        "G0M0A3": {"Ville": "Saint-Zacharie", "Latitude": 46.1367, "Longitude": -70.3697},
        "G0M0A4": {"Ville": "Saint-Côme-Linière", "Latitude": 46.0625, "Longitude": -70.5233},
        "G0M0A5": {"Ville": "Sainte-Aurélie", "Latitude": 46.1856, "Longitude": -70.3697},
        "G0M0A6": {"Ville": "Saint-Éphrem-de-Beauce", "Latitude": 46.0575, "Longitude": -70.9472},
        "G0M0A7": {"Ville": "Saint-Prosper", "Latitude": 46.2114, "Longitude": -70.4792},
        "G0M0A8": {"Ville": "Lambton", "Latitude": 45.8375, "Longitude": -71.0911},
        "G0M0A9": {"Ville": "Saint-Benjamin", "Latitude": 46.2878, "Longitude": -70.6128},
        "G0M0B1": {"Ville": "Saint-Victor", "Latitude": 46.1436, "Longitude": -70.8931},
        "G5Y7W9": {"Ville": "Saint-Georges", "Latitude": 46.1180, "Longitude": -70.6720},
        "G5Y5B8": {"Ville": "Saint-Georges", "Latitude": 46.1264, "Longitude": -70.6820},
    }
    if code_nettoye in base_codes_postaux:
        return base_codes_postaux[code_nettoye]
    if code_nettoye.startswith("G0M"):
        return {"Ville": "Zone rurale G0M (Beauce)", "Latitude": 46.0500, "Longitude": -70.7000}
    return None

# --- 2. BASE DE DONNÉES INTERNE DES ÉPICERIES ET LOGOS ---
@st.cache_data
def charger_base_epiceries():
    # Intégration d'URLs d'images publiques pour les logos officiels
    donnees_epiceries = {
        "Bannière": ["Marché Ami", "Marché Tradition", "Super C", "IGA Extra", "Maxi", "Metro Plus", "Provigo", "Super C", "IGA"],
        "Logo_URL": [
            "https://marcheami.ca",
            "https://marchetradition.com",
            "https://superc.ca",
            "https://iga.net",
            "https://maxi.ca",
            "https://metro.ca",
            "https://provigo.ca",
            "https://superc.ca",
            "https://iga.net"
        ],
        "Enseigne": ["Marché Ami La Guadeloupe", "Marché Tradition St-Honoré", "Super C Saint-Georges", "IGA Familles Rodriguez", "Maxi Saint-Georges", "Metro Plus Giguère", "Provigo Le Sieur", "Super C Sainte-Marie", "IGA Marché de la Chaudière"],
        "Adresse": ["1405 Rue principale, La Guadeloupe, QC", "441 Rue principale, Saint-Honoré-de-Shenley, QC", "8585 Boulevard Lacroix, Saint-Georges, QC", "9000 Boulevard Lacroix, Saint-Georges, QC", "10400 Boulevard Lacroix, Saint-Georges, QC", "12550 Boulevard Lacroix, Saint-Georges, QC", "150 120e Rue, Saint-Georges, QC", "1000 Route du Président-Kennedy, Sainte-Marie, QC", "125 Route du Président-Kennedy, Beauceville, QC"],
        "Latitude":  [45.9652, 45.9790, 46.1264, 46.1312, 46.1420, 46.1550, 46.1180, 46.4385, 46.2155],
        "Longitude": [-70.9395, -70.8420, -70.6820, -70.6865, -70.6990, -70.7150, -70.6720, -71.1410, -70.7760]
    }
    return pd.DataFrame(donnees_epiceries)

df_epiceries = charger_base_epiceries()

# --- 3. INTERFACE COMPORTANT LE CURSEUR ---
col_recherche, col_curseur = st.columns(2)

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0 ou G5Y 7W9) :").strip().upper()

with col_curseur:
    rayon_max = st.slider("Zoomer selon une distance (km) :", min_value=0, max_value=50, value=25, step=1)

# --- 4. ENGINE DE CALCULS ---
if saisie_usager:
    infos_client = chercher_coordonnees_code_postal(saisie_usager)
    
    if infos_client:
        lat_client = infos_client["Latitude"]
        lon_client = infos_client["Longitude"]
        ville_client = infos_client["Ville"]
        
        st.success(f"📍 Consommateur localisé à : **{ville_client}** ({saisie_usager})")
        
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, 
            df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        df_resultat_final = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        df_resultat_final = df_resultat_final.sort_values(by='Distance du consommateur')
        
        # --- 5. AFFICHAGE VISUEL DES LOGOS ---
        st.write("---")
        st.subheader(f"🛒 Bannières disponibles dans un rayon de {rayon_max} km")
        
        if not df_resultat_final.empty:
            # On récupère les logos uniques des bannières à proximité
            bannieres_uniques = df_resultat_final.drop_duplicates(subset=['Bannière'])
            
            # Création de colonnes alignées pour afficher les logos côte à côte
            colonnes_logos = st.columns(max(len(bannieres_uniques), 2))
            
            for index, ligne in enumerate(bannieres_uniques.itertuples()):
                with colonnes_logos[index]:
                    # Essaye d'afficher le logo officiel, sinon affiche du texte
                    try:
                        st.image(ligne.Logo_URL, width=120)
                    except:
                        st.metric(label="Épicerie", value=ligne.Bannière)
            
            # --- 6. AFFICHAGE DU TABLEAU DÉTAILLÉ ---
            st.write("---")
            st.markdown("### 📋 Liste détaillée des épiceries à proximité")
            
            # Nettoyage cosmétique du tableau
            df_resultat_final['Distance du consommateur'] = df_resultat_final['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
            affichage_propre = df_resultat_final.drop(columns=['Latitude', 'Longitude', 'Logo_URL'])
            st.dataframe(affichage_propre, use_container_width=True)
        else:
            st.warning(f"Aucun commerce d'alimentation ne se situe à moins de {rayon_max} km de cette zone.")
            
else:
    st.info("👋 Saisissez un code postal complet ci-dessus pour charger l'interface de recherche par rayon.")
