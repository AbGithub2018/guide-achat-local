import streamlit as st
import urllib.parse

st.title("📍 Localisateur d'Épiceries du Québec")
st.write("Entrez le nom de n'importe quelle ville ou municipalité du Québec pour afficher ses épiceries.")

# 1. La case où l'utilisateur écrit sa ville
ville_saisie = st.text_input("Entrez votre ville ou municipalité :", "Sainte-Marie")

if ville_saisie:
    # 2. Le texte de recherche envoyé à Google
    recherche_complete = f"épiceries, {ville_saisie}, Québec, Canada"
    
    # 3. L'encodage pour les accents et les espaces
    terme_encode = urllib.parse.quote(recherche_complete)
    
    # 4. LA SEULE LIGNE À MODIFIER : L'adresse officielle simplifiée
    lien_maps = f"https://www.google.com/maps/search/?api=1&query={terme_encode}&z=13"
    
    # 5. Le bouton pour ouvrir la carte
    st.link_button(f"🚀 Ouvrir la carte pour {ville_saisie}", lien_maps)
