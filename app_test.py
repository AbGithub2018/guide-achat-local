import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# 1. Configuration de la page
st.set_page_config(page_title="Recherche de Commerces", layout="wide")
st.title("🍎 Recherche de commerces d'alimentation au Québec")

# 2. Chargement exclusif des données depuis votre vrai lien GitHub
@st.cache_data
def load_data():
    # Lien brut officiel vers votre fichier de 9 000 lignes
    url = "https://githubusercontent.com"
    df = pd.read_csv(url)
    
    # Nettoyage et uniformisation de la colonne Code_Postal
    if 'Code_Postal' in df.columns:
        df['Code_Postal'] = df['Code_Postal'].astype(str).str.replace(" ", "").str.upper()
    return df

try:
    df_magasins = load_data()
except Exception as e:
    st.error(f"Erreur de lecture du fichier GitHub : {e}")
    df_magasins = pd.DataFrame()

# Initialisation du service de géolocalisation gratuit
geolocator = Nominatim(user_agent="guide_achat_local_quebec_final")

# 3. Barre latérale de recherche
st.sidebar.header("Critères de recherche")
user_postal = st.sidebar.text_input("Entrez votre code postal (ex: G5Y 1V3)", "").replace(" ", "").upper()
rayon_km = st.sidebar.slider("Sélectionnez le rayon maximum (km)", min_value=1, max_value=50, value=10, step=1)

# 4. Traitement et filtrage par rayon
if user_postal and not df_magasins.empty:
    if len(user_postal) >= 3:
        with st.spinner("Localisation de votre zone et calcul des distances..."):
            try:
                # Étape A : Trouver la position GPS de l'utilisateur
                location_user = geolocator.geocode(f"{user_postal}, Québec, Canada")
                
                if location_user:
                    coords_user = (location_user.latitude, location_user.longitude)
                    
                    # Étape B : Filtrage par la première lettre du Code Postal (ex: G) pour restreindre la zone
                    premiere_lettre = user_postal[0]
                    df_region = df_magasins[df_magasins['Code_Postal'].str.startswith(premiere_lettre, na=False)].copy()
                    
                    # Étape C : Ciblage sur la zone locale immédiate (ex: G5Y)
                    zone_locale = user_postal[:3]
                    df_a_calculer = df_region[df_region['Code_Postal'].str.startswith(zone_locale, na=False)].copy()
                    
                    # Si aucun magasin ne partage les 3 mêmes caractères, on garde toute la zone régionale (lettre)
                    if df_a_calculer.empty:
                        df_a_calculer = df_region
                    
                    # Extraction des codes postaux uniques présents dans cette sélection
                    codes_postaux_uniques = df_a_calculer['Code_Postal'].unique()
                    
                    cache_distances = {}
                    for cp in codes_postaux_uniques:
                        time.sleep(1) # Pause requise pour respecter les limites du serveur gratuit Nominatim
                        location_magasin = geolocator.geocode(f"{cp}, Canada")
                        
                        if location_magasin:
                            distance = geodesic(coords_user, (location_magasin.latitude, location_magasin.longitude)).km
                            cache_distances[cp] = distance
                        else:
                            cache_distances[cp] = float('inf')
                    
                    # Étape D : Application des distances réelles calculées
                    df_a_calculer['Distance'] = df_a_calculer['Code_Postal'].map(cache_distances)
                    
                    # Filtrer selon le rayon de l'utilisateur et trier
                    df_final = df_a_calculer[df_a_calculer['Distance'] <= rayon_km].sort_values(by='Distance')
                    
                    # Étape E : Affichage des résultats
                    if not df_final.empty:
                        st.success(f"🎉 {len(df_final)} commerces trouvés dans un rayon de {rayon_km} km !")
                        
                        df_affichage = df_final.copy()
                        df_affichage['Distance'] = df_affichage['Distance'].round(2).astype(str) + " km"
                        
                        # Afficher exactement vos colonnes GitHub
                        colonnes_visibles = ['Nom_Commerce', 'Adresse_Rue', 'Municipalite', 'Code_Postal', 'Distance']
                        st.dataframe(df_affichage[[c for c in colonnes_visibles if c in df_affichage.columns]], use_container_width=True)
                    else:
                        st.warning(f"Aucun commerce trouvé dans un rayon de {rayon_km} km pour cette zone.")
                else:
                    st.error("Impossible de localiser ce code postal. Vérifiez votre saisie.")
            except Exception as e:
                st.error(f"Erreur de connexion au service de carte : {e}")
    else:
        st.error("Le code postal doit contenir au moins 3 caractères.")
elif df_magasins.empty:
    st.warning("En attente du chargement des données depuis votre dépôt GitHub...")
else:
    st.info("💡 Entrez votre code postal dans le panneau de gauche pour afficher les commerces ouverts autour de vous.")
