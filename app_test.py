import pandas as pd
import streamlit as st
import numpy as np
import urllib.parse
import os

st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Moteur géospatiale basé sur la localisation précise des épiceries et marchés du Québec.")

# --- FORMULE DE CALCUL DE DISTANCE GPS ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. CHARGEMENT GLOBAL DE VOTRE LISTE DE CODES POSTAUX (POUR SITUER L'UTILISATEUR) ---
@st.cache_data
def charger_tous_les_codes_qc():
    fichier_csv = "codes_qc.csv"
    if not os.path.exists(fichier_csv):
        st.error(f"❌ Le fichier '{fichier_csv}' est introuvable dans le dossier.")
        return None
    try:
        df = pd.read_csv(fichier_csv, low_memory=False)
        df.columns = df.columns.str.strip()
        
        col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal', 'postal_code'] if c in df.columns), df.columns[0])
        col_ville = next((c for c in ['Ville', 'ville', 'place_name', 'Municipalité'] if c in df.columns), 'Ville')
        col_lat = next((c for c in ['Latitude', 'latitude'] if c in df.columns), 'Latitude')
        col_lon = next((c for c in ['Longitude', 'longitude'] if c in df.columns), 'Longitude')
        
        df['Code_Strict'] = df[col_cp].astype(str).str.replace(" ", "").str.upper()
        df['Latitude'] = pd.to_numeric(df[col_lat], errors='coerce')
        df['Longitude'] = pd.to_numeric(df[col_lon], errors='coerce')
        df['Ville_Propre'] = df[col_ville].astype(str).str.strip()
        
        return df[['Code_Strict', 'Ville_Propre', 'Latitude', 'Longitude']]
    except Exception as e:
        st.error(f"Erreur lors de la lecture de codes_qc.csv : {e}")
        return None

df_codes_global = charger_tous_les_codes_qc()

# --- 2. NOUVEAU : CHARGEMENT DE VOTRE LISTE D'ÉPICERIES EXTRAITES AVEC LEURS ADRESSES ---
@st.cache_data
def charger_adresses_epiceries():
    # Remplacez par le nom exact du nouveau fichier contenant les adresses extraites
    fichier_csv = "adresses_magasins_qc.csv" 
    if not os.path.exists(fichier_csv):
        st.error(f"❌ Le fichier '{fichier_csv}' contenant les adresses extraites est introuvable.")
        return None
    try:
        df = pd.read_csv(fichier_csv, low_memory=False)
        df.columns = df.columns.str.strip()
        
        # Standardisation du code postal de l'épicerie pour la liaison GPS
        col_cp_magasin = next((c for c in ['code_postal', 'Code postal', 'Code_Postal'] if c in df.columns), None)
        if col_cp_magasin:
            df['Code_Strict'] = df[col_cp_magasin].astype(str).str.replace(" ", "").str.upper()
        else:
            st.error("❌ Impossible de trouver la colonne du code postal dans le fichier des épiceries.")
            return None
            
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier d'épiceries : {e}")
        return None

df_epiceries = charger_adresses_epiceries()

# --- CONFIGURATION DES LIENS DE CIRCULAIRES ---
LIENS_BANNIERES = {
    "IGA": "https://iga.net", "Maxi": "https://maxi.ca", "Metro": "https://metro.ca",
    "Super C": "https://superc.ca", "Walmart": "https://walmart.ca", "Tigre Geant": "https://tigregeant.com",
    "Dollarama": "https://dollarama.com", "Provigo": "https://provigo.ca", "Costco": "https://costco.ca",
    "Marché Ami": "https://marcheami.ca", "Marché Tradition": "https://marchestradition.com"
}

# --- 3. INTERFACE UTILISATEUR ---
col_recherche, col_curseur = st.columns(2)

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0, G5Y 7W9) :").strip().upper()

with col_curseur:
    rayon_max = st.slider("Agrandir le rayon de recherche en kilomètres :", min_value=0, max_value=100, value=25, step=5)

# --- 4. CALCULS GÉOSPATIAUX ET RECHERCHE ---
if saisie_usager and df_codes_global is not None and df_epiceries is not None:
    code_client_strict = saisie_usager.replace(" ", "")
    
    # Étape A : Trouver la position GPS du consommateur
    ligne_client = df_codes_global[df_codes_global['Code_Strict'] == code_client_strict]
    
    if not ligne_client.empty:
        lat_client = ligne_client.iloc[0]['Latitude']
        lon_client = ligne_client.iloc[0]['Longitude']
        ville_client = ligne_client.iloc[0]['Ville_Propre']
        
        st.success(f"📍 Position identifiée : **{ville_client}** ({saisie_usager})")
        
        # Étape B : Associer les coordonnées GPS (Latitude/Longitude) à chaque magasin
        # On fusionne notre liste de magasins avec le référentiel des codes postaux pour avoir les positions GPS des magasins
        df_magasins_gps = pd.merge(
            df_epiceries, 
            df_codes_global[['Code_Strict', 'Latitude', 'Longitude']], 
            on='Code_Strict', 
            how='inner'
        )
        
        # Étape C : Calculer la distance entre le client et chaque épicerie
        df_magasins_gps['Distance'] = calculer_distance(
            lat_client, lon_client, df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        # Étape D : Filtrer selon le rayon de kilomètres choisi
        df_resultat_filtré = df_magasins_gps[df_magasins_gps['Distance'] <= rayon_max].copy()
        df_resultat_filtré = df_resultat_filtré.sort_values(by='Distance')
        
        if not df_resultat_filtré.empty:
            # --- AFFICHAGE DE LA CARTE ---
            st.write("### 🗺️ Emplacement des magasins à proximité")
            # Renommer temporairement pour st.map qui requiert obligatoirement 'latitude' et 'longitude' en minuscules
            df_map = df_resultat_filtré[['Latitude', 'Longitude']].rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude'}).drop_duplicates()
            st.map(df_map)
            
            st.write("---")
            st.subheader(f"📋 Épiceries trouvées dans votre rayon de {rayon_max} km ({len(df_resultat_filtré)} options)")
            
            # Préparation des données d'affichage
            df_affichage = pd.DataFrame()
            
            # Identifier dynamiquement le nom de la bannière (s'il y a une colonne 'Banniere' ou 'nom')
            col_banniere = next((c for c in ['Bannière', 'banniere', 'Nom', 'nom', 'nom_entreprise'] if c in df_resultat_filtré.columns), df_resultat_filtré.columns[0])
            col_adresse = next((c for c in ['adresse_complete', 'adresse', 'Adresse'] if c in df_resultat_filtré.columns), df_resultat_filtré.columns[1])
            
            df_affichage['Bannière'] = df_resultat_filtré[col_banniere]
            df_affichage['Adresse complète'] = df_resultat_filtré[col_adresse]
            df_affichage['Distance estimée'] = df_resultat_filtré['Distance'].apply(lambda x: f"{x:.1f} km" if x > 0.1 else "Dans votre secteur")
            
            # Génération des liens dynamiques
            df_affichage['Site Web / Circulaire'] = df_affichage['Bannière'].apply(lambda x: LIENS_BANNIERES.get(x, "https://google.com"))
            df_affichage['Itinéraire'] = df_affichage['Adresse complète'].apply(lambda x: f"https://google.com{urllib.parse.quote(x)}")
            
            # Rendu du tableau dynamique
            st.data_editor(
                df_affichage,
                column_config={
                    "Site Web / Circulaire": st.column_config.LinkColumn("Circulaire 🌐", display_text="Ouvrir les rabais"),
                    "Itinéraire": st.column_config.LinkColumn("Route 🚗", display_text="Calculer l'itinéraire"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning(f"⚠️ Aucun magasin trouvé dans un rayon de {rayon_max} km autour de votre position.")
    else:
        st.error("❌ Ce code postal n'est pas reconnu dans votre fichier codes_qc.csv.")
