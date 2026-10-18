import streamlit as st
import pandas as pd
import numpy as np

# 1. Configuration de l'interface graphique
st.set_page_config(page_title="Recherche Commerces Réelle", layout="wide")
st.title("🍎 Recherche géolocalisée de commerces au Québec")

# 2. Chargement des deux fichiers avec mise en cache Streamlit
@st.cache_data
def load_data():
    try:
        # Lecture de votre fichier de 8169 lignes (séparateur VIRGULE, UTF-8)
        df_mag = pd.read_csv("disponibilite_magasins.csv", sep=",", encoding="utf-8")
        df_gps = pd.read_csv("codes_qc.csv") # Votre référentiel de codes postaux
        
        # Uniformisation des codes postaux pour la liaison en mémoire
        df_mag['Code_Postal_Nettoye'] = df_mag['Code_Postal'].astype(str).str.replace(" ", "").str.upper().str.strip()
        df_gps['Code_Postal_Nettoye'] = df_gps['Code postal'].astype(str).str.replace(" ", "").str.upper().str.strip()
                    
        return df_mag, df_gps
    except Exception as e:
        st.error(f"Erreur de chargement des fichiers : {e}")
        return pd.DataFrame(), pd.DataFrame()

df_magasins, df_postaux = load_data()

# Fonction mathématique de Haversine pour calculer la distance réelle sur la Terre
def calculer_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Rayon moyen de la Terre en kilomètres
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

# 3. Formulaire de recherche dans la barre latérale (Sidebar)
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G0M 1G0)", "").replace(" ", "").upper().strip()
rayon_recherche = st.sidebar.slider("Rayon maximum de recherche (km)", min_value=5, max_value=50, value=15)

# NOUVEAUTÉ : Menu déroulant pour choisir une bannière spécifique
liste_bannieres = ["Toutes les bannières", "IGA", "IGA EXTRA", "IGA EXPRESS", "SUPER C", "METRO", "MAXI", "PROVIGO", "DOLLARAMA", "MARCHE AMI", "TIGRE GEANT", "WALMART", "COSTCO", "MARCHE TRADITION", "MARCHE BONICHOIX", "MARCHE RICHELIEU", "IGA EXPRESS", "IGA EXTRA", "MARCHE ADONIS"]
banniere_choisie = st.sidebar.selectbox("Filtrer par bannière :", liste_bannieres)

# 4. Traitement cartographique et calcul de distance
if user_postal and not df_postaux.empty and not df_magasins.empty:
    
    # Extraire les coordonnées GPS du code postal entré par l'utilisateur
    coords_client = df_postaux[df_postaux['Code_Postal_Nettoye'] == user_postal]
    
    if not coords_client.empty:
        lat_client = coords_client.iloc[0]['Latitude']
        lon_client = coords_client.iloc[0]['Longitude']
        
        # Jumeler en mémoire les magasins avec leurs positions GPS
        df_magasins_gps = pd.merge(
            df_magasins, 
            df_postaux[['Code_Postal_Nettoye', 'Latitude', 'Longitude']], 
            on='Code_Postal_Nettoye', 
            how='inner'
        )
        
        # Calculer la distance réelle km par km
        df_magasins_gps['Distance_KM'] = calculer_distance(
            lat_client, lon_client, 
            df_magasins_gps['Latitude'], df_magasins_gps['Longitude']
        )
        
        # Filtrer uniquement ce qui entre dans le rayon choisi
        df_resultats = df_magasins_gps[df_magasins_gps['Distance_KM'] <= rayon_recherche].copy()
        
        # NOUVEAUTÉ : Application du filtre de bannière si l'utilisateur en choisit une
        if banniere_choisie != "Toutes les bannières":
            df_resultats = df_resultats[df_resultats['Nom_Commerce'].astype(str).str.upper().str.contains(banniere_choisie)]
        
        # Tri du plus proche au plus lointain
        df_resultats = df_resultats.sort_values(by='Distance_KM')
        
        # 5. Affichage final à l'écran
        if not df_resultats.empty:
            st.success(f"🎉 {len(df_resultats)} commerce(s) trouvé(s) dans un rayon de {rayon_recherche} km autour de {user_postal} !")
            df_resultats['Distance_KM'] = df_resultats['Distance_KM'].round(1)
            
            # Reconstruction du format d'affichage postal officiel (A1A 1A1)
            df_resultats['Code_Postal_Formatte'] = df_resultats['Code_Postal'].astype(str).apply(lambda c: f"{c[:3]} {c[3:]}" if len(c)==6 else c)
            
            # Sélection ordonnée des colonnes pour le rendu visuel
            df_affichage = pd.DataFrame()
            df_affichage['Nom du commerce'] = df_resultats['Nom_Commerce']
            df_affichage['Adresse Civique'] = df_resultats['Adresse_Rue']
            df_affichage['Municipalité'] = df_resultats['Municipalite']
            df_affichage['Code Postal'] = df_resultats['Code_Postal_Formatte']
            df_affichage['Distance (km)'] = df_resultats['Distance_KM']
            
            st.dataframe(df_affichage, use_container_width=True)
        else:
            st.warning(f"Aucun commerce de type '{banniere_choisie}' trouvé dans un rayon de {rayon_recherche} km.")
    else:
        st.error("Ce code postal n'existe pas dans le fichier de référence géographique.")
else:
    if not user_postal:
        st.info("💡 Entrez un code postal dans la barre latérale pour lancer la recherche.")
