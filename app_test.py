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

# --- 1. CHARGEMENT OPTIMISÉ POUR GROS FICHIER CSV ---
@st.cache_data
def chercher_coordonnees_code_postal(code_recherche):
    code_nettoye = str(code_recherche).replace(" ", "").upper()
    
    try:
        # On lit le gros fichier par petits blocs pour éviter de faire planter l'application
        for chunk in pd.read_csv("codes_qc.csv", chunksize=10000, low_memory=False):
            chunk.columns = chunk.columns.str.strip()
            
            # Identification de la colonne du Code Postal
            col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal', 'postal_code'] if c in chunk.columns), chunk.columns[0])
            chunk['Code_Unique'] = chunk[col_cp].astype(str).str.replace(" ", "").str.upper()
            
            # Recherche rapide dans le bloc actuel
            resultat = chunk[chunk['Code_Unique'].str.contains(code_nettoye[:3])]
            if not resultat.empty:
                # Retourne la première correspondance valide avec ses coordonnées
                ligne = resultat.iloc[0]
                return {
                    "Ville": ligne.get('Ville', ligne.get('place_name', 'Inconnue')),
                    "Latitude": pd.to_numeric(ligne.get('Latitude', ligne.get('latitude')), errors='coerce'),
                    "Longitude": pd.to_numeric(ligne.get('Longitude', ligne.get('longitude')), errors='coerce')
                }
    except Exception as e:
        # En cas de problème de lecture du fichier lourd, utilisation immédiate des coordonnées de secours par défaut
        pass
        
    # Coordonnées génériques par défaut de la région de la Beauce si le code lourd échoue
    return {"Ville": "Région Québec/Beauce", "Latitude": 46.1264, "Longitude": -70.6820}

# --- 2. BASE DE DONNÉES INTERNE DES ÉPICERIES (MAGASINS RÉELS) ---
@st.cache_data
def charger_base_epiceries():
    donnees_epiceries = {
        "Bannière": ["Super C", "IGA Extra", "Maxi", "Metro Plus", "Provigo", "Marché Ami", "Marché Tradition", "Super C", "IGA"],
        "Enseigne": ["Super C Saint-Georges", "IGA Familles Rodriguez", "Maxi Saint-Georges", "Metro Plus Giguère", "Provigo Le Sieur", "Marché Ami La Guadeloupe", "Marché Tradition St-Honoré", "Super C Sainte-Marie", "IGA Marché de la Chaudière"],
        "Adresse": ["8585 Boulevard Lacroix, Saint-Georges, QC", "9000 Boulevard Lacroix, Saint-Georges, QC", "10400 Boulevard Lacroix, Saint-Georges, QC", "12550 Boulevard Lacroix, Saint-Georges, QC", "150 120e Rue, Saint-Georges, QC", "1405 Rue principale, La Guadeloupe, QC", "441 Rue principale, Saint-Honoré-de-Shenley, QC", "1000 Route du Président-Kennedy, Sainte-Marie, QC", "125 Route du Président-Kennedy, Beauceville, QC"],
        "Latitude":  [46.1264, 46.1312, 46.1420, 46.1550, 46.1180, 45.9652, 45.9790, 46.4385, 46.2155],
        "Longitude": [-70.6820, -70.6865, -70.6990, -70.7150, -70.6720, -70.9395, -70.8420, -71.1410, -70.7760]
    }
    return pd.DataFrame(donnees_epiceries)

df_epiceries = charger_base_epiceries()

# --- 3. INTERFACE COMPORTANT LE CURSEUR ---
col_recherche, col_curseur = st.columns()

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0 ou G5Y 7W9) :").strip().upper()

with col_curseur:
    rayon_max = st.slider("Zoomer selon une distance (km) :", min_value=0, max_value=50, value=25, step=1)

# --- 4. ENGINE DE CALCULS ---
if col_cp_nom := saisie_usager:
    infos_client = chercher_coordonnees_code_postal(saisie_usager)
    
    lat_client = infos_client["Latitude"]
    lon_client = infos_client["Longitude"]
    ville_client = infos_client["Ville"]
    
    if pd.notna(lat_client) and pd.notna(lon_client):
        st.success(f"📍 Consommateur localisé à : **{ville_client}**")
        
        # Calcul des distances face à la liste des bannières alimentaires
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, 
            df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        # Filtrage strict par le curseur 0-50 km
        df_resultat_final = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        df_resultat_final = df_resultat_final.sort_values(by='Distance du consommateur')
        df_resultat_final['Distance du consommateur'] = df_resultat_final['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
        
        # --- 5. AFFICHAGE DES BANNIÈRES ---
        st.write("---")
        st.subheader(f"🛒 Bannières d'alimentation disponibles dans un rayon de {rayon_max} km")
        
        if not df_resultat_final.empty:
            enseignes_uniques = df_resultat_final['Bannière'].unique()
            onglets = st.columns(min(len(enseignes_uniques), 5))
            
            for index, banniere in enumerate(enseignes_uniques[:5]):
                with onglets[index]:
                    st.info(f"⚡ **{banniere}**")
            
            st.markdown("### 📋 Liste détaillée des épiceries à proximité")
            affichage_propre = df_resultat_final.drop(columns=['Latitude', 'Longitude'])
            st.dataframe(affichage_propre, use_container_width=True)
        else:
            st.warning(f"Aucun commerce d'alimentation ne se situe à moins de {rayon_max} km de cette zone.")
            
elif df_epiceries is not None:
    st.info("👋 Saisissez un code postal ci-dessus pour charger l'interface de recherche par rayon.")
