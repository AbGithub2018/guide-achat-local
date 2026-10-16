import pandas as pd
import streamlit as st
import numpy as np
import urllib.parse
import os

st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Prototype de recherche géospatiale combinant calcul de distance par rayon GPS et validation des bannières locales.")

# --- FORMULE DE CALCUL DE DISTANCE GPS ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. CHARGEMENT ET RECHERCHE GPS DU CONSOMMATEUR ---
@st.cache_data
def chercher_coordonnees_csv_strict(code_recherche):
    code_nettoye = str(code_recherche).replace(" ", "").upper()
    if not os.path.exists("codes_qc.csv"):
        return None
    try:
        for chunk in pd.read_csv("codes_qc.csv", chunksize=50000, low_memory=False):
            chunk.columns = chunk.columns.str.strip()
            col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal', 'postal_code'] if c in chunk.columns), chunk.columns[0])
            chunk['Code_Strict'] = chunk[col_cp].astype(str).str.replace(" ", "").str.upper()
            resultat = chunk[chunk['Code_Strict'] == code_nettoye]
            if not resultat.empty:
                ligne = resultat.iloc[0]
                col_ville = next((c for c in ['Ville', 'ville', 'place_name'] if c in chunk.columns), 'Ville')
                col_lat = next((c for c in ['Latitude', 'latitude'] if c in chunk.columns), 'Latitude')
                col_lon = next((c for c in ['Longitude', 'longitude'] if c in chunk.columns), 'Longitude')
                return {
                    "Ville": ligne.get(col_ville, "Inconnue"),
                    "Latitude": pd.to_numeric(ligne.get(col_lat), errors='coerce'),
                    "Longitude": pd.to_numeric(ligne.get(col_lon), errors='coerce')
                }
    except Exception:
        pass
    return None

# --- 2. CHARGEMENT DE VOTRE MATRICE DE DISPONIBILITÉS ---
@st.cache_data
def charger_disponibilites_magasins():
    fichier_csv = "disponibilite_magasins.csv"
    if not os.path.exists(fichier_csv):
        return None
    try:
        df = pd.read_csv(fichier_csv, low_memory=False)
        df.columns = df.columns.str.strip()
        col_cp = df.columns[0]
        df['Code_Strict'] = df[col_cp].astype(str).str.replace(" ", "").str.upper()
        return df
    except Exception:
        return None

df_matrice_bannieres = charger_disponibilites_magasins()

# --- 3. BASE DE DONNÉES RÉELLE DES ÉPICERIES DU QUÉBEC ---
@st.cache_data
def charger_base_epiceries():
    donnees_epiceries = {
        "Bannière": ["Marché Ami", "Marché Tradition", "IGA Extra", "IGA", "Super C", "Maxi", "IGA", "Super C"],
        "Site Web": [
            "https://marcheami.ca", "https://marchestradition.com",
            "https://iga.net", "https://iga.net", "https://superc.ca", "https://maxi.ca", "https://iga.net", "https://superc.ca"
        ],
        "Enseigne": [
            "Marché Ami La Guadeloupe", "Marché Tradition St-Honoré", "IGA Extra Saint-Georges (Lacroix)", 
            "IGA Rodrigue et Filles (Dionne)", "Super C Saint-Georges", "Maxi Saint-Georges", "IGA Beauceville", "Super C Sainte-Marie"
        ],
        "Adresse": [
            "1405 Rue principale, La Guadeloupe, QC", "441 Rue principale, Saint-Honoré-de-Shenley, QC", 
            "8980 Boulevard Lacroix, Saint-Georges, QC", "1950 Boulevard Dionne, Saint-Georges, QC", 
            "8585 Boulevard Lacroix, Saint-Georges, QC", "10400 Boulevard Lacroix, Saint-Georges, QC",
            "630 Boulevard Renault, Beauceville, QC", "1000 Route du Président-Kennedy, Sainte-Marie, QC"
        ],
        "Latitude":  [45.9652, 45.9790, 46.1312, 46.1090, 46.1264, 46.1420, 46.2155, 46.4385],
        "Longitude": [-70.9395, -70.8420, -70.6865, -70.7035, -70.6820, -70.6990, -70.7760, -71.1410]
    }
    return pd.DataFrame(donnees_epiceries)

df_epiceries = charger_base_epiceries()

# --- 4. INTERFACE UTILISATEUR ---
col_recherche, col_curseur = st.columns(2)

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0, G5Y 7W9) :").strip().upper()

with col_curseur:
    rayon_max = st.slider("Agrandir le rayon de recherche en kilomètres (Gaspésie, régions éloignées) :", min_value=0, max_value=100, value=25, step=5)

# --- 5. ENGIN DE CALCULS ET FILTRAGE SPATIAL ---
if saisie_usager:
    infos_client = chercher_coordonnees_csv_strict(saisie_usager)
    
    code_sans_espace = saisie_usager.replace(" ", "")
    if not infos_client and code_sans_espace == "G0M1G0":
        infos_client = {"Ville": "La Guadeloupe", "Latitude": 45.9652, "Longitude": -70.9395}
    elif not infos_client and code_sans_espace == "G0A0A0":
        infos_client = {"Ville": "Portneuf", "Latitude": 46.7022, "Longitude": -71.8845}

    if infos_client and pd.notna(infos_client["Latitude"]) and pd.notna(infos_client["Longitude"]):
        lat_client = infos_client["Latitude"]
        lon_client = infos_client["Longitude"]
        ville_client = infos_client["Ville"]
        
        st.success(f"📍 Position identifiée : **{ville_client}** ({saisie_usager})")
        
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        df_dans_rayon = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        
        if df_matrice_bannieres is not None:
            ligne_matrice = df_matrice_bannieres[df_matrice_bannieres['Code_Strict'] == code_sans_espace]
            if not ligne_matrice.empty:
                donnees_zone = ligne_matrice.iloc[0]
                bannieres_valides = [col for col in df_matrice_bannieres.columns if col not in ['Code postal', 'code_postal', 'Code_Strict'] and str(donnees_zone[col]).strip() == "1"]
                df_dans_rayon = df_dans_rayon[df_dans_rayon['Bannière'].isin(bannieres_valides)]
        
        if not df_dans_rayon.empty:
            df_dans_rayon = df_dans_rayon.sort_values(by='Distance du consommateur')
            df_dans_rayon['Itinéraire GPS'] = df_dans_rayon['Adresse'].apply(
                lambda addr: f"https://google.com{urllib.parse.quote(addr)}")        
            
            st.write("### 🗺️ Carte des épiceries à proximité")
            df_map = df_dans_rayon[['Latitude', 'Longitude']].rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'})
            st.map(df_map)
            
            st.write("---")
            st.subheader(f"📋 Épiceries accessibles dans un rayon de {rayon_max} km ({len(df_dans_rayon)} trouvées)")
            
            df_affichage = df_dans_rayon.copy()
            df_affichage['Distance du consommateur'] = df_affichage['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
            
            st.data_editor(
                df_affichage[['Bannière', 'Enseigne', 'Adresse', 'Distance du consommateur', 'Site Web', 'Itinéraire GPS']],
                column_config={
                    "Site Web": st.column_config.LinkColumn("Circulaire 🌐", display_text="Voir le magasin"),
                    "Itinéraire GPS": st.column_config.LinkColumn("Route 🚗", display_text="Calculer l'itinéraire"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning(f"⚠️ Aucun magasin trouvé dans un rayon de {rayon_max} km avec des rabais configurés pour cette zone.")
    else:
        st.error("❌ Impossible de géolocaliser ce code postal.")
