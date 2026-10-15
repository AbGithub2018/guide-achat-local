import pandas as pd
import streamlit as st
import numpy as np
import urllib.parse
import os

st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Prototype de recherche géospatiale par code postal, rayon de distance et filtrage de bannières.")

# --- FORMULE DE CALCUL DE DISTANCE GPS ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. RECHERCHE ULTRA-PRÉCISE ET RAPIDE DANS VOTRE GROS CSV ---
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
                # Correction mineure ici : utiliser .iloc[0] au lieu de .iloc pour extraire proprement les valeurs de la ligne
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

# --- 2. BASE DE DONNÉES RÉELLE DES ÉPICERIES DE LA BEAUCE ---
@st.cache_data
def charger_base_epiceries():
    donnees_epiceries = {
        "Bannière": ["Marché Ami", "Marché Tradition", "IGA Extra", "IGA", "Super C", "Maxi", "IGA", "Super C"],
        "Site Web": [
            "https://marcheami.ca", "https://www.marchestradition.com/fr/stores/les-marches-tradition-10/",
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

# --- 3. INTERFACE UTILISATEUR ---
col_recherche, col_curseur = st.columns(2)

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0, G5Y 7W9) :").strip().upper()

with col_curseur:
    rayon_max = st.slider("Zoomer selon une distance (km) :", min_value=0, max_value=50, value=25, step=1)

# --- 4. ENGINE DE CALCULS DYNAMIQUE ---
if saisie_usager:
    infos_client = chercher_coordonnees_csv_strict(saisie_usager)
    
    # Secours démo
    if not infos_client and saisie_usager.replace(" ", "") == "G0M1G0":
        infos_client = {"Ville": "La Guadeloupe", "Latitude": 45.9652, "Longitude": -70.9395}
    elif not infos_client and saisie_usager.replace(" ", "") == "G5Y7W9": # Ajout d'un secours pour Saint-Georges
        infos_client = {"Ville": "Saint-Georges", "Latitude": 46.1180, "Longitude": -70.6713}
        
    if infos_client and pd.notna(infos_client["Latitude"]) and pd.notna(infos_client["Longitude"]):
        lat_client = infos_client["Latitude"]
        lon_client = infos_client["Longitude"]
        ville_client = infos_client["Ville"]
        
        st.success(f"📍 Position exacte trouvée : **{ville_client}** ({saisie_usager})")
        
        # Étape A : Calcul des distances initiales
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        # Étape B : Premier filtrage selon le RAYON choisi
        df_dans_rayon = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        
        if not df_dans_rayon.empty:
            # Étape C : EXTRACTION DYNAMIQUE DES BANNIÈRES DISPONIBLES DANS CE RAYON
            bannieres_dispo_locales = sorted(df_dans_rayon['Bannière'].unique())
            
            # Étape D : Affichage du filtre MULTISELECT (les bannières sont cochées par défaut)
            bannieres_selectionnees = st.multiselect(
                "Filtrer par enseigne/bannière disponible à proximité :",
                options=bannieres_dispo_locales,
                default=bannieres_dispo_locales
            )
            
            # Étape E : Filtrage final selon les bannières cochées
            df_resultat_final = df_dans_rayon[df_dans_rayon['Bannière'].isin(bannieres_selectionnees)].copy()
            df_resultat_final = df_resultat_final.sort_values(by='Distance du consommateur')
            
            if not df_resultat_final.empty:
                # Liens GPS et affichage
                df_resultat_final['Itinéraire GPS'] = df_resultat_final['Adresse'].apply(
                    lambda addr: f"https://google.com/maps/search/?api=1&query={urllib.parse.quote(addr)}")        
                df_resultat_final['Site Web'] = df_resultat_final['Site Web'].astype(str)
                
                # --- VISUALISATION CARTE INTERACTIVE ---
                st.write("### 🗺️ Carte des épiceries sélectionnées")
                # Format requis pour st.map : un DataFrame contenant 'latitude' et 'longitude'
                df_map = df_resultat_final[['Latitude', 'Longitude']].rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'})
                st.map(df_map)
                
                st.write("---")
                st.subheader(f"📋 Épiceries correspondantes ({len(df_resultat_final)} trouvées)")
                
                # Formatage de la distance pour l'affichage textuel propre
                df_affichage = df_resultat_final.copy()
                df_affichage['Distance du consommateur'] = df_affichage['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
                
                affichage_propre = df_affichage[['Bannière', 'Site Web', 'Enseigne', 'Adresse', 'Distance du consommateur', 'Itinéraire GPS']]
                
                st.data_editor(
                    affichage_propre,
                    column_config={
                        "Site Web": st.column_config.LinkColumn("Outil Localisateur 🌐", display_text="Trouver le magasin local"),
                        "Itinéraire GPS": st.column_config.LinkColumn("S'y rendre 🚗", display_text="🗺️ Google Maps"),
                    },
                    disabled=True,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Veuillez sélectionner au moins une bannière pour afficher les résultats.")
        else:
            st.warning(f"Aucun commerce d'alimentation ne se situe à moins de {rayon_max} km de cette zone précise.")
    else:
        st.error(f"Le code postal '{saisie_usager}' est introuvable ou mal formaté.")
else:
    st.info("👋 Saisissez un code postal complet pour lancer le moteur de recherche géospatial.")
