import pandas as pd
import streamlit as st
import numpy as np
import urllib.parse
import os

st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Moteur géospatiale basé exclusivement sur la matrice officielle des codes postaux et des municipalités du Québec.")

# --- FORMULE DE CALCUL DE DISTANCE GPS ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. CHARGEMENT GLOBAL DE VOTRE LISTE DE CODES POSTAUX ET MUNICIPALITÉS ---
@st.cache_data
def charger_tous_les_codes_qc():
    fichier_csv = "codes_qc.csv"
    if not os.path.exists(fichier_csv):
        st.error(f"❌ Le fichier '{fichier_csv}' est introuvable dans le dossier.")
        return None
    try:
        # Tente d'abord de lire avec une virgule, si ça échoue, tente le point-virgule d'Excel
        try:
            df = pd.read_csv(fichier_csv, low_memory=False, sep=',')
            if len(df.columns) <= 1:
                df = pd.read_csv(fichier_csv, low_memory=False, sep=';')
        except:
            df = pd.read_csv(fichier_csv, low_memory=False, sep=';')
            
        df.columns = df.columns.str.strip()
        
        # Identification automatique des colonnes clés
        col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal', 'postal_code'] if c in df.columns), df.columns[0])
        col_ville = next((c for c in ['Ville', 'ville', 'place_name', 'Municipalité'] if c in df.columns), 'Ville')
        col_lat = next((c for c in ['Latitude', 'latitude'] if c in df.columns), None)
        col_lon = next((c for c in ['Longitude', 'longitude'] if c in df.columns), None)
        
        if not col_lat or not col_lon:
            st.error(f"❌ Impossible de trouver les colonnes de Latitude/Longitude. Colonnes détectées : {list(df.columns)}")
            return None
        
        # Nettoyage et standardisation
        df['Code_Strict'] = df[col_cp].astype(str).str.replace(" ", "").str.upper()
        df['Latitude'] = pd.to_numeric(df[col_lat], errors='coerce')
        df['Longitude'] = pd.to_numeric(df[col_lon], errors='coerce')
        df['Ville_Propre'] = df[col_ville].astype(str).str.strip()
        
        return df[['Code_Strict', 'Ville_Propre', 'Latitude', 'Longitude']]
    except Exception as e:
        st.error(f"Erreur lors de la lecture de codes_qc.csv : {e}")
        return None

df_codes_global = charger_tous_les_codes_qc()

# --- 2. CHARGEMENT DE VOTRE MATRICE DE DISPONIBILITÉS (1-0) ---
@st.cache_data
def charger_disponibilites_magasins():
    fichier_csv = "disponibilite_magasins.csv"
    if not os.path.exists(fichier_csv):
        st.error(f"❌ Le fichier '{fichier_csv}' est introuvable.")
        return None
    try:
        # Même sécurité de séparateur pour le fichier des magasins
        try:
            df = pd.read_csv(fichier_csv, low_memory=False, sep=',')
            if len(df.columns) <= 1:
                df = pd.read_csv(fichier_csv, low_memory=False, sep=';')
        except:
            df = pd.read_csv(fichier_csv, low_memory=False, sep=';')
            
        df.columns = df.columns.str.strip()
        # On utilise la première colonne pour l'indexation des codes postaux des magasins
        df['Code_Strict'] = df[df.columns[0]].astype(str).str.replace(" ", "").str.upper()
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture de disponibilite_magasins.csv : {e}")
        return None

df_matrice_bannieres = charger_disponibilites_magasins()

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

# --- 4. CALCULS GÉOSPATIAUX DYNAMIQUES ---
if saisie_usager and df_codes_global is not None and df_matrice_bannieres is not None:
    code_client_strict = saisie_usager.replace(" ", "")
    
    # Étape A : Trouver la position GPS du code postal de l'usager
    ligne_client = df_codes_global[df_codes_global['Code_Strict'] == code_client_strict]
    
    if not ligne_client.empty:
        lat_client = ligne_client.iloc[0]['Latitude']
        lon_client = ligne_client.iloc[0]['Longitude']
        ville_client = ligne_client.iloc[0]['Ville_Propre']
        
        st.success(f"📍 Position identifiée : **{ville_client}** ({saisie_usager})")
        
        # Étape B : Associer les coordonnées GPS à chaque code postal présent dans votre fichier magasin
        codes_configures = df_matrice_bannieres['Code_Strict'].unique()
        df_magasins_gps = df_codes_global[df_codes_global['Code_Strict'].isin(codes_configures)].copy()
        
        # Étape C : Calculer la distance entre le client et toutes les localisations de la matrice
        df_magasins_gps['Distance'] = calculer_distance(
            lat_client, lon_client, df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        # Étape D : Filtrer selon le rayon choisi par l'utilisateur
        df_zones_dans_rayon = df_magasins_gps[df_magasins_gps['Distance'] <= rayon_max].copy()
        
        # Étape E : Extraire les bannières actives (marquées '1') pour les codes postaux dans le rayon
        liste_magasins_trouves = []
        
        for index, zone in df_zones_dans_rayon.iterrows():
            code_zone = zone['Code_Strict']
            distance_zone = zone['Distance']
            nom_municipalite = zone['Ville_Propre']
            
            ligne_matrice = df_matrice_bannieres[df_matrice_bannieres['Code_Strict'] == code_zone]
            
            if not ligne_matrice.empty:
                donnees_bannieres = ligne_matrice.iloc[0]
                
                for colonne in df_matrice_bannieres.columns:
                    # On ignore les colonnes d'identifiants techniques pour ne scanner que les bannières
                    if colonne not in ['Code postal', 'code_postal', 'Code_Strict', df_matrice_bannieres.columns[0]]:
                        valeur = str(donnees_bannieres[colonne]).strip()
                        if valeur in ["1", "1.0"]:
                            liste_magasins_trouves.append({
                                "Bannière": colonne,
                                "Municipalité / Secteur": nom_municipalite,
                                "Code Postal": code_zone,
                                "Distance estimée": distance_zone,
                                "Site Web / Circulaire": LIENS_BANNIERES.get(colonne, "https://google.com"),
                                "Itinéraire": f"https://google.com{urllib.parse.quote(f'{nom_municipalite}, {code_zone}, QC')}",
                                "latitude": zone['Latitude'],
                                "longitude": zone['Longitude']
                            })
        
        if liste_magasins_trouves:
            df_resultat_final = pd.DataFrame(liste_magasins_trouves)
            df_resultat_final = df_resultat_final.sort_values(by='Distance estimée')
            
            # --- AFFICHAGE DE LA CARTE ---
            st.write("### 🗺️ Carte des municipalités desservies à proximité")
            df_map = df_resultat_final[['latitude', 'longitude']].drop_duplicates()
            st.map(df_map)
            
            st.write("---")
            st.subheader(f"📋 Épiceries accessibles dans votre rayon de {rayon_max} km ({len(df_resultat_final)} options trouvées)")
            
            # Formatage de la distance pour l'affichage textuel
            df_affichage = df_resultat_final.copy()
            df_affichage['Distance estimée'] = df_affichage['Distance estimée'].apply(lambda x: f"{x:.1f} km" if x > 0.1 else "Dans votre secteur")
            
            st.data_editor(
                df_affichage[['Bannière', 'Municipalité / Secteur', 'Code Postal', 'Distance estimée', 'Site Web / Circulaire', 'Itinéraire']],
                column_config={
                    "Site Web / Circulaire": st.column_config.LinkColumn("Circulaire 🌐", display_text="Ouvrir les rabais"),
                    "Itinéraire": st.column_config.LinkColumn("Route 🚗", display_text="Calculer l'itinéraire"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning(f"⚠️ Aucun magasin configuré n'a été trouvé dans un rayon de {rayon_max} km autour de votre position.")
    else:
        st.error("❌ Ce code postal n'est pas reconnu dans votre fichier codes_qc.csv.")
