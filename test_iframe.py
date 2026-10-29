import streamlit as st

url_super_c = "https://superc.ca"

# Code HTML pour un bouton qui réutilise TOUJOURS le même onglet nommé "onglet_circulaire"
bouton_html = f"""
<a href="{url_super_c}" target="onglet_circulaire" style="
    text-decoration: none; 
    padding: 10px 20px; 
    background-color: #ff4b4b; 
    color: white; 
    border-radius: 5px; 
    font-weight: bold; 
    display: inline-block;
    text-align: center;
    width: 100%;">
    Voir ma succursale
</a>
"""

# Affichage dans l'application
st.markdown(bouton_html, unsafe_allow_html=True)
