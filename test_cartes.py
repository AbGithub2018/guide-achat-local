import streamlit as st
import urllib.parse
from geopy.geocoders import Nominatim

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Entrez le nom de n'importe quelle municipalité pour afficher ses épiceries avec un zoom parfait.")

# 1. Saisie de la ville par l'utilisateur
ville_saisie = st.text_input("Entrez votre ville ou municipalité :", "Sainte-Marie")

if ville_saisie:
    try:
        # 2. Utilisation d'un géolocalisateur gratuit pour trouver la latitude et la longitude exactes
        geolocator = Nominatim(user_agent="localisateur_epiceries_quebec")
        location = geolocator.geocode(f"{ville_saisie}, Québec, Canada")
        
        if location:
            lat = location.latitude
            lon = location.longitude
            
            # Encodage du mot épiceries
            terme_recherche = urllib.parse.quote("épiceries")
            
            # 3. L'URL parfaite avec coordonnées ET zoom bloqué à 13 (échelle de ville)
            lien_maps = f"https://google.com{terme_recherche}/@{lat},{lon},13z"
            
            # 4. Le bouton d'action
            st.link_button(f"🚀 Ouvrir la carte pour {ville_saisie}", lien_maps)
        else:
            st.error("Municipalité introuvable. Assurez-vous de bien orthographier le nom.")
            
    except Exception:
        # Solution de secours si le service de géolocalisation est surchargé
        terme_encode = urllib.parse.quote(f"épiceries, {ville_saisie}, Québec, Canada")
        lien_maps = f"https://www.google.com/maps/search/?api=1&query={terme_encode}"
        st.link_button(f"🚀 Ouvrir la carte pour {ville_saisie} (Zoom automatique)", lien_maps)
