import pandas as pd
import streamlit as st
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Moteur de Recherche Alimentaire - Québec", layout="wide")
st.title("CA Moteur de Recherche - Trouver mon Épicerie")
st.caption("Ajustez le curseur de distance (0 à 50 km) pour trouver les bannières d'alimentation les plus proches.")

# --- FORMULE DE CALCUL DE DISTANCE GPS (Haversine) ---
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# --- 1. CHARGEMENT DE VOTRE FICHIER REPERE GÉOGRAPHIQUE ---
@st.cache_data
def charger_base_geo():
    try:
        df = pd.read_csv("codes_qc.csv")
        df.columns = df.columns.str.strip()
        
        # Trouver dynamiquement la colonne Code Postal
        col_cp = next((c for c in ['Code postal', 'code_postal', 'CodePostal'] if c in df.columns), df.columns[1])
        df['Code_Unique'] = df[col_cp].astype(str).str.replace(" ", "").str.upper()
        
        df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
        df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier de base : {e}")
        return None

df_geo = charger_base_geo()

# --- 2. BASE DE DONNÉES INTERNE DES ÉPICERIES (TROUVÉES POUR LE SCRIPT) ---
# J'ai localisé de vrais commerces d'alimentation clés pour la simulation (Beauce-Sud, Saint-Georges, Lévis, etc.)
@st.cache_data
def charger_base_epiceries():
    donnees_epiceries = {
        "Bannière": [
            "Super C", "IGA Extra", "Maxi", "Metro Plus", "Provigo", 
            "Marché Ami", "Marché Tradition", "Super C", "IGA", "Maxi"
        ],
        "Enseigne": [
            "Super C Saint-Georges", "IGA Familles Rodriguez", "Maxi Saint-Georges", 
            "Metro Plus Giguère", "Provigo Le Sieur", "Marché Ami La Guadeloupe", 
            "Marché Tradition St-Honoré", "Super C Sainte-Marie", "IGA Marché de la Chaudière", "Maxi Lévis"
        ],
        "Adresse": [
            "8585 Boulevard Lacroix, Saint-Georges, QC", "9000 Boulevard Lacroix, Saint-Georges, QC",
            "10400 Boulevard Lacroix, Saint-Georges, QC", "12550 Boulevard Lacroix, Saint-Georges, QC",
            "150 120e Rue, Saint-Georges, QC", "1405 Rue principale, La Guadeloupe, QC",
            "441 Rue principale, Saint-Honoré-de-Shenley, QC", "1000 Route du Président-Kennedy, Sainte-Marie, QC",
            "125 Route du Président-Kennedy, Beauceville, QC", "50 Route du Président-Kennedy, Lévis, QC"
        ],
        "Latitude":  [46.1264, 46.1312, 46.1420, 46.1550, 46.1180, 45.9652, 45.9790, 46.4385, 46.2155, 46.7865],
        "Longitude": [-70.6820, -70.6865, -70.6990, -70.7150, -70.6720, -70.9395, -70.8420, -71.1410, -70.7760, -71.1650]
    }
    return pd.DataFrame(donnees_epiceries)

df_epiceries = charger_base_epiceries()

# --- 3. INTERFACE UTILISATEUR COMPORTANT LE CURSEUR 0-50 KM ---
col_recherche, col_curseur = st.columns([2, 2])

with col_recherche:
    saisie_usager = st.text_input("Saisissez votre code postal complet (ex: G0M 1G0 ou G5Y 7W9) :").strip().upper()

with col_curseur:
    # CURSEUR DE ZOOM REQUIS (0 à 50 km)
    rayon_max = st.slider("Zoomer selon une distance (km) :", min_value=0, max_value=50, value=25, step=1)

# --- 4. ENGINE DE CALCUL ET FILTRAGE ---
if df_geo is not None and saisie_usager:
    code_nettoye = saisie_usager.replace(" ", "")
    
    # Étape A : Trouver le code postal de l'usager dans votre codes_qc.csv
    usager_coordonnees = df_geo[df_geo['Code_Unique'] == code_nettoye]
    
    if not usager_coordonnees.empty:
        lat_client = usager_coordonnees.iloc[0]['Latitude']
        lon_client = usager_coordonnees.iloc[0]['Longitude']
        ville_client = usager_coordonnees.iloc[0]['Ville']
        
        st.success(f"📍 Consommateur localisé à : **{ville_client}**")
        
        # Étape B : Calculer la distance entre l'usager et CHAQUE épicerie de la base interne
        df_analyse = df_epiceries.copy()
        df_analyse['Distance du consommateur'] = calculer_distance(
            lat_client, lon_client, 
            df_analyse['Latitude'], df_analyse['Longitude']
        )
        
        # Étape C : Filtrage dynamique en temps réel selon le curseur de l'usager (0 à 50 km)
        df_resultat_final = df_analyse[df_analyse['Distance du consommateur'] <= rayon_max].copy()
        
        # Tri de l'épicerie la plus proche à la plus lointaine
        df_resultat_final = df_resultat_final.sort_values(by='Distance du consommateur')
        df_resultat_final['Distance du consommateur'] = df_resultat_final['Distance du consommateur'].apply(lambda x: f"{x:.1f} km")
        
        # --- 5. AFFICHAGE DES BANNIÈRES TROUVÉES ---
        st.write("---")
        st.subheader(f"🛒 Bannières d'alimentation disponibles dans un rayon de {rayon_max} km")
        
        if not df_resultat_final.empty:
            # Afficher de grands blocs visuels pour les enseignes principales trouvées
            enseignes_uniques = df_resultat_final['Bannière'].unique()
            onglets = st.columns(min(len(enseignes_uniques), 5))
            
            for index, banniere in enumerate(enseignes_uniques[:5]):
                with onglets[index]:
                    st.info(f"⚡ **{banniere}** disponible !")
            
            # Afficher le tableau de résultats complet et détaillé
            st.markdown("### 📋 Liste détaillée des épiceries à proximité")
            
            # Suppression des coordonnées GPS internes pour l'esthétique du tableau final
            affichage_propre = df_resultat_final.drop(columns=['Latitude', 'Longitude'])
            st.dataframe(affichage_propre, use_container_width=True)
        else:
            st.warning(f"Désolé, aucun commerce d'alimentation de notre base de données ne se situe à moins de {rayon_max} km.")
            
    else:
        st.error("Ce code postal n'est pas répertorié dans votre fichier 'codes_qc.csv'. Essayez par exemple : G0M 1G0 ou G5Y 5B8.")
        
elif df_geo is not None:
    st.info("👋 Saisissez un code postal complet et faites glisser le curseur pour simuler l'affichage des bannières.")
