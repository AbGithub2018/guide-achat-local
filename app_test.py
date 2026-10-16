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
    # RECOMMANDATION : Remplacez par le lien "Raw" de votre fichier GitHub final
    url = "https://githubusercontent.com"
    df = pd.read_csv(url)
    
    # Nettoyage et uniformisation de la colonne Code_Postal (enlever espaces et majuscules)
    if 'Code_Postal' in df.columns:
        df['Code_Postal'] = df['Code_Postal'].str.replace(" ", "").str.upper()
    return df

try:
    df_magasins = load_data()
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier GitHub : {e}")
    df_magasins = pd.DataFrame()

# Initialisation du service de géolocalisation gratuit
geolocator = Nominatim(user_agent="mon_application_alimentation_quebec_v2")

# 3. Barre latérale de recherche
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G5Y 1V3)", "").replace(" ", "").upper()
rayon_km = st.sidebar.slider("Sélectionnez le rayon maximum (km)", min_value=1, max_value=50, value=10, step=1)

# 4. Traitement et filtrage
if user_postal:
    if len(user_postal) >= 3:
        with st.spinner("Localisation de votre zone et calcul des commerces à proximité..."):
            try:
                # Étape A : Trouver la position GPS de l'utilisateur
                location_user = geolocator.geocode(f"{user_postal}, Québec, Canada")
                
                if location_user:
                    coords_user = (location_user.latitude, location_user.longitude)
                    
                    # Étape B : Pré-filtrage ultra rapide par la première lettre du Code Postal
                    # Si l'utilisateur est à Montréal (H...), on ne regarde que les commerces en H...
                    premiere_lettre = user_postal[0]
                    df_region = df_magasins[df_magasins['Code_Postal'].str.startswith(premiere_lettre, na=False)].copy()
                    
                    # Étape C : Pour aller encore plus vite, on cible en priorité les commerces 
                    # qui partagent la même zone locale (les 3 premiers caractères, ex: G5Y)
                    zone_locale = user_postal[:3]
                    df_super_proche = df_region[df_region['Code_Postal'].str.startswith(zone_locale, na=False)].copy()
                    
                    # Si on ne trouve rien dans la zone immédiate, on élargit à toute la région de la lettre
                    df_a_calculer = df_super_proche if not df_super_proche.empty else df_region
                    
                    # Limiter le traitement pour ne pas bloquer le serveur web (Geopy gratuit limite les requêtes)
                    codes_postaux_uniques = df_a_calculer['Code_Postal'].unique()[:40] 
                    
                    cache_distances = {}
                    for cp in codes_postaux_uniques:
                        # Petite pause obligatoire d'une seconde pour respecter le serveur gratuit Nominatim
                        time.sleep(1) 
                        # On cherche le code postal du magasin au format "G2J1E3, Canada"
                        location_magasin = geolocator.geocode(f"{cp}, Canada")
                        
                        if location_magasin:
                            distance = geodesic(coords_user, (location_magasin.latitude, location_magasin.longitude)).km
                            cache_distances[cp] = distance
                        else:
                            cache_distances[cp] = float('inf')
                    
                    # Étape D : Application des distances trouvées sur nos commerces
                    df_a_calculer['Distance'] = df_a_calculer['Code_Postal'].map(cache_distances)
                    
                    # Filtrer par le rayon choisi par l'utilisateur et trier du plus proche au plus loin
                    df_final = df_a_calculer[df_a_calculer['Distance'] <= rayon_km].sort_values(by='Distance')
                    
                    # Étape E : Affichage des résultats dans Streamlit
                    if not df_final.empty:
                        st.success(f"🎉 {len(df_final)} commerces trouvés dans un rayon de {rayon_km} km !")
                        
                        # Arrondir la distance pour un affichage propre
                        df_final['Distance'] = df_final['Distance'].round(2).astype(str) + " km"
                        
                        # Afficher le tableau avec vos colonnes exactes de la photo
                        colonnes_visibles = ['Nom_Commerce', 'Adresse_Rue', 'Municipalite', 'Code_Postal', 'Distance']
                        st.dataframe(df_final[colonnes_visibles], use_container_width=True)
                    else:
                        st.warning(f"Aucun commerce trouvé dans un rayon de {rayon_km} km. Essayez d'augmenter le rayon.")
                else:
                    st.error("Impossible de trouver ce code postal. Vérifiez la saisie.")
            except Exception as e:
                st.error(f"Erreur de connexion au service de carte : {e}")
    else:
        st.error("Le code postal doit contenir au moins 3 caractères.")
else:
    st.info("💡 Entrez votre code postal dans le panneau de gauche pour afficher les épiceries et supermarchés ouverts autour de vous.")
