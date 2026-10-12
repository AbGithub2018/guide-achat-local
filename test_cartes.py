import streamlit as st
import urllib.parse

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Entrez le nom de n'importe quelle ville ou municipalité du Québec pour afficher ses épiceries.")

# 1. Zone de texte libre où l'utilisateur tape sa ville (Ex: Saint-Georges, Rimouski, Trois-Rivières)
ville_saisie = st.text_input("Entrez votre ville ou municipalité :", "Saint-Georges")

if ville_saisie:
    # 2. Nettoyage du texte pour s'assurer que Google cherche bien au Québec, Canada
    recherche_complete = f"épiceries, {ville_saisie}, Québec, Canada"
    
    # 3. Encodage sécurisé pour créer une URL propre (gère les espaces et les accents)
    terme_encode = urllib.parse.quote(recherche_complete)
    
    # 4. Construction de l'URL universelle de recherche Google Maps
    lien_maps = f"https://www.google.com/maps/search/{terme_encode}"
    
    # 5. Bouton d'action pour l'utilisateur
    st.link_button(f"🚀 Ouvrir la carte pour {ville_saisie}", lien_maps)
