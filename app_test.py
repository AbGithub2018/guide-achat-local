import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 1. Configuration de la page
st.set_page_config(page_title="Recherche de Commerces", layout="wide")
st.title("🍎 Recherche de commerces d'alimentation au Québec")

# 2. Chargement des données depuis votre VRAI lien GitHub
@st.cache_data
def load_data():
    # Votre lien exact mis à jour
    url = "https://raw.githubusercontent.com/AbGithub2018/guide-achat-local/refs/heads/main/disponibilite_magasins.csv"
    df = pd.read_csv(url)
    
    # Nettoyage et uniformisation de la colonne Code_Postal
    if 'Code_Postal' in df.columns:
        df['Code_Postal'] = df['Code_Postal'].str.replace(" ", "").str.upper()
    return df

try:
    df_magasins = load_data()
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier GitHub : {e}")
    df_magasins = pd.DataFrame()

# Initialisation du service de géolocalisation gratuit
geolocator = Nominatim(user_agent="guide_achat_local_quebec_v2")

# 3. Barre latérale de recherche
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G5Y 1V3)", "").replace(" ", "").upper()
rayon_km = st.sidebar.slider("Sélectionnez le rayon maximum (km)", min_value=1, max_value=50, value=10, step=1)

# 4. Traitement et filtrage par rayon
if user_postal and not df_magasins.empty:
    if len(user_postal) >= 3:
        with st.spinner("Localisation de votre zone et calcul des commerces à proximité..."):
            try:
                # Étape A : Trouver la position GPS de l'utilisateur
                location_user = geolocator.geocode(f"{user_postal}, Québec, Canada")
                
                if location_user:
                    coords_user = (location_user.latitude, location_user.longitude)
                    
                    # Étape B : Pré-filtrage par la première lettre du Code Postal (ex: G pour Québec, H pour Montréal)
                    premiere_lettre = user_postal[0]
                    df_region = df_magasins[df_magasins['Code_Postal'].str.startswith(premiere_lettre, na=False)].copy()
                    
                    # Étape C : Ciblage ultra-rapide sur la zone locale (les 3 premiers caractères, ex: G5Y)
                    zone_locale = user_postal[:3]
                    df_super_proche = df_region[df_region['Code_Postal'].str.startswith(zone_locale, na=False)].copy()
                    
                    # Si la zone immédiate est vide, on cherche dans toute la région de cette lettre
                    df_a_calculer = df_super_proche if not df_super_proche.empty else df_region
                    
                    # On isole les codes postaux uniques (max 40 pour éviter les blocages de l'API gratuite)
                    codes_postaux_uniques = df_a_calculer['Code_Postal'].unique()[:40]
                    
                    cache_distances = {}
                    for cp in codes_postaux_uniques:
                        time.sleep(1) # Pause requise pour respecter le serveur gratuit Nominatim
                        location_magasin = geolocator.geocode(f"{cp}, Canada")
                        
                        if location_magasin:
                            distance = geodesic(coords_user, (location_magasin.latitude, location_magasin.longitude)).km
                            cache_distances[cp] = distance
                        else:
                            cache_distances[cp] = float('inf')
                    
                    # Étape D : Application des distances sur les magasins correspondants
                    df_a_calculer['Distance'] = df_a_calculer['Code_Postal'].map(cache_distances)
                    
                    # Filtrer selon le rayon de l'utilisateur et trier du plus proche au plus loin
                    df_final = df_a_calculer[df_a_calculer['Distance'] <= rayon_km].sort_values(by='Distance')
                    
                    # Étape E : Affichage des résultats
                    if not df_final.empty:
                        st.success(f"🎉 {len(df_final)} commerces trouvés dans un rayon de {rayon_km} km !")
                        
                        # Formatage de la distance pour l'affichage
                        df_final['Distance'] = df_final['Distance'].round(2).astype(str) + " km"
                        
                        # Structure finale du tableau selon votre CSV
                        colonnes_visibles = ['Nom_Commerce', 'Adresse_Rue', 'Municipalite', 'Code_Postal', 'Distance']
                        st.dataframe(df_final[colonnes_visibles], use_container_width=True)
                    else:
                        st.warning(f"Aucun commerce trouvé dans un rayon de {rayon_km} km. Essayez d'augmenter le rayon.")
                else:
                    st.error("Impossible de localiser ce code postal. Vérifiez votre saisie.")
            except Exception as e:
                st.error(f"Erreur de connexion au service de carte : {e}")
    else:
        st.error("Le code postal doit contenir au moins 3 caractères.")
elif df_magasins.empty:
    st.warning("En attente du chargement des données depuis GitHub...")
else:
    st.info("💡 Entrez votre code postal dans le panneau de gauche pour afficher les épiceries et supermarchés autour de vous.")
