import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 1. Configuration de la page
st.set_page_config(page_title="Recherche de Commerces", layout="wide")
st.title("🍎 Recherche de commerces d'alimentation au Québec")

# 2. Chargement des données depuis GitHub
@st.cache_data
def load_data():
    # Remplacez par le lien "Raw" de votre fichier GitHub
    url = "https://githubusercontent.com"
    df = pd.read_csv(url)
    
    # Nettoyage simple des codes postaux (enlever les espaces et mettre en majuscules)
    if 'code_postal' in df.columns:
        df['code_postal'] = df['code_postal'].str.replace(" ", "").str.upper()
    return df

try:
    df_magasins = load_data()
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier GitHub : {e}")
    df_magasins = pd.DataFrame()

# Initialisation du géocodeur Geopy (avec un nom d'application unique pour respecter les règles d'utilisation)
geolocator = Nominatim(user_agent="mon_application_quebec_alimentation_v1")

# 3. Barre latérale pour les critères de recherche
st.sidebar.header("Critères de recherche")

user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G5Y 1V3)", "").replace(" ", "").upper()
rayon_km = st.sidebar.slider("Sélectionnez le rayon maximum (km)", min_value=1, max_value=50, value=10, step=1)

# 4. Logique de filtrage et affichage des résultats
if user_postal:
    if len(user_postal) >= 3:
        with st.spinner("Localisation de votre code postal et recherche des commerces..."):
            try:
                # Étape A : Trouver les coordonnées GPS du code postal de l'utilisateur
                # On ajoute ", Québec, Canada" pour s'assurer que Geopy cherche au bon endroit
                location = geolocator.geocode(f"{user_postal}, Québec, Canada")
                
                if location:
                    user_coords = (location.latitude, location.longitude)
                    
                    # Étape B : Trouver les coordonnées de chaque magasin
                    # Pour éviter de géocoder 9000 adresses à chaque clic (ce qui bloquerait l'application),
                    # nous allons d'abord filtrer grossièrement par la RMR (Région Métropolitaine) 
                    # ou calculer les distances si vos lignes contiennent déjà la latitude/longitude.
                    
                    # Si votre fichier possède déjà des colonnes 'latitude' et 'longitude' :
                    if 'latitude' in df_magasins.columns and 'longitude' in df_magasins.columns:
                        
                        # Calculer la distance pour chaque ligne
                        def calculer_distance(row):
                            if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                                return geodesic(user_coords, (row['latitude'], row['longitude'])).km
                            return float('inf')
                        
                        df_magasins['distance_km'] = df_magasins.apply(calculer_distance, axis=1)
                        df_filtre = df_magasins[df_magasins['distance_km'] <= rayon_km].sort_values(by='distance_km')
                    
                    # Si votre fichier n'a PAS de coordonnées mais juste les codes postaux des magasins :
                    else:
                        # Comme le géocodage à la volée de 9000 lignes prendrait des heures, une astuce efficace
                        # consiste à filtrer les magasins qui partagent les 3 premières lettres du code postal (la RTA)
                        rta_utilisateur = user_postal[:3]
                        df_proche = df_magasins[df_magasins['code_postal'].str.startswith(rta_utilisateur, na=False)].copy()
                        
                        # Géocoder uniquement ce petit groupe filtré pour aller très vite
                        coordonnees_cache = {}
                        distances = []
                        
                        for cp in df_proche['code_postal'].unique():
                            time.sleep(1) # Pause d'une seconde requise par Geopy pour ne pas être bloqué
                            loc_mag = geolocator.geocode(f"{cp}, Québec, Canada")
                            if loc_mag:
                                coordonnees_cache[cp] = geodesic(user_coords, (loc_mag.latitude, loc_mag.longitude)).km
                            else:
                                coordonnees_cache[cp] = float('inf')
                        
                        df_proche['distance_km'] = df_proche['code_postal'].map(coordonnees_cache)
                        df_filtre = df_proche[df_proche['distance_km'] <= rayon_km].sort_values(by='distance_km')

                    # Étape C : Affichage des résultats
                    if not df_filtre.empty:
                        st.success(f"🎉 {len(df_filtre)} commerces trouvés dans un rayon de {rayon_km} km !")
                        
                        # Formater l'affichage
                        df_affichage = df_filtre.copy()
                        df_affichage['distance_km'] = df_affichage['distance_km'].round(2).astype(str) + " km"
                        
                        colonnes_affichage = ['nom', 'adresse', 'code_postal', 'distance_km']
                        st.dataframe(df_affichage[[c for c in colonnes_affichage if c in df_affichage.columns]], use_container_width=True)
                    else:
                        st.warning(f"Aucun commerce trouvé dans un rayon de {rayon_km} km pour le code postal {user_postal}.")
                else:
                    st.error("Impossible de localiser ce code postal au Québec. Vérifiez l'orthographe.")
                    
            except Exception as e:
                st.error(f"Une erreur est survenue lors de la recherche géographique : {e}")
    else:
        st.error("Veuillez entrer un code postal valide.")
else:
    st.info("💡 Entrez un code postal dans la barre latérale pour commencer la recherche.")
