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

# --- 1. CHARGEMENT OPTIMISÉ AVEC RECHERCHE STRICTE SUR 6 CARACTÈRES ---
@st.cache_data
def chercher_coordonnees_code_postal(code_recherche):
    # Nettoyage complet (ex: "G0M 1G0" -> "G0M1G0")
    code_nettoye = str(code_recherche).replace(" ", "").upper()
    
    try:
        # Lecture par blocs pour digérer le gros fichier sans planter
        for chunk in pd.read_csv("codes_qc.csv", chunksize=20000, low_memory=False):
            chunk.columns = chunk.columns.str.strip()
            
            # Repérage de la colonne de code postal
            col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal', 'postal_code'] if c in chunk.columns), chunk.columns[1])
            
            # Création d'une colonne propre sans espace pour comparer les 6 caractères
            chunk['Code_Unique_Strict'] = chunk[col_cp].astype(str).str.replace(" ", "").str.upper()
            
            # RECHERCHE EXACTE : On cherche la correspondance parfaite sur les 6 caractères
            resultat = chunk[chunk['Code_Unique_Strict'] == code_nettoye]
            
            # Si l'utilisateur n'a tapé que 3 lettres (ex: G0M), on prend la première municipalité par défaut
            if resultat.empty and len(code_nettoye) == 3:
                resultat = chunk[chunk['Code_Unique_Strict'].str.startswith(code_nettoye)]
                
            if not resultat.empty:
                premiere_ligne = resultat.iloc[0]
                
                # Récupération dynamique du nom de la ville
                col_ville = next((c for c in ['Ville', 'ville', 'place_name'] if c in chunk.columns), 'Ville')
                col_lat = next((c for c in ['Latitude', 'latitude'] if c in chunk.columns), 'Latitude')
                col_lon = next((c for c in ['Longitude', 'longitude'] if c in chunk.columns), 'Longitude')
                
                return {
                    "Ville": premiere_ligne.get(col_ville, "Inconnue"),
                    "Latitude": pd.to_numeric(premiere_ligne.get(col_lat), errors='coerce'),
                    "Longitude": pd.to_numeric(premiere_ligne.get(col_lon), errors='coerce')
                }
    except Exception as e:
        st.error(f"Erreur technique de lecture : {e}")
        
    return None

# --- 2. BASE DE DONNÉES INTERNE DES ÉPICERIES ---
@st.cache_data
def charger_base_epiceries():
    donnees_epiceries = {
        "Bannière": ["Marché Ami", "Marché Tradition", "Super C", "IGA Extra", "Maxi", "Metro Plus", "Provigo", "Super C", "IGA"],
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
    
    if infos_client and pd.notna(infos_client["Latitude"]) and pd.notna(infos_client["Longitude"]):
        lat_client = infos_client["Latitude"]
        lon_client = infos_client["Longitude"]
        ville_client = infos_client["Ville"]
        
        st.success(f"📍 Consommateur localisé à : **{ville_client}** ({saisie_usager})")
        
        # Calcul des distances réelles face à notre base de magasins d'alimentation
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, 
            df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        # Filtrage strict par le curseur 0-50 km
        df_resultat_final = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        df_resultat_final = df_resultat_final.sort_values(by='Distance du consommateur')
        
        # Formatage de l'affichage de la distance
        df_resultat_final['Distance du consommateur'] = df_resultat_final['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
        
        # --- 5. AFFICHAGE DES BANNIÈRES ---
        st.write("---")
        st.subheader(f"🛒 Bannières d'alimentation disponibles dans un rayon de {rayon_max} km")
        
        if not df_resultat_final.empty:
            enseignes_uniques = df_resultat_final['Bannière'].unique()
            
            # Disposition dynamique des bannières trouvées
            onglets = st.columns(len(enseignes_uniques))
            for index, banniere in enumerate(enseignes_uniques):
                with onglets[index]:
                    st.info(f"⚡ **{banniere}**")
            
            st.markdown("### 📋 Liste détaillée des épiceries à proximité")
            affichage_propre = df_resultat_final.drop(columns=['Latitude', 'Longitude'])
            st.dataframe(affichage_propre, use_container_width=True)
        else:
            st.warning(f"Aucun commerce d'alimentation ne se situe à moins de {rayon_max} km de cette zone.")
            
    else:
        st.error("Code postal introuvable dans la base de données. Assurez-vous d'entrer les 6 caractères (ex: G0M 1G0).")
            
else:
    st.info("👋 Saisissez un code postal complet ci-dessus pour charger l'interface de recherche par rayon.")
