import streamlit as st
import pandas as pd
import numpy as np

# 1. Configuration de l'interface
st.set_page_config(page_title="Recherche Commerces Réelle", layout="wide")
st.title("🍎 Vraie recherche géolocalisée de commerces au Québec")

# 2. Chargement des deux fichiers avec mise en cache
@st.cache_data
def load_data():
    try:
        # Lecture du nouveau fichier de 1866+ lignes généré en UTF-8
        df_mag = pd.read_csv("disponibilite_magasins.csv", sep=",", encoding="utf-8")
        df_gps = pd.read_csv("codes_qc.csv")
        
        # Nettoyage et uniformisation des codes postaux (retrait des espaces et majuscules)
        # Cela garantit que les liaisons se font instantanément en mémoire
        if 'Code_Postal' in df_mag.columns:
            df_mag['Code_Postal_Nettoye'] = df_mag['Code_Postal'].astype(str).str.replace(" ", "").str.upper().str.strip()
        
        if 'Code postal' in df_gps.columns:
            df_gps['Code_Postal_Nettoye'] = df_gps['Code postal'].astype(str).str.replace(" ", "").str.upper().str.strip()
                    
        return df_mag, df_gps
    except Exception as e:
        st.error(f"Erreur de chargement des fichiers : {e}")
        return pd.DataFrame(), pd.DataFrame()

df_magasins, df_postaux = load_data()

# Fonction mathématique de Haversine pour calculer la distance réelle sur la sphère terrestre
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Rayon de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# 3. Formulaire de recherche dans la barre latérale
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G0M 1G0)", "").replace(" ", "").upper().strip()
rayon_recherche = st.sidebar.slider("Rayon maximum de recherche (km)", min_value=5, max_value=50, value=15)

# 4. Traitement et calcul géolocalisé réel
if user_postal and not df_postaux.empty and not df_magasins.empty:
    
    # Trouver les coordonnées GPS exactes du code postal entré par l'utilisateur
    coords_client = df_postaux[df_postaux['Code_Postal_Nettoye'] == user_postal]
    
    if not coords_client.empty:
        lat_client = coords_client.iloc[0]['Latitude']
        lon_client = coords_client.iloc[0]['Longitude']
        
        # Liaison en mémoire avec le fichier des magasins
        df_magasins_gps = pd.merge(
            df_magasins, 
            df_postaux[['Code_Postal_Nettoye', 'Latitude', 'Longitude']], 
            on='Code_Postal_Nettoye', 
            how='inner'
        )
        
        # Calcul de la distance réelle
        df_magasins_gps['Distance_KM'] = calculer_distance(
            lat_client, lon_client, 
            df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        # Filtrage selon le rayon choisi
        df_resultats = df_magasins_gps[df_magasins_gps['Distance_KM'] <= rayon_recherche].sort_values(by='Distance_KM')
        
        # Affichage du tableau final
        if not df_resultats.empty:
            st.success(f"🎉 {len(df_resultats)} commerce(s) réellement trouvé(s) dans un rayon de {rayon_recherche} km autour de {user_postal} !")
            df_resultats['Distance_KM'] = df_resultats['Distance_KM'].round(1)
            
            colonnes_visibles = ['Nom_Commerce', 'Adresse_Rue', 'Municipalite', 'Code_Postal', 'Distance_KM']
            st.dataframe(df_resultats[colonnes_visibles], use_container_width=True)
        else:
            st.warning(f"Aucun commerce trouvé dans un rayon réel de {rayon_recherche} km autour de ce code postal.")
    else:
        st.error("Ce code postal n'existe pas dans le fichier de référence géographique.")
else:
    if not user_postal:
        st.info("💡 Entrez un code postal dans la barre latérale pour lancer la recherche par rayon.")
